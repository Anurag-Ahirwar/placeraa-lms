# Copyright (c) 2026, Placeraa and contributors
# For license information, please see license.txt

"""Row-level access for the records that belong to one student.

The DocPerm rows say which roles may read these DocTypes at all. `LMS Student` is given
by LMS to every new user, so on its own it would let any student list everyone's skills,
gaps and readiness. These hooks narrow that role to the student's own rows.

A has_permission hook can only take access away, never grant it, so the roles that hold
broader DocPerm rows are listed in SEES_EVERY_STUDENT. A role missing from it would be
refused silently.
"""

import frappe

# Every DocType with a `student` field that these hooks gate.
STUDENT_RECORD_DOCTYPES = (
	"Student Skill",
	"Skill Gap",
	"Recommendation",
	"Placement Readiness",
)

SEES_EVERY_STUDENT = {"System Manager", "Moderator"}


def sees_every_student(user: str) -> bool:
	return user == "Administrator" or bool(SEES_EVERY_STUDENT & set(frappe.get_roles(user)))


def student_record_query_conditions(user: str | None = None, doctype: str | None = None) -> str:
	"""List-read counterpart of :func:`student_record_has_permission`, as SQL."""
	if doctype not in STUDENT_RECORD_DOCTYPES:
		# "" means "no restriction" to the list engine, so a DocType this function does
		# not gate must refuse explicitly.
		return "1 = 0"

	user = user or frappe.session.user
	if sees_every_student(user):
		return ""
	return f"`tab{doctype}`.`student` = {frappe.db.escape(user)}"


def student_record_has_permission(doc, ptype: str = "read", user: str | None = None, **kwargs) -> bool:
	"""A student's record belongs to that student, and to whoever manages every student."""
	user = user or frappe.session.user
	if sees_every_student(user):
		return True

	# A saved row is judged by its STORED student, or relabelling `student` in the same
	# request would move it into the caller's reach.
	student = doc.student if doc.is_new() else frappe.db.get_value(doc.doctype, doc.name, "student")
	return bool(student) and student == user
