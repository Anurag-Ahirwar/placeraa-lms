# Copyright (c) 2026, Placeraa and contributors
# For license information, please see license.txt

"""Data for the Placeraa student dashboard."""

import frappe
from frappe import _
from frappe.utils import flt

from placeraa.permissions import sees_every_student
from placeraa.scoring import DEFAULT_TARGET_SCORE

SEVERITY_ORDER = {"High": 0, "Medium": 1, "Low": 2}
READINESS_FIELDS = (
	"overall_score",
	"technical_score",
	"problem_solving_score",
	"aptitude_score",
	"communication_score",
	"readiness_level",
	"last_updated",
)


def lms_course_url(course: str) -> str:
	"""Where the student opens the course in the LMS."""
	lms_path = (frappe.conf.get("lms_path") or "lms").strip("/")
	return f"/{lms_path}/courses/{course}"


@frappe.whitelist()
def get_student_dashboard(student: str | None = None) -> dict:
	"""Everything the dashboard shows for one student.

	A student sees their own dashboard. Whoever manages every student (System Manager,
	Moderator) may name another student, for instance to demo their view.
	"""
	student = resolve_student(student)

	user = frappe.db.get_value("User", student, ["full_name", "first_name", "user_image"], as_dict=True)
	skills = get_skills(student)
	gaps = get_gaps(student)
	recommendations = get_recommendations(student, gaps)

	readiness = frappe.db.get_value(
		"Placement Readiness", {"student": student}, list(READINESS_FIELDS), as_dict=True
	)
	targets = {gap["skill"]: gap["target_score"] for gap in gaps}
	for skill in skills:
		skill["target_score"] = targets.get(skill["skill"], DEFAULT_TARGET_SCORE)

	return {
		"student": {
			"name": student,
			"full_name": user.full_name,
			"first_name": user.first_name or user.full_name,
			"image": user.user_image,
		},
		"readiness": readiness,
		"skills": skills,
		"gaps": gaps,
		"recommendations": recommendations,
		"enrollments": get_enrollments(student),
		"summary": {
			"skills_assessed": len(skills),
			"open_gaps": len(gaps),
			"recommended_courses": len(recommendations),
		},
		"lms_url": "/" + (frappe.conf.get("lms_path") or "lms").strip("/"),
		"is_own_dashboard": student == frappe.session.user,
	}


def resolve_student(student: str | None) -> str:
	user = frappe.session.user
	if user == "Guest":
		frappe.throw(_("Please log in to see your dashboard."), frappe.PermissionError)

	student = student or user
	if student != user and not sees_every_student(user):
		frappe.throw(_("You can only see your own dashboard."), frappe.PermissionError)
	if not frappe.db.exists("User", student):
		frappe.throw(_("Student {0} does not exist.").format(frappe.bold(student)), frappe.DoesNotExistError)
	return student


def get_skills(student: str) -> list[dict]:
	return frappe.db.sql(
		"""
		select student_skill.skill, skill.category, student_skill.proficiency_score as score,
			student_skill.level, student_skill.last_assessed_on
		from `tabStudent Skill` student_skill
		join `tabSkill` skill on skill.name = student_skill.skill
		where student_skill.student = %s and skill.is_active = 1
		order by skill.creation, skill.name
		""",
		student,
		as_dict=True,
	)


def get_gaps(student: str) -> list[dict]:
	"""Open gaps, most severe first."""
	gaps = frappe.get_all(
		"Skill Gap",
		filters={"student": student, "status": ("!=", "Resolved")},
		fields=["skill", "current_score", "target_score", "gap_score", "severity", "status"],
	)
	return sorted(gaps, key=lambda gap: (SEVERITY_ORDER.get(gap.severity, 3), -flt(gap.gap_score)))


def get_recommendations(student: str, gaps: list[dict]) -> list[dict]:
	"""Courses recommended for an open gap, plus any the student already started or finished."""
	open_gap_skills = {gap["skill"] for gap in gaps}
	recommendations = [
		rec
		for rec in frappe.get_all(
			"Recommendation",
			filters={"student": student},
			fields=["name", "skill", "course", "reason", "priority", "status"],
		)
		if rec.skill in open_gap_skills or rec.status in ("In Progress", "Completed")
	]
	if not recommendations:
		return []

	courses = {
		course.name: course
		for course in frappe.get_all(
			"LMS Course",
			filters={"name": ("in", [rec.course for rec in recommendations]), "published": 1},
			fields=["name", "title", "short_introduction", "image", "lessons"],
		)
	}
	progress = {
		row.course: flt(row.progress)
		for row in frappe.get_all("LMS Enrollment", filters={"member": student}, fields=["course", "progress"])
	}

	cards = []
	for rec in recommendations:
		course = courses.get(rec.course)
		if not course:
			continue
		done = progress.get(rec.course)
		cards.append(
			{
				**rec,
				"title": course.title,
				"short_introduction": course.short_introduction,
				"image": course.image,
				"lessons": course.lessons,
				"url": lms_course_url(rec.course),
				"enrolled": done is not None,
				"progress": done or 0,
				"action": _action_label(done),
			}
		)
	return sorted(cards, key=lambda card: (SEVERITY_ORDER.get(card["priority"], 3), card["title"]))


def _action_label(progress: float | None) -> str:
	if progress is None or progress == 0:
		return _("Start Course")
	return _("Review Course") if progress >= 100 else _("Continue Course")


def get_enrollments(student: str) -> list[dict]:
	"""The student's LMS courses with their progress, most recently touched first."""
	enrollments = frappe.db.sql(
		"""
		select enrollment.course, course.title, enrollment.progress
		from `tabLMS Enrollment` enrollment
		join `tabLMS Course` course on course.name = enrollment.course
		where enrollment.member = %s and course.published = 1
		order by enrollment.modified desc
		limit 8
		""",
		student,
		as_dict=True,
	)
	for enrollment in enrollments:
		enrollment["url"] = lms_course_url(enrollment.course)
	return enrollments
