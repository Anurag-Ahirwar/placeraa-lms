# Copyright (c) 2026, Placeraa and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from placeraa.validation import validate_skill_is_active, validate_unique


class QuizSkill(Document):
	def validate(self):
		validate_skill_is_active(self)
		validate_unique(self, "quiz", "skill")
