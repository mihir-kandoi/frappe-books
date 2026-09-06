"""Stock ledger and stock balance report calculations."""

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import get_datetime

from frappe_books.accounting.money import as_decimal, rounded
from frappe_books.inventory.valuation import computed_entries


def stock_ledger(filters=None):
	filters = frappe._dict(filters or {})
	rows = computed_entries(filters)
	return _ledger_columns(), rows


def stock_balance(filters=None):
	filters = frappe._dict(filters or {})
	rows = computed_entries(filters, include_before=True)
	grouped = defaultdict(_empty_balance)
	from_date = get_datetime(filters.from_date) if filters.from_date else None
	to_date = get_datetime(filters.to_date) if filters.to_date else None
	for row in rows:
		key = (row["item"], row["location"], row.get("batch") or "")
		balance = grouped[key]
		balance.update({"item": row["item"], "location": row["location"], "batch": row.get("batch")})
		date = get_datetime(row["date"])
		quantity = as_decimal(row["quantity"])
		value = as_decimal(row["value_change"])
		if from_date and date < from_date:
			balance["opening_quantity"] += quantity
			balance["opening_value"] += value
		elif not to_date or date <= to_date:
			if quantity >= 0:
				balance["incoming_quantity"] += quantity
				balance["incoming_value"] += value
			else:
				balance["outgoing_quantity"] += abs(quantity)
				balance["outgoing_value"] += abs(value)
	data = []
	for balance in grouped.values():
		balance["balance_quantity"] = (
			balance["opening_quantity"] + balance["incoming_quantity"] - balance["outgoing_quantity"]
		)
		balance["balance_value"] = (
			balance["opening_value"] + balance["incoming_value"] - balance["outgoing_value"]
		)
		balance["valuation_rate"] = rounded(
			balance["balance_value"] / balance["balance_quantity"] if balance["balance_quantity"] else 0
		)
		data.append(
			{key: rounded(value) if hasattr(value, "quantize") else value for key, value in balance.items()}
		)
	data.sort(key=lambda row: (row["item"], row["location"], row.get("batch") or ""))
	return _balance_columns(), data


def _empty_balance():
	return {
		"opening_quantity": as_decimal(0),
		"opening_value": as_decimal(0),
		"incoming_quantity": as_decimal(0),
		"incoming_value": as_decimal(0),
		"outgoing_quantity": as_decimal(0),
		"outgoing_value": as_decimal(0),
	}


def _ledger_columns():
	return [
		{"label": _("Date"), "fieldname": "date", "fieldtype": "Datetime", "width": 150},
		{"label": _("Item"), "fieldname": "item", "fieldtype": "Link", "options": "Books Item", "width": 180},
		{
			"label": _("Location"),
			"fieldname": "location",
			"fieldtype": "Link",
			"options": "Books Location",
			"width": 130,
		},
		{
			"label": _("Batch"),
			"fieldname": "batch",
			"fieldtype": "Link",
			"options": "Books Batch",
			"width": 120,
		},
		{
			"label": _("Serial Number"),
			"fieldname": "serial_number",
			"fieldtype": "Link",
			"options": "Books Serial Number",
			"width": 140,
		},
		{"label": _("Quantity"), "fieldname": "quantity", "fieldtype": "Float", "width": 100},
		{"label": _("Balance Qty"), "fieldname": "balance_quantity", "fieldtype": "Float", "width": 110},
		{"label": _("Incoming Rate"), "fieldname": "incoming_rate", "fieldtype": "Currency", "width": 120},
		{"label": _("Valuation Rate"), "fieldname": "valuation_rate", "fieldtype": "Currency", "width": 120},
		{"label": _("Balance Value"), "fieldname": "balance_value", "fieldtype": "Currency", "width": 120},
		{"label": _("Value Change"), "fieldname": "value_change", "fieldtype": "Currency", "width": 120},
		{
			"label": _("Reference Type"),
			"fieldname": "reference_type",
			"fieldtype": "Link",
			"options": "DocType",
			"width": 170,
		},
		{
			"label": _("Reference"),
			"fieldname": "reference_name",
			"fieldtype": "Dynamic Link",
			"options": "reference_type",
			"width": 160,
		},
	]


def _balance_columns():
	return [
		{"label": _("Item"), "fieldname": "item", "fieldtype": "Link", "options": "Books Item", "width": 180},
		{
			"label": _("Location"),
			"fieldname": "location",
			"fieldtype": "Link",
			"options": "Books Location",
			"width": 130,
		},
		{
			"label": _("Batch"),
			"fieldname": "batch",
			"fieldtype": "Link",
			"options": "Books Batch",
			"width": 120,
		},
		{"label": _("Opening Qty"), "fieldname": "opening_quantity", "fieldtype": "Float", "width": 105},
		{"label": _("Opening Value"), "fieldname": "opening_value", "fieldtype": "Currency", "width": 115},
		{"label": _("In Qty"), "fieldname": "incoming_quantity", "fieldtype": "Float", "width": 90},
		{"label": _("In Value"), "fieldname": "incoming_value", "fieldtype": "Currency", "width": 110},
		{"label": _("Out Qty"), "fieldname": "outgoing_quantity", "fieldtype": "Float", "width": 90},
		{"label": _("Out Value"), "fieldname": "outgoing_value", "fieldtype": "Currency", "width": 110},
		{"label": _("Balance Qty"), "fieldname": "balance_quantity", "fieldtype": "Float", "width": 105},
		{"label": _("Balance Value"), "fieldname": "balance_value", "fieldtype": "Currency", "width": 115},
		{"label": _("Valuation Rate"), "fieldname": "valuation_rate", "fieldtype": "Currency", "width": 115},
	]
