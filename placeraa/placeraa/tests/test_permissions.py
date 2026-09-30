# Copyright (c) 2026, Placeraa and contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase

from placeraa.permissions import (
	STUDENT_RECORD_DOCTYPES,
	student_record_has_permission,
	student_record_query_conditions,
)


def roles(*names):
	return patch("placeraa.permissions.frappe.get_roles", return_value=list(names))


class TestStudentRecordPermissions(UnitTestCase):
	def test_managers_are_not_narrowed(self):
		for role in ("System Manager", "Moderator"):
			with roles(role):
				for doctype in STUDENT_RECORD_DOCTYPES:
					self.assertEqual(student_record_query_conditions("m@example.com", doctype), "")

	def test_administrator_is_not_narrowed(self):
		self.assertEqual(student_record_query_conditions("Administrator", "Skill Gap"), "")

	def test_a_student_is_narrowed_to_their_own_rows(self):
		with roles("LMS Student"):
			condition = student_record_query_conditions("a@example.com", "Skill Gap")
		self.assertEqual(condition, "`tabSkill Gap`.`student` = 'a@example.com'")

	def test_the_user_is_escaped_in_the_condition(self):
		with roles("LMS Student"):
			condition = student_record_query_conditions("x' OR '1'='1", "Skill Gap")
		self.assertNotIn("x' OR", condition)

	def test_a_doctype_it_does_not_gate_is_refused(self):
		self.assertEqual(student_record_query_conditions("a@example.com", "User"), "1 = 0")

	def test_a_student_reads_only_their_own_saved_row(self):
		doc = frappe._dict(doctype="Skill Gap", name="GAP-00001", student="a@example.com", is_new=lambda: False)
		with roles("LMS Student"), patch("placeraa.permissions.frappe.db.get_value") as stored:
			stored.return_value = "a@example.com"
			self.assertTrue(student_record_has_permission(doc, "read", "a@example.com"))
			self.assertFalse(student_record_has_permission(doc, "read", "b@example.com"))

	def test_relabelling_student_in_the_request_does_not_grant_access(self):
		# The request claims the row is b's, but the database says it is a's.
		doc = frappe._dict(doctype="Skill Gap", name="GAP-00001", student="b@example.com", is_new=lambda: False)
		with roles("LMS Student"), patch("placeraa.permissions.frappe.db.get_value", return_value="a@example.com"):
			self.assertFalse(student_record_has_permission(doc, "read", "b@example.com"))

	def test_managers_have_permission_on_any_row(self):
		doc = frappe._dict(doctype="Skill Gap", name="GAP-00001", student="a@example.com", is_new=lambda: False)
		with roles("Moderator"):
			self.assertTrue(student_record_has_permission(doc, "write", "m@example.com"))
