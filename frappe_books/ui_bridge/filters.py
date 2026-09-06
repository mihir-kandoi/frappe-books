"""Validate the filter operators shared by the Books list and database adapter."""

from decimal import Decimal, InvalidOperation

import frappe

FILTER_OPERATORS = {
	"=",
	"!=",
	">",
	">=",
	"<",
	"<=",
	"in",
	"not in",
	"like",
	"not like",
	"includes",
	"is null",
	"is not null",
}
NUMERIC_TYPES = {"Check", "Currency", "Float", "Int", "Long Int", "Percent"}


def filter_pairs(fieldname, value):
	conditions = value if isinstance(value, list) else ["=", value]
	if not conditions or len(conditions) % 2:
		frappe.throw(f"Invalid filter for Books field {fieldname}")
	for index in range(0, len(conditions), 2):
		operator = str(conditions[index]).lower()
		if operator not in FILTER_OPERATORS:
			frappe.throw(f"Unsupported Books filter operator: {operator}")
		comparison = conditions[index + 1]
		if operator in {"in", "not in"}:
			if not isinstance(comparison, list) or any(isinstance(item, (dict, list)) for item in comparison):
				frappe.throw(f"Books {operator} filters require an array of values")
		elif isinstance(comparison, (dict, list)):
			frappe.throw(f"Invalid filter value for Books field {fieldname}")
		yield operator, comparison


def validate_filter_value(meta, fieldname, operator, value):
	field = meta.get_field(fieldname)
	if value is None or not field or field.fieldtype not in NUMERIC_TYPES:
		return
	if operator in {"like", "not like", "includes"}:
		frappe.throw(f"Text conditions are not supported for Books field {fieldname}")
	try:
		number = Decimal(int(value) if isinstance(value, bool) else str(value))
	except InvalidOperation, ValueError:
		frappe.throw(f"Invalid number for Books field {fieldname}")
	if not number.is_finite() or (
		field.fieldtype in {"Int", "Long Int", "Check"} and number != number.to_integral_value()
	):
		frappe.throw(f"Invalid number for Books field {fieldname}")
	if field.fieldtype == "Check" and number not in (0, 1):
		frappe.throw(f"Books field {fieldname} requires Yes or No")


def docstatus_filter(filters):
	statuses = {0, 1, 2}
	for fieldname in ("submitted", "cancelled"):
		if fieldname not in filters:
			continue
		for operator, value in filter_pairs(fieldname, filters[fieldname]):
			if operator not in {"=", "!="} or value not in (True, False, 0, 1, "0", "1"):
				frappe.throw(f"Invalid filter for Books field {fieldname}")
			expected = value in (True, 1, "1")
			matching = {1, 2} if fieldname == "submitted" else {2}
			if expected == (operator == "="):
				statuses &= matching
			else:
				statuses -= matching
	return ["docstatus", "in", sorted(statuses)]
