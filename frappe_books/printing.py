"""Print context shared by the standard Books print formats."""

from __future__ import annotations

from typing import Any

import frappe


def get_print_settings() -> dict[str, Any]:
	"""Return the small, presentation-safe context used by print formats."""
	settings = frappe.get_single("Books Print Settings")
	accounting = frappe.get_single("Books Accounting Settings")
	address = ""
	if settings.address and frappe.db.exists("Books Address", settings.address):
		address = frappe.db.get_value("Books Address", settings.address, "address_display") or ""
	return {
		"company_name": settings.company_name or accounting.company_name or "Frappe Books",
		"logo": settings.logo,
		"display_logo": settings.display_logo,
		"email": settings.email or accounting.email,
		"phone": settings.phone,
		"address": address,
		"color": settings.color or "#112B42",
		"gstin": accounting.gstin,
		"show_terms": settings.displaytermsandconditions,
		"terms": settings.terms_and_conditions,
	}
