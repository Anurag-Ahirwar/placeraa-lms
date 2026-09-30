# Copyright (c) 2026, Placeraa and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from placeraa.validation import validate_skill_is_active, validate_unique


class Recommendation(Document):
	def validate(self):
		validate_skill_is_active(self)
		# The same course is recommended to a student once, whichever skill asked for it.
		validate_unique(self, "student", "course")
