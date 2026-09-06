"""Currency metadata used for company number display defaults."""

import frappe


def currency_precision(currency: str) -> int:
	if currency == "JPY":
		return 0
	units = frappe.db.get_value("Currency", currency, "fraction_units") if currency else None
	if units is None:
		return 2
	return max(0, len(str(int(units))) - 1)
