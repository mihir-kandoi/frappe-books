"""Draft common follow-up documents from Books transactions."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import now_datetime

from frappe_books.accounting.money import as_decimal

INVOICE_DOCTYPES = {"Books Sales Invoice", "Books Purchase Invoice"}
ITEM_FIELDS = (
	"item",
	"item_code",
	"description",
	"rate",
	"is_manual_rate",
	"transfer_unit",
	"transfer_quantity",
	"unit",
	"batch",
	"quantity",
	"unit_conversion_factor",
	"account",
	"tax",
	"set_item_discount_amount",
	"item_discount_amount",
	"item_discount_percent",
	"hsn_code",
	"serial_number",
)


@frappe.whitelist()
def make_payment(invoice_doctype: str, invoice_name: str) -> dict:
	"""Return an unsaved payment allocated to one submitted invoice."""
	invoice = _submitted_document(invoice_doctype, invoice_name, INVOICE_DOCTYPES)
	outstanding = abs(as_decimal(invoice.outstanding_amount))
	if outstanding <= 0:
		frappe.throw(_("This invoice has no outstanding amount."))

	is_sales = invoice.doctype == "Books Sales Invoice"
	is_return = bool(invoice.return_against)
	default_field = "sales_payment_account" if is_sales else "purchase_payment_account"
	payment_account = frappe.db.get_single_value("Books Defaults", default_field)
	payment_method = "Cash"
	if not payment_account:
		payment_account = frappe.db.get_value("Books Payment Method", payment_method, "account")
	if not payment_account:
		frappe.throw(_("Set a default payment account in Books Defaults."))

	payment = frappe.new_doc("Books Payment")
	payment.update(
		{
			"party": invoice.party,
			"date": now_datetime(),
			"payment_type": "Receive" if is_sales != is_return else "Pay",
			"account": invoice.account,
			"payment_account": payment_account,
			"payment_method": payment_method,
			"amount": outstanding,
		}
	)
	payment.append(
		"payment_references",
		{
			"reference_type": invoice.doctype,
			"reference_name": invoice.name,
			"amount": outstanding,
		},
	)
	return payment.as_dict()


@frappe.whitelist()
def make_return(invoice_doctype: str, invoice_name: str) -> dict:
	"""Return an unsaved full credit note or purchase return."""
	invoice = _submitted_document(invoice_doctype, invoice_name, INVOICE_DOCTYPES)
	if invoice.return_against:
		frappe.throw(_("Create a return from the original invoice."))
	if invoice.is_fully_returned:
		frappe.throw(_("This invoice is already fully returned."))

	return_invoice = frappe.new_doc(invoice.doctype)
	return_invoice.update(
		{
			"party": invoice.party,
			"account": invoice.account,
			"date": now_datetime(),
			"price_list": invoice.get("price_list"),
			"currency": invoice.get("currency"),
			"exchange_rate": invoice.get("exchange_rate") or 1,
			"entry_currency": invoice.get("entry_currency"),
			"terms": invoice.get("terms"),
			"return_against": invoice.name,
			"make_auto_stock_transfer": invoice.get("make_auto_stock_transfer"),
		}
	)
	for source_row in invoice.items:
		values = _copy_item_values(source_row)
		values["quantity"] = -abs(as_decimal(source_row.quantity))
		values["transfer_quantity"] = -abs(as_decimal(source_row.transfer_quantity))
		return_invoice.append("items", values)
	return return_invoice.as_dict()


@frappe.whitelist()
def make_sales_invoice(quote_name: str) -> dict:
	"""Return an unsaved sales invoice copied from a submitted quote."""
	quote = _submitted_document("Books Sales Quote", quote_name, {"Books Sales Quote"})
	invoice = frappe.new_doc("Books Sales Invoice")
	invoice.update(
		{
			"party": quote.party,
			"account": frappe.db.get_value("Books Party", quote.party, "default_account"),
			"date": now_datetime(),
			"price_list": quote.get("price_list"),
			"currency": quote.get("currency"),
			"exchange_rate": quote.get("exchange_rate") or 1,
			"entry_currency": quote.get("entry_currency"),
			"terms": quote.get("terms"),
			"discount_after_tax": quote.get("discount_after_tax"),
			"set_discount_amount": quote.get("set_discount_amount"),
			"discount_amount": quote.get("discount_amount"),
			"discount_percent": quote.get("discount_percent"),
			"quote": quote.name,
		}
	)
	for source_row in quote.items:
		invoice.append("items", _copy_item_values(source_row))
	return invoice.as_dict()


def _submitted_document(doctype: str, name: str, allowed_doctypes: set[str]):
	if doctype not in allowed_doctypes:
		frappe.throw(_("Unsupported document type."))
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("read")
	if doc.docstatus != 1:
		frappe.throw(_("Submit {0} before creating a follow-up document.").format(doc.name))
	return doc


def _copy_item_values(source_row) -> dict:
	return {
		fieldname: source_row.get(fieldname)
		for fieldname in ITEM_FIELDS
		if source_row.get(fieldname) is not None
	}
