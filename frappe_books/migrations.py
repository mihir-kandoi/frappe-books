"""Repairs for data written before the functional PR fixes."""

from collections import defaultdict

import frappe
from frappe.query_builder.functions import Cast_, Length
from frappe.utils import getdate

from frappe_books.accounting.money import as_decimal

VOUCHER_TYPES = {
	"Books Sales Invoice",
	"Books Purchase Invoice",
	"Books Payment",
	"Books Journal Entry",
	"Books Stock Movement",
	"Books Shipment",
	"Books Purchase Receipt",
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
		dates = {}
		if voucher_type in VOUCHER_TYPES:
			dates = dict(
				frappe.get_all(
					voucher_type,
					filters={"name": ["in", list({row.voucher_no for row in rows})]},
					fields=["name", "date"],
					as_list=True,
				)
			)
		for row in rows:
			date = getdate(dates.get(row.voucher_no) or row.posting_date[:10])
			frappe.db.set_value("Books Ledger Entry", row.name, "posting_date", date, update_modified=False)


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
	from frappe_books.currency import currency_precision

	settings = frappe.get_single("Books System Settings")
	if settings.display_precision == 2:
		frappe.db.set_single_value(
			"Books System Settings", "display_precision", currency_precision(settings.currency)
		)
