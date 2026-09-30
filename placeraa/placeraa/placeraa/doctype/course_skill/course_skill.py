# Copyright (c) 2026, Placeraa and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from placeraa.validation import validate_scores, validate_skill_is_active, validate_unique


class CourseSkill(Document):
	def validate(self):
		validate_skill_is_active(self)
		validate_scores(self, "weight")
		validate_unique(self, "course", "skill")
