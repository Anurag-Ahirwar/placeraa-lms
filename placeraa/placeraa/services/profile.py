# Copyright (c) 2026, Placeraa and contributors
# For license information, please see license.txt

"""Turns a student's skill scores into gaps, recommendations and placement readiness.

Deterministic and rule based, no AI. The steps, each safe to run again:

1. `record_skill_score`         a score for one skill -> the student's Student Skill
2. `refresh_skill_gap`          below target -> an open Skill Gap; back on target -> Resolved
3. `refresh_recommendations`    an open gap -> the courses mapped to that skill (Course Skill)
4. `sync_recommendation_progress`  LMS enrollment progress -> Recommendation status
5. `refresh_placement_readiness`   skill scores -> the readiness components and overall score

These run on behalf of the system, not the student, who may only read their own records,
so they save with ignore_permissions. Callers decide who may trigger them.
"""

import frappe
from frappe.utils import flt, now_datetime

from placeraa.scoring import DEFAULT_TARGET_SCORE, READINESS_COMPONENTS, overall_readiness_score


def record_skill_score(student: str, skill: str, score: float, assessed_on=None):
	"""Set the student's current proficiency in a skill. The latest score wins."""
	values = {"proficiency_score": flt(score), "last_assessed_on": assessed_on or now_datetime()}
	name = frappe.db.get_value("Student Skill", {"student": student, "skill": skill})
	if name:
		doc = frappe.get_doc("Student Skill", name)
		doc.update(values)
		doc.save(ignore_permissions=True)
	else:
		doc = frappe.get_doc({"doctype": "Student Skill", "student": student, "skill": skill, **values})
		doc.insert(ignore_permissions=True)
	return doc


def refresh_skill_gap(student: str, skill: str, score: float):
	"""Keep the student's gap in a skill in step with their score.

	A skill below the default target gets a gap. A gap that already exists follows the
	score whatever it is, so it can close (the Skill Gap controller marks it Resolved).
	A skill on target with no gap gets none. Returns the gap, or None.
	"""
	name = frappe.db.get_value("Skill Gap", {"student": student, "skill": skill})
	if name:
		gap = frappe.get_doc("Skill Gap", name)
		gap.current_score = flt(score)
		gap.save(ignore_permissions=True)
		return gap

	if flt(score) >= DEFAULT_TARGET_SCORE:
		return None
	gap = frappe.get_doc(
		{
			"doctype": "Skill Gap",
			"student": student,
			"skill": skill,
			"current_score": flt(score),
			"target_score": DEFAULT_TARGET_SCORE,
		}
	)
	gap.insert(ignore_permissions=True)
	return gap


def refresh_recommendations(student: str, skill: str, gap) -> list[str]:
	"""Recommend the courses mapped to the skill while the student has an open gap in it.

	A course is recommended to a student once, whichever skill asks for it. A
	recommendation still open is brought up to date with the gap; a Completed one is
	left alone. Returns the names of the recommendations that are current.
	"""
	if not gap or gap.status == "Resolved":
		return []

	mappings = frappe.get_all(
		"Course Skill",
		filters={"skill": skill, "is_active": 1},
		fields=["course"],
		order_by="weight desc, creation asc",
	)
	reason = f"Recommended because {skill} is below your target skill level."
	names = []
	for mapping in mappings:
		if not frappe.db.get_value("LMS Course", mapping.course, "published"):
			continue

		name = frappe.db.get_value("Recommendation", {"student": student, "course": mapping.course})
		if name:
			rec = frappe.get_doc("Recommendation", name)
			if rec.status != "Completed":
				rec.update({"skill": skill, "priority": gap.severity, "reason": reason})
				rec.save(ignore_permissions=True)
		else:
			rec = frappe.get_doc(
				{
					"doctype": "Recommendation",
					"student": student,
					"skill": skill,
					"course": mapping.course,
					"reason": reason,
					"priority": gap.severity,
				}
			)
			rec.insert(ignore_permissions=True)
		names.append(rec.name)
	return names


def sync_recommendation_progress(student: str) -> None:
	"""Recommended -> In Progress -> Completed, from the student's LMS enrollment progress."""
	progress = {
		row.course: flt(row.progress)
		for row in frappe.get_all("LMS Enrollment", filters={"member": student}, fields=["course", "progress"])
	}
	for rec in frappe.get_all(
		"Recommendation",
		filters={"student": student, "status": ("!=", "Completed")},
		fields=["name", "course", "status"],
	):
		done = progress.get(rec.course, 0)
		status = "Completed" if done >= 100 else "In Progress" if done > 0 else rec.status
		if status != rec.status:
			frappe.db.set_value("Recommendation", rec.name, "status", status)


def refresh_placement_readiness(student: str):
	"""Recompute the readiness components from the student's skills, then the overall score.

	A component is the average of the student's active skills in that category. A category
	with no assessed skill keeps whatever the record already holds, and a component at 0
	is left out of the overall score (see `overall_readiness_score`).
	"""
	rows = frappe.db.sql(
		"""
		select skill.category, avg(student_skill.proficiency_score) as score
		from `tabStudent Skill` student_skill
		join `tabSkill` skill on skill.name = student_skill.skill
		where student_skill.student = %s and skill.is_active = 1
		group by skill.category
		""",
		student,
		as_dict=True,
	)
	name = frappe.db.get_value("Placement Readiness", {"student": student})
	doc = frappe.get_doc("Placement Readiness", name) if name else frappe.new_doc("Placement Readiness")
	doc.student = student

	for row in rows:
		fieldname = READINESS_COMPONENTS.get(row.category, (None,))[0]
		if fieldname:
			doc.set(fieldname, round(flt(row.score), 2))
	doc.overall_score = overall_readiness_score(
		{fieldname: doc.get(fieldname) for fieldname, _weight in READINESS_COMPONENTS.values()}
	)
	if name:
		doc.save(ignore_permissions=True)
	else:
		doc.insert(ignore_permissions=True)
	return doc


def refresh_student(student: str, skills: list[str] | None = None):
	"""Recalculate gaps and recommendations for the given skills (default: all the student's
	skills), then progress and readiness."""
	scores = {
		row.skill: row.proficiency_score
		for row in frappe.get_all(
			"Student Skill", filters={"student": student}, fields=["skill", "proficiency_score"]
		)
	}
	for skill in skills if skills is not None else list(scores):
		if skill in scores:
			gap = refresh_skill_gap(student, skill, scores[skill])
			refresh_recommendations(student, skill, gap)
	sync_recommendation_progress(student)
	return refresh_placement_readiness(student)
