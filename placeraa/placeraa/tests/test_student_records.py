# Copyright (c) 2026, Placeraa and contributors
# For license information, please see license.txt

"""Validation of the Placeraa DocTypes.

Documents are built in memory and only `validate` is called, with the two database
lookups it makes patched, so nothing is read from or written to the site.
"""

from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase


def new_doc(doctype: str, **values):
	doc = frappe.new_doc(doctype)
	doc.update(values)
	return doc


def active_skill(is_active=1):
	return patch("placeraa.validation.frappe.db.get_value", return_value=is_active)


def no_duplicate(exists=False):
	return patch("placeraa.validation.frappe.db.exists", return_value=exists)


class TestStudentSkill(UnitTestCase):
	def test_level_follows_the_score(self):
		doc = new_doc("Student Skill", student="a@example.com", skill="Python", proficiency_score=72)
		with active_skill(), no_duplicate():
			doc.validate()
		self.assertEqual(doc.level, "Proficient")

	def test_score_outside_0_to_100_is_refused(self):
		for score in (-1, 100.5):
			doc = new_doc("Student Skill", student="a@example.com", skill="Python", proficiency_score=score)
			with active_skill(), no_duplicate(), self.assertRaises(frappe.ValidationError):
				doc.validate()

	def test_duplicate_student_and_skill_is_refused(self):
		doc = new_doc("Student Skill", student="a@example.com", skill="Python", proficiency_score=50)
		with active_skill(), no_duplicate(exists=True), self.assertRaises(frappe.DuplicateEntryError):
			doc.validate()

	def test_inactive_skill_is_refused_for_a_new_record(self):
		doc = new_doc("Student Skill", student="a@example.com", skill="Python", proficiency_score=50)
		with active_skill(is_active=0), no_duplicate(), self.assertRaises(frappe.ValidationError):
			doc.validate()


class TestSkillGap(UnitTestCase):
	def validated(self, current, target=70, status="Open"):
		doc = new_doc(
			"Skill Gap",
			student="a@example.com",
			skill="SQL",
			current_score=current,
			target_score=target,
			status=status,
		)
		with active_skill(), no_duplicate():
			doc.validate()
		return doc

	def test_gap_and_severity_are_derived(self):
		doc = self.validated(current=25)
		self.assertEqual((doc.gap_score, doc.severity, doc.status), (45, "High", "Open"))

		doc = self.validated(current=60)
		self.assertEqual((doc.gap_score, doc.severity), (10, "Medium"))

		doc = self.validated(current=67)
		self.assertEqual((doc.gap_score, doc.severity), (3, "Low"))

	def test_a_closed_gap_is_resolved_and_a_reopened_one_is_open(self):
		self.assertEqual(self.validated(current=80).status, "Resolved")
		self.assertEqual(self.validated(current=80, status="Improving").status, "Resolved")
		self.assertEqual(self.validated(current=50, status="Resolved").status, "Open")

	def test_improving_is_kept_while_a_gap_remains(self):
		self.assertEqual(self.validated(current=50, status="Improving").status, "Improving")

	def test_scores_outside_0_to_100_are_refused(self):
		for kwargs in ({"current": 101}, {"current": -5}, {"current": 50, "target": 120}):
			with self.assertRaises(frappe.ValidationError):
				self.validated(**kwargs)


class TestPlacementReadiness(UnitTestCase):
	def test_level_and_timestamp_are_set(self):
		doc = new_doc("Placement Readiness", student="a@example.com", overall_score=80)
		doc.validate()
		self.assertEqual(doc.readiness_level, "Placement Ready")
		self.assertTrue(doc.last_updated)

	def test_every_score_is_range_checked(self):
		for field in (
			"overall_score",
			"technical_score",
			"problem_solving_score",
			"aptitude_score",
			"communication_score",
		):
			doc = new_doc("Placement Readiness", student="a@example.com", **{field: 101})
			with self.assertRaises(frappe.ValidationError, msg=field):
				doc.validate()


class TestCourseSkill(UnitTestCase):
	def validated(self, **values):
		doc = new_doc("Course Skill", course="sql-basics", skill="SQL", **values)
		with active_skill(), no_duplicate():
			doc.validate()
		return doc

	def test_weight_defaults_to_100_and_the_row_to_active(self):
		doc = new_doc("Course Skill", course="sql-basics", skill="SQL")
		self.assertEqual((doc.weight, doc.is_active), (100, 1))

	def test_weight_must_be_between_0_and_100(self):
		self.assertEqual(self.validated(weight=0).weight, 0)
		self.assertEqual(self.validated(weight=100).weight, 100)
		for weight in (-1, 100.01):
			with self.assertRaises(frappe.ValidationError):
				self.validated(weight=weight)

	def test_a_course_is_mapped_to_a_skill_once(self):
		doc = new_doc("Course Skill", course="sql-basics", skill="SQL")
		with active_skill(), no_duplicate(exists=True), self.assertRaises(frappe.DuplicateEntryError):
			doc.validate()

	def test_only_an_active_skill_can_be_mapped(self):
		doc = new_doc("Course Skill", course="sql-basics", skill="SQL")
		with active_skill(is_active=0), no_duplicate(), self.assertRaises(frappe.ValidationError):
			doc.validate()


class TestRecommendationAndQuizSkill(UnitTestCase):
	def test_a_course_is_recommended_to_a_student_once(self):
		doc = new_doc("Recommendation", student="a@example.com", skill="SQL", course="sql-basics")
		with active_skill(), no_duplicate(exists=True), self.assertRaises(frappe.DuplicateEntryError):
			doc.validate()
		with active_skill(), no_duplicate():
			doc.validate()

	def test_a_quiz_is_mapped_to_a_skill_once(self):
		doc = new_doc("Quiz Skill", quiz="quiz-1", skill="SQL")
		with active_skill(), no_duplicate(exists=True), self.assertRaises(frappe.DuplicateEntryError):
			doc.validate()
