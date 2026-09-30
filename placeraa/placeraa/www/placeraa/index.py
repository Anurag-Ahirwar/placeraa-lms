# Copyright (c) 2026, Placeraa and contributors
# For license information, please see license.txt

import math

import frappe
from frappe import _
from frappe.utils import flt

from placeraa.api.dashboard import get_student_dashboard

no_cache = 1

RING_RADIUS = 52


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/placeraa"
		raise frappe.Redirect

	context.no_cache = 1
	context.no_breadcrumbs = 1
	context.title = _("Placeraa | Your Placement Readiness")
	context.data = get_student_dashboard(frappe.form_dict.get("student"))

	# The readiness ring is an SVG circle whose stroke is cut to the score.
	overall = flt((context.data["readiness"] or {}).get("overall_score"))
	circumference = 2 * math.pi * RING_RADIUS
	context.ring = {
		"radius": RING_RADIUS,
		"circumference": round(circumference, 2),
		"offset": round(circumference * (1 - min(max(overall, 0), 100) / 100), 2),
	}
	return context
