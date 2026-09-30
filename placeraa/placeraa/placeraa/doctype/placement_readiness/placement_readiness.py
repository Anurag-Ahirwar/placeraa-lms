# Copyright (c) 2026, Placeraa and contributors
# For license information, please see license.txt

from frappe.model.document import Document
from frappe.utils import now_datetime

from placeraa.scoring import readiness_level
from placeraa.validation import validate_scores

SCORE_FIELDS = (
	"overall_score",
	"technical_score",
	"problem_solving_score",
	"aptitude_score",
	"communication_score",
)


class PlacementReadiness(Document):
	def validate(self):
		validate_scores(self, *SCORE_FIELDS)
		self.readiness_level = readiness_level(self.overall_score)
		self.last_updated = now_datetime()
