# Copyright (c) 2026, Placeraa and contributors
# For license information, please see license.txt

"""Checks that several Placeraa DocTypes run in their `validate`."""

import frappe
from frappe import _
from frappe.utils import flt

from placeraa.scoring import MAX_SCORE, MIN_SCORE


def validate_scores(doc, *fieldnames) -> None:
	"""Every named score that is set must lie on the 0-100 scale."""
	for fieldname in fieldnames:
		value = doc.get(fieldname)
		if value is None or value == "":
			continue
		if not MIN_SCORE <= flt(value) <= MAX_SCORE:
			frappe.throw(
				_("{0} must be between {1} and {2}").format(
					_(doc.meta.get_label(fieldname)), MIN_SCORE, MAX_SCORE
				),
				title=_("Invalid Score"),
			)


def validate_skill_is_active(doc) -> None:
	"""New records cannot be attached to a retired skill. Existing rows stay editable."""
	if doc.is_new() and doc.skill and not frappe.db.get_value("Skill", doc.skill, "is_active"):
		frappe.throw(_("Skill {0} is not active").format(frappe.bold(doc.skill)))


def validate_unique(doc, *fieldnames) -> None:
	"""At most one row per combination of the named fields."""
	filters = {fieldname: doc.get(fieldname) for fieldname in fieldnames}
	if any(value in (None, "") for value in filters.values()):
		return
	if not doc.is_new():
		filters["name"] = ("!=", doc.name)
	if frappe.db.exists(doc.doctype, filters):
		combination = ", ".join(f"{_(doc.meta.get_label(f))}: {doc.get(f)}" for f in fieldnames)
		frappe.throw(
			_("{0} already exists for {1}").format(_(doc.doctype), combination),
			exc=frappe.DuplicateEntryError,
		)
