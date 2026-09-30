# Copyright (c) 2026, Placeraa and contributors
# For license information, please see license.txt

"""The quiz -> skill profile -> gap -> recommendation -> readiness chain, and the dashboard.

These run against the seeded demo data (`bench execute placeraa.demo.seed.seed_demo_data`)
and skip themselves without it. Every test ends with a rollback, so nothing is kept.
"""

import unittest
from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase

from placeraa.api.dashboard import get_student_dashboard
from placeraa.demo.seed import DEMO_STUDENT, SQL_QUIZ_TITLE
from placeraa.services.profile import record_skill_score, refresh_student

STUDENT = DEMO_STUDENT["email"]
OTHER_STUDENT = "jane.smith@example.com"


def submit_quiz(quiz: str, correct: int, user: str = STUDENT):
	"""A quiz submission made the way LMS makes one, by the given student."""
	from lms.lms.doctype.lms_quiz.lms_quiz import create_submission

	questions = frappe.get_all(
		"LMS Quiz Question", filters={"parent": quiz}, fields=["question", "marks"], order_by="idx", limit=4
	)
	results = [
		{
			"question": "q",
			"answer": "a",
			"is_correct": int(i < correct),
			"question_name": q.question,
			"question_type": "Choices",
			"marks": q.marks if i < correct else 0,
			"marks_out_of": q.marks,
		}
		for i, q in enumerate(questions)
	]
	frappe.set_user(user)
	try:
		return create_submission(quiz, results, sum(q.marks for q in questions), 60)
	finally:
		frappe.set_user("Administrator")


class SeededTestCase(UnitTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.quiz = frappe.db.get_value("LMS Quiz", {"title": SQL_QUIZ_TITLE})
		if not (cls.quiz and frappe.db.exists("User", STUDENT)):
			raise unittest.SkipTest("demo data is not seeded (placeraa.demo.seed.seed_demo_data)")

	def setUp(self):
		# The demo student may have used the app since the seed ran (a quiz retaken, say).
		# Every test starts from the seeded state, inside the transaction tearDown rolls back.
		record_skill_score(STUDENT, "SQL", 52)
		refresh_student(STUDENT)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def skill(self, name="SQL"):
		return frappe.db.get_value(
			"Student Skill", {"student": STUDENT, "skill": name}, ["proficiency_score", "level"], as_dict=True
		)

	def gap(self, name="SQL"):
		return frappe.db.get_value(
			"Skill Gap",
			{"student": STUDENT, "skill": name},
			["gap_score", "severity", "status"],
			as_dict=True,
		)

	def readiness(self):
		return frappe.db.get_value(
			"Placement Readiness",
			{"student": STUDENT},
			["overall_score", "technical_score", "readiness_level"],
			as_dict=True,
		)


class TestQuizToSkillProfile(SeededTestCase):
	def test_the_seed_shows_the_showcase_starting_point(self):
		self.assertEqual(self.skill().proficiency_score, 52)
		self.assertEqual(self.gap().severity, "High")
		self.assertEqual(self.gap("Web Development").severity, "Medium")
		self.assertEqual(self.readiness().overall_score, 71.6)

	def test_a_passing_quiz_raises_the_skill_and_closes_the_gap(self):
		submission = submit_quiz(self.quiz, correct=3)

		self.assertEqual(submission.percentage, 75)
		self.assertEqual(self.skill().proficiency_score, 75)
		self.assertEqual(self.skill().level, "Proficient")
		self.assertEqual(self.gap().status, "Resolved")
		self.assertEqual(self.readiness().technical_score, 74.25)

	def test_a_perfect_retake_makes_the_student_placement_ready(self):
		submit_quiz(self.quiz, correct=4)

		self.assertEqual(self.skill().level, "Advanced")
		self.assertEqual(self.readiness().readiness_level, "Placement Ready")

	def test_a_poor_retake_reopens_the_gap_without_duplicating_anything(self):
		submit_quiz(self.quiz, correct=4)
		submit_quiz(self.quiz, correct=1)

		self.assertEqual((self.gap().status, self.gap().severity, self.gap().gap_score), ("Open", "High", 45))
		self.assertEqual(frappe.db.count("Skill Gap", {"student": STUDENT, "skill": "SQL"}), 1)
		self.assertEqual(frappe.db.count("Recommendation", {"student": STUDENT}), 2)

	def test_a_quiz_with_no_skill_mapping_changes_nothing(self):
		other = frappe.db.get_value("LMS Quiz", {"title": ("!=", SQL_QUIZ_TITLE)})
		submit_quiz(other, correct=1)

		self.assertEqual(self.skill().proficiency_score, 52)

	def test_one_students_quiz_does_not_touch_another_profile(self):
		submit_quiz(self.quiz, correct=4, user=OTHER_STUDENT)

		self.assertEqual(self.skill().proficiency_score, 52)
		self.assertTrue(frappe.db.exists("Student Skill", {"student": OTHER_STUDENT, "skill": "SQL"}))

	def test_a_failure_in_placeraa_never_fails_the_students_quiz(self):
		import placeraa.services.assessment as assessment

		real = assessment.process_quiz_submission

		def failing(_submission):
			raise RuntimeError("simulated failure")

		assessment.process_quiz_submission = failing
		# Error Log rows are written outside the transaction and would survive the rollback,
		# so the logger is replaced rather than letting a test leave rows behind.
		try:
			with patch("frappe.log_error") as log_error:
				submission = submit_quiz(self.quiz, correct=4)
		finally:
			assessment.process_quiz_submission = real

		self.assertTrue(frappe.db.exists("LMS Quiz Submission", submission.name))
		self.assertEqual(self.skill().proficiency_score, 52)
		log_error.assert_called_once()


class TestDashboard(SeededTestCase):
	def dashboard(self, user, student=None):
		frappe.set_user(user)
		try:
			return get_student_dashboard(student)
		finally:
			frappe.set_user("Administrator")

	def test_the_student_sees_the_showcase(self):
		data = self.dashboard(STUDENT)

		self.assertEqual(round(data["readiness"]["overall_score"]), 72)
		self.assertEqual(len(data["skills"]), 5)
		self.assertEqual([(g["skill"], g["severity"]) for g in data["gaps"]], [("SQL", "High"), ("Web Development", "Medium")])
		self.assertEqual(
			[(c["title"], c["action"], c["url"]) for c in data["recommendations"]],
			[
				("SQL for Placement Preparation", "Start Course", "/lms/courses/sql-for-placement-preparation"),
				("Web Development Fundamentals", "Continue Course", "/lms/courses/web-development-fundamentals"),
			],
		)

	def test_a_resolved_gap_leaves_the_dashboard(self):
		submit_quiz(self.quiz, correct=4)
		data = self.dashboard(STUDENT)

		self.assertEqual([g["skill"] for g in data["gaps"]], ["Web Development"])
		self.assertEqual([c["skill"] for c in data["recommendations"]], ["Web Development"])

	def test_a_student_cannot_open_another_students_dashboard(self):
		with self.assertRaises(frappe.PermissionError):
			self.dashboard(OTHER_STUDENT, STUDENT)

	def test_a_manager_can(self):
		self.assertEqual(self.dashboard("Administrator", STUDENT)["student"]["name"], STUDENT)

	def test_a_guest_cannot(self):
		with self.assertRaises(frappe.PermissionError):
			self.dashboard("Guest")

	def test_a_student_with_no_data_gets_an_empty_dashboard(self):
		data = self.dashboard("john.doe@example.com")

		self.assertIsNone(data["readiness"])
		self.assertEqual((data["skills"], data["gaps"], data["recommendations"]), ([], [], []))
