# Copyright (c) 2026, Placeraa and contributors
# For license information, please see license.txt

"""Demo data for the Placeraa showcase.

    bench --site lms.localhost execute placeraa.demo.seed.seed_demo_data

Idempotent: every record is looked up first and only created when missing, so running it
again creates nothing and never overwrites what a student has done since (a retaken quiz
keeps its new score). The demo LMS courses carry the tag `placeraa-demo`.

`dry_run=True` does everything and then rolls the transaction back, to check the seed
against a site without keeping anything.
"""

import json
import os
import random
import string

import frappe
from frappe.utils import nowdate, now_datetime
from frappe.utils.password import update_password

from placeraa.services.profile import record_skill_score, refresh_student

DEMO_TAG = "placeraa-demo"
DEMO_STUDENT = {"email": "demo.student@placeraa.test", "first_name": "Demo", "last_name": "Student"}
# Local development only: the password is set when the demo student is created, and only on a
# site in developer mode. Set PLACERAA_DEMO_PASSWORD to choose a different one.
DEMO_PASSWORD = "Placeraa-Demo-2026!"

DSA, PYTHON, SQL, WEB, APTITUDE = (
	"Data Structures & Algorithms",
	"Python",
	"SQL",
	"Web Development",
	"Aptitude",
)

SKILLS = [
	(DSA, "Technical", "Arrays, linked lists, trees, graphs, sorting, searching and complexity."),
	(PYTHON, "Technical", "Core Python for coding rounds and everyday scripting."),
	(SQL, "Technical", "Querying relational data: filters, joins and aggregations."),
	(WEB, "Technical", "HTML, CSS and JavaScript fundamentals for building web pages."),
	(APTITUDE, "Aptitude", "Quantitative reasoning tested in placement aptitude rounds."),
]

# Where the demo student stands today.
DEMO_SCORES = {DSA: 82, PYTHON: 76, SQL: 52, WEB: 64, APTITUDE: 71}
# No skill in these categories is assessed yet, so their readiness components are seeded.
DEMO_READINESS_EXTRAS = {"problem_solving_score": 78, "communication_score": 70}

COURSES = [
	{
		"skill": DSA,
		"title": "DSA for Placement Preparation",
		"intro": "Master the data structures and algorithms that placement interviews test.",
		"description": "<p>Build the problem-solving toolkit every coding round expects: arrays, linked lists, stacks, queues, sorting, searching and how to reason about time and space complexity.</p>",
		"chapter": "Core Data Structures",
		"lessons": [
			(
				"Arrays, Linked Lists and Stacks",
				[
					"An array stores items contiguously, so reading by index is O(1) but inserting in the middle is O(n). A linked list trades that around: inserting is O(1) once you hold the node, while reaching the n-th item costs O(n).",
					"A stack is last in, first out. It powers undo, expression evaluation and depth-first search. A queue is first in, first out and powers breadth-first search and scheduling.",
				],
			),
			(
				"Sorting and Searching",
				[
					"Binary search finds an item in a sorted array in O(log n) by halving the range each step. Merge sort and quick sort both sort in O(n log n) on average.",
					"In an interview, state the complexity of your approach before you code it, then look for a way to do better.",
				],
			),
		],
	},
	{
		"skill": PYTHON,
		"title": "Python for Placement Preparation",
		"intro": "Write clean, correct Python for coding rounds and technical interviews.",
		"description": "<p>Cover the Python that placement tests rely on: data types, control flow, functions, comprehensions and the built-in tools that keep solutions short and readable.</p>",
		"chapter": "Python Essentials",
		"lessons": [
			(
				"Types, Loops and Functions",
				[
					"Lists, tuples, sets and dictionaries cover most needs: a list keeps order, a set removes duplicates, and a dictionary looks a key up in O(1) on average.",
					"Functions take arguments, return values and can carry default parameters. Keep each one small and give it a single job.",
				],
			),
			(
				"Comprehensions and Built-ins",
				[
					"A list comprehension such as [x * x for x in nums if x % 2 == 0] replaces a short loop with one readable line.",
					"Built-ins like sorted, enumerate, zip, sum and any do a lot of work for you, and interviewers like to see them used well.",
				],
			),
		],
	},
	{
		"skill": SQL,
		"title": "SQL for Placement Preparation",
		"intro": "Query relational data with confidence: filters, joins and aggregations.",
		"description": "<p>Learn the SQL that appears in technical interviews and online assessments: selecting and filtering rows, joining tables, grouping results and reading a query plan in your head.</p>",
		"chapter": "SQL Foundations",
		"lessons": [
			(
				"SELECT, WHERE and ORDER BY",
				[
					"SELECT chooses the columns, FROM names the table, WHERE keeps only the rows that match a condition, and ORDER BY sorts what is left.",
					"DISTINCT removes duplicate rows from the result. LIMIT keeps only the first rows, which is useful with ORDER BY.",
				],
			),
			(
				"Joins and Aggregations",
				[
					"An INNER JOIN keeps only rows that match in both tables. A LEFT JOIN keeps every row from the left table and fills the gaps with NULL.",
					"GROUP BY collapses rows into groups so you can COUNT, SUM or AVG each group. WHERE filters rows before grouping and HAVING filters the groups after.",
				],
			),
		],
	},
	{
		"skill": WEB,
		"title": "Web Development Fundamentals",
		"intro": "Build and style web pages with HTML, CSS and JavaScript.",
		"description": "<p>Start from the three building blocks of the web: HTML for structure, CSS for presentation and JavaScript for behaviour, then put them together in a small page.</p>",
		"chapter": "Building for the Web",
		"lessons": [
			(
				"HTML and CSS Basics",
				[
					"HTML describes what is on the page with elements such as headings, paragraphs, links, lists and forms. CSS decides how it looks: colours, spacing and layout.",
					"Flexbox and grid are the two layout systems to know. Flexbox lays items out along one axis and grid works in rows and columns.",
				],
			),
			(
				"JavaScript and the DOM",
				[
					"The DOM is the browser's live model of the page. JavaScript can read it, change it and react to events such as clicks.",
					"Keep logic in functions, prefer const and let over var, and use fetch to load data from a server without reloading the page.",
				],
			),
		],
	},
	{
		"skill": APTITUDE,
		"title": "Quantitative Aptitude for Placements",
		"intro": "Sharpen the number skills that aptitude rounds reward.",
		"description": "<p>Practise the quantitative topics that recur in placement aptitude tests, with the shortcuts that save time under pressure.</p>",
		"chapter": "Numbers Under Pressure",
		"lessons": [
			(
				"Percentages, Ratios and Averages",
				[
					"A percentage is a fraction of 100. To increase a value by 20 percent, multiply by 1.2. To split in the ratio 3:2, give 3/5 and 2/5 of the total.",
					"The average is the sum divided by the count, so when one value changes, the average moves by the change divided by the count.",
				],
			),
			(
				"Time, Speed and Work",
				[
					"Distance equals speed times time. For a round trip at speeds a and b over the same distance, the average speed is 2ab / (a + b), not the plain average.",
					"If A finishes a job in 6 days and B in 3 days, together they do 1/6 + 1/3 = 1/2 of it per day, so they take 2 days.",
				],
			),
		],
	},
]

SQL_QUIZ_TITLE = "SQL Fundamentals Quiz"
SQL_QUIZ = [
	(
		"Which SQL clause filters rows before they are grouped?",
		["WHERE", "HAVING", "ORDER BY", "LIMIT"],
		0,
	),
	(
		"Which JOIN returns only the rows that have a match in both tables?",
		["INNER JOIN", "LEFT JOIN", "RIGHT JOIN", "CROSS JOIN"],
		0,
	),
	(
		"Which function counts the number of rows in a group?",
		["COUNT()", "SUM()", "AVG()", "MAX()"],
		0,
	),
	(
		"What does SELECT DISTINCT do?",
		[
			"Removes duplicate rows from the result",
			"Sorts the result",
			"Limits the number of rows returned",
			"Deletes duplicate rows from the table",
		],
		0,
	),
]

# The demo student has started this course, to show progress next to a course still to start.
ENROLLED_DEMO_COURSE = "Web Development Fundamentals"
ENROLLED_PROGRESS = 30


def seed_demo_data(dry_run: bool = False) -> dict:
	"""Create the showcase data that is missing. Returns what was created and what was kept."""
	created: dict[str, list[str]] = {}

	def once(doctype: str, filters: dict, values: dict | None = None):
		"""The record matching `filters`, created from `filters` + `values` if there is none."""
		name = frappe.db.get_value(doctype, filters)
		if name:
			return frappe.get_doc(doctype, name)
		doc = frappe.get_doc({"doctype": doctype, **filters, **(values or {})})
		doc.insert(ignore_permissions=True)
		created.setdefault(doctype, []).append(doc.name)
		return doc

	for skill_name, category, description in SKILLS:
		once("Skill", {"skill_name": skill_name}, {"category": category, "description": description})

	courses = {course["skill"]: _ensure_course(course, once) for course in COURSES}
	quiz = _ensure_sql_quiz(courses[SQL], once)

	for skill, course in courses.items():
		once("Course Skill", {"course": course.name, "skill": skill}, {"weight": 100, "is_active": 1})
	once("Quiz Skill", {"quiz": quiz.name, "skill": SQL})

	student = _ensure_demo_student(created)
	_ensure_enrollment(student, courses[WEB].name, once)

	for skill, score in DEMO_SCORES.items():
		# Only when missing: a student's real quiz scores must survive a re-run.
		if not frappe.db.exists("Student Skill", {"student": student, "skill": skill}):
			doc = record_skill_score(student, skill, score, assessed_on=now_datetime())
			created.setdefault("Student Skill", []).append(doc.name)
	once("Placement Readiness", {"student": student}, DEMO_READINESS_EXTRAS)
	refresh_student(student)

	for doctype in ("Skill Gap", "Recommendation"):
		created.setdefault(doctype, [])
	summary = {
		"student": student,
		"created": {doctype: len(names) for doctype, names in created.items() if names},
		"totals": {
			doctype: frappe.db.count(doctype, {"student": student})
			for doctype in ("Student Skill", "Skill Gap", "Recommendation", "Placement Readiness")
		},
		"dry_run": bool(dry_run),
	}
	if dry_run:
		frappe.db.rollback()
	return summary


def _ensure_course(spec: dict, once):
	course = once(
		"LMS Course",
		{"title": spec["title"]},
		{
			"short_introduction": spec["intro"],
			"description": spec["description"],
			"published": 1,
			"status": "Approved",
			"published_on": nowdate(),
			"tags": DEMO_TAG,
			"instructors": [{"instructor": "Administrator"}],
		},
	)
	if not course.chapters:
		chapter = once("Course Chapter", {"course": course.name, "title": spec["chapter"]})
		# The course must list the chapter before its lessons are added: LMS counts a
		# course's lessons through its chapter list. Creating the chapter already touched
		# the course row, so add to its current state.
		course.reload()
		course.append("chapters", {"chapter": chapter.name})
		course.save(ignore_permissions=True)

		for title, paragraphs in spec["lessons"]:
			lesson = once(
				"Course Lesson",
				{"chapter": chapter.name, "course": course.name, "title": title},
				{"content": _editor_content(title, paragraphs)},
			)
			# LMS updates the chapter as lessons come and go, so add to the current row.
			chapter.reload()
			chapter.append("lessons", {"lesson": lesson.name})
			chapter.save(ignore_permissions=True)
		course.reload()

	_sync_lesson_count(course)
	return course


def _sync_lesson_count(course) -> None:
	"""Make LMS Course.lessons the number LMS itself counts, repairing an earlier run."""
	from lms.lms.utils import get_lesson_count

	expected = get_lesson_count(course.name)
	if course.lessons != expected:
		frappe.db.set_value("LMS Course", course.name, "lessons", expected)
		course.lessons = expected


def _ensure_sql_quiz(course, once):
	"""The SQL quiz, and a lesson in the SQL course that holds it."""
	questions = []
	for text, options, correct in SQL_QUIZ:
		values = {"type": "Choices", "marks": 5, "multiple": 0}
		for index, option in enumerate(options, start=1):
			values[f"option_{index}"] = option
			values[f"is_correct_{index}"] = 1 if index - 1 == correct else 0
		questions.append(once("LMS Question", {"question": text}, values))

	quiz = once(
		"LMS Quiz",
		{"title": SQL_QUIZ_TITLE},
		{
			"course": course.name,
			"passing_percentage": 60,
			"total_marks": 5 * len(questions),
			"max_attempts": 0,
			"show_answers": 1,
			"questions": [{"question": q.name, "marks": 5} for q in questions],
		},
	)

	chapter = frappe.get_doc("Course Chapter", course.chapters[0].chapter)
	if not frappe.db.exists("Course Lesson", {"chapter": chapter.name, "title": SQL_QUIZ_TITLE}):
		lesson = once(
			"Course Lesson",
			{"chapter": chapter.name, "course": course.name, "title": SQL_QUIZ_TITLE},
			{"content": _editor_content(None, [], quiz=quiz.name)},
		)
		chapter.reload()
		chapter.append("lessons", {"lesson": lesson.name})
		chapter.save(ignore_permissions=True)
	return quiz


def _editor_content(title: str | None, paragraphs: list[str], quiz: str | None = None) -> str:
	"""A lesson body in the block format LMS lessons use (Editor.js)."""

	def block(kind: str, data: dict) -> dict:
		return {"id": "".join(random.choices(string.ascii_letters + string.digits, k=10)), "type": kind, "data": data}

	blocks = []
	if title:
		blocks.append(block("header", {"text": title, "level": 2}))
	blocks += [block("paragraph", {"text": text}) for text in paragraphs]
	if quiz:
		blocks.append(block("quiz", {"quiz": quiz}))
	return json.dumps({"time": int(now_datetime().timestamp() * 1000), "blocks": blocks, "version": "2.29.0"})


def _ensure_demo_student(created: dict) -> str:
	email = DEMO_STUDENT["email"]
	if frappe.db.exists("User", email):
		return email

	frappe.get_doc(
		{
			"doctype": "User",
			**DEMO_STUDENT,
			"send_welcome_email": 0,
			"enabled": 1,
			"user_type": "Website User",
		}
	).insert(ignore_permissions=True)
	created.setdefault("User", []).append(email)

	# A known password is only acceptable on a development site.
	if frappe.conf.get("developer_mode"):
		update_password(email, os.environ.get("PLACERAA_DEMO_PASSWORD") or DEMO_PASSWORD)
	return email


def _ensure_enrollment(student: str, course: str, once) -> None:
	once(
		"LMS Enrollment",
		{"member": student, "course": course},
		{"member_type": "Student", "role": "Member", "progress": ENROLLED_PROGRESS},
	)
