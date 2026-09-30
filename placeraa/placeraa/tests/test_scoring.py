# Copyright (c) 2026, Placeraa and contributors
# For license information, please see license.txt

from frappe.tests import UnitTestCase

from placeraa.scoring import (
	calculate_gap,
	gap_severity,
	overall_readiness_score,
	proficiency_level,
	readiness_level,
)


class TestScoring(UnitTestCase):
	def test_proficiency_level_boundaries(self):
		for score, level in [
			(0, "Beginner"),
			(39.99, "Beginner"),
			(40, "Developing"),
			(69.99, "Developing"),
			(70, "Proficient"),
			(84.99, "Proficient"),
			(85, "Advanced"),
			(100, "Advanced"),
		]:
			self.assertEqual(proficiency_level(score), level, score)

	def test_readiness_level_boundaries(self):
		for score, level in [
			(0, "Not Ready"),
			(49.99, "Not Ready"),
			(50, "Developing"),
			(74.99, "Developing"),
			(75, "Placement Ready"),
			(100, "Placement Ready"),
		]:
			self.assertEqual(readiness_level(score), level, score)

	def test_gap_severity_boundaries(self):
		for gap, severity in [(0, "Low"), (4.99, "Low"), (5, "Medium"), (14.99, "Medium"), (15, "High"), (60, "High")]:
			self.assertEqual(gap_severity(gap), severity, gap)

	def test_the_showcase_gaps_are_prioritised_as_shown(self):
		# SQL 52 / 70 is High priority and Web Development 64 / 70 is Medium.
		self.assertEqual(gap_severity(calculate_gap(52, 70)), "High")
		self.assertEqual(gap_severity(calculate_gap(64, 70)), "Medium")

	def test_overall_readiness_is_a_weighted_average(self):
		scores = {
			"technical_score": 68.5,
			"problem_solving_score": 78,
			"aptitude_score": 71,
			"communication_score": 70,
		}
		self.assertEqual(overall_readiness_score(scores), 71.6)

	def test_unassessed_components_do_not_drag_the_overall_down(self):
		self.assertEqual(overall_readiness_score({"technical_score": 60, "aptitude_score": 80}), 66.67)
		self.assertEqual(overall_readiness_score({"technical_score": 60}), 60)
		self.assertEqual(overall_readiness_score({}), 0)

	def test_gap_is_never_negative(self):
		self.assertEqual(calculate_gap(30, 70), 40)
		self.assertEqual(calculate_gap(70, 70), 0)
		self.assertEqual(calculate_gap(90, 70), 0)

	def test_empty_scores_count_as_zero(self):
		self.assertEqual(proficiency_level(None), "Beginner")
		self.assertEqual(calculate_gap(None, 70), 70)
