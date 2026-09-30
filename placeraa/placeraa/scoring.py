# Copyright (c) 2026, Placeraa and contributors
# For license information, please see license.txt

"""Score scale and level thresholds shared by the Placeraa DocTypes.

Pure functions and constants only, so they are trivial to test and to reuse from
the assessment, gap and recommendation logic that will be built on top.
"""

from frappe.utils import flt

MIN_SCORE = 0
MAX_SCORE = 100

# The score a student is expected to reach in a skill unless told otherwise.
DEFAULT_TARGET_SCORE = 70

# Every band list is (label, inclusive lower bound), highest band first.
PROFICIENCY_LEVELS = (("Advanced", 85), ("Proficient", 70), ("Developing", 40), ("Beginner", 0))
GAP_SEVERITIES = (("High", 15), ("Medium", 5), ("Low", 0))
READINESS_LEVELS = (("Placement Ready", 75), ("Developing", 50), ("Not Ready", 0))

# Skill category -> (Placement Readiness field, weight of that field in the overall score).
READINESS_COMPONENTS = {
	"Technical": ("technical_score", 0.40),
	"Problem Solving": ("problem_solving_score", 0.25),
	"Aptitude": ("aptitude_score", 0.20),
	"Communication": ("communication_score", 0.15),
}


def _band(value, bands) -> str:
	value = flt(value)
	for label, lower_bound in bands:
		if value >= lower_bound:
			return label
	return bands[-1][0]


def proficiency_level(score) -> str:
	return _band(score, PROFICIENCY_LEVELS)


def gap_severity(gap) -> str:
	return _band(gap, GAP_SEVERITIES)


def readiness_level(score) -> str:
	return _band(score, READINESS_LEVELS)


def overall_readiness_score(component_scores: dict) -> float:
	"""Weighted average of the readiness components, by Placement Readiness fieldname.

	A component at 0 is treated as not assessed yet and left out, with the remaining
	weights scaled up to fill its share. Otherwise a student assessed in one category
	would be scored as if they had failed the others.
	"""
	weighted = total_weight = 0.0
	for fieldname, weight in READINESS_COMPONENTS.values():
		score = flt(component_scores.get(fieldname))
		if score > 0:
			weighted += score * weight
			total_weight += weight
	return round(weighted / total_weight, 2) if total_weight else 0.0


def calculate_gap(current_score, target_score) -> float:
	"""Points still missing to reach the target. Never negative: exceeding it is no gap."""
	return round(max(flt(target_score) - flt(current_score), 0), 2)
