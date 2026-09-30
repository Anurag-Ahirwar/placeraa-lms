# Copyright (c) 2026, Placeraa and contributors
# For license information, please see license.txt

"""Feeds LMS quiz results into the student's skill profile.

LMS keeps running its quizzes exactly as before. When a quiz is submitted, the Quiz Skill
rows say which skills it measures, and the result becomes the student's score in them.

MVP simplification: the score in a skill is the percentage of the latest submission of a
quiz mapped to it. A quiz mapped to several skills gives every one of them that same
percentage. Weighting by question, or by attempt history, comes later.
"""

import frappe
from frappe.utils import flt

from placeraa.scoring import MAX_SCORE, MIN_SCORE
from placeraa.services.profile import record_skill_score, refresh_student


def mapped_skills(quiz: str) -> list[str]:
	"""The active skills the quiz measures."""
	return frappe.get_all(
		"Quiz Skill",
		filters={"quiz": quiz, "skill": ("in", frappe.get_all("Skill", {"is_active": 1}, pluck="name"))},
		pluck="skill",
		order_by="creation asc",
	)


def process_quiz_submission(submission) -> list[str]:
	"""Apply one LMS Quiz Submission (a name or a document). Returns the skills updated."""
	doc = frappe.get_doc("LMS Quiz Submission", submission) if isinstance(submission, str) else submission
	if not (doc.quiz and doc.member):
		return []

	skills = mapped_skills(doc.quiz)
	if not skills:
		return []

	score = min(max(flt(doc.percentage), MIN_SCORE), MAX_SCORE)
	for skill in skills:
		record_skill_score(doc.member, skill, score)
	refresh_student(doc.member, skills)
	return skills


def on_quiz_submission(doc, method=None) -> None:
	"""doc_events hook for `LMS Quiz Submission` after_insert.

	A problem here must never stop a student submitting their quiz, so whatever this did is
	undone and logged rather than raised.
	"""
	save_point = "placeraa_quiz_submission"
	frappe.db.savepoint(save_point)
	try:
		process_quiz_submission(doc)
	except Exception:
		frappe.db.rollback(save_point=save_point)
		frappe.log_error(title="Placeraa: quiz result not applied to the skill profile")
