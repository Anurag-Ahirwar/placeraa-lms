# Copyright (c) 2026, Placeraa and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from placeraa.scoring import proficiency_level
from placeraa.validation import validate_scores, validate_skill_is_active, validate_unique


class StudentSkill(Document):
	def validate(self):
		validate_skill_is_active(self)
		validate_scores(self, "proficiency_score")
		validate_unique(self, "student", "skill")
		self.level = proficiency_level(self.proficiency_score)
