# Copyright (c) 2026, Placeraa and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from placeraa.scoring import calculate_gap, gap_severity
from placeraa.validation import validate_scores, validate_skill_is_active, validate_unique


class SkillGap(Document):
	def validate(self):
		validate_skill_is_active(self)
		validate_scores(self, "current_score", "target_score")
		validate_unique(self, "student", "skill")
		self.set_gap()
		self.sync_status()

	def set_gap(self):
		self.gap_score = calculate_gap(self.current_score, self.target_score)
		self.severity = gap_severity(self.gap_score)

	def sync_status(self):
		"""A closed gap is Resolved, and a Resolved one that reopens is Open again."""
		if self.gap_score == 0:
			self.status = "Resolved"
		elif self.status == "Resolved":
			self.status = "Open"
