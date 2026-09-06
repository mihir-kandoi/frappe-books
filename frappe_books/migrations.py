"""Repairs for data written before the functional PR fixes."""

from collections import defaultdict

import frappe
from babel.numbers import is_currency
from frappe.query_builder.functions import Cast_, Length
from frappe.utils import getdate

from frappe_books.accounting.money import as_decimal
from frappe_books.currency import currency_fraction_values, currency_precision

VOUCHER_DATE_FIELDS = {
	"Books Sales Invoice": "date",
	"Books Purchase Invoice": "date",
	"Books Payment": "date",
	"Books Journal Entry": "posting_date",
	"Books Stock Movement": "date",
	"Books Shipment": "date",
	"Books Purchase Receipt": "date",
}


def normalize_ledger_dates():
	"""Repair legacy timestamp strings using the exact source voucher when available."""
	if frappe.db.db_type != "sqlite" or not frappe.db.table_exists("Books Ledger Entry"):
		return
	ledger = frappe.qb.DocType("Books Ledger Entry")
	stored_date = Cast_(ledger.posting_date, "text")
	entries = (
		frappe.qb.from_(ledger)
		.select(ledger.name, stored_date.as_("posting_date"), ledger.voucher_type, ledger.voucher_no)
		.where(Length(stored_date) > 10)
	).run(as_dict=True)
	by_type = defaultdict(list)
	for entry in entries:
		if len(str(entry.posting_date or "")) > 10:
			by_type[entry.voucher_type].append(entry)
	for voucher_type, rows in by_type.items():
		dates = _voucher_dates(voucher_type, rows)
		for row in rows:
			date = getdate(dates.get(row.voucher_no) or row.posting_date[:10])
			frappe.db.set_value("Books Ledger Entry", row.name, "posting_date", date, update_modified=False)


def _voucher_dates(voucher_type, rows):
	date_field = VOUCHER_DATE_FIELDS.get(voucher_type)
	if not date_field:
		return {}
	return dict(
		frappe.get_all(
			voucher_type,
			filters={"name": ["in", list({row.voucher_no for row in rows})]},
			fields=["name", date_field],
			as_list=True,
		)
	)


def convert_line_discounts():
	"""Preserve existing invoice values when flat discounts become line amounts."""
	for doctype in ("Books Sales Invoice Item", "Books Purchase Invoice Item", "Books Sales Quote Item"):
		rows = frappe.get_all(
			doctype,
			filters={"set_item_discount_amount": 1},
			fields=["name", "quantity", "item_discount_amount"],
		)
		for row in rows:
			amount = as_decimal(row.item_discount_amount) * abs(as_decimal(row.quantity))
			frappe.db.set_value(doctype, row.name, "item_discount_amount", amount, update_modified=False)


def update_currency_display():
	update_currency_fractions()
	settings = frappe.get_single("Books System Settings")
	if settings.display_precision == 2:
		frappe.db.set_single_value(
			"Books System Settings", "display_precision", currency_precision(settings.currency)
		)


def update_currency_fractions():
	"""Repair standard currency defaults while preserving larger cash increments."""
	for currency in frappe.get_all("Books Currency", fields=["name", "fraction_units", "smallest_value"]):
		if not is_currency(currency.name):
			continue
		values = currency_fraction_values(currency.name)
		if as_decimal(currency.smallest_value) >= values["smallest_value"]:
			values.pop("smallest_value")
		changes = {field: value for field, value in values.items() if currency.get(field) != value}
		if changes:
			frappe.db.set_value("Books Currency", currency.name, changes, update_modified=False)
