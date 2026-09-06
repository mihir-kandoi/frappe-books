"""Set up a Books company on the current Frappe site."""

import frappe

from frappe_books.coa import ensure_bank_account, ensure_discount_account, ensure_standard_coa
from frappe_books.currency import currency_precision
from frappe_books.regional import ensure_regional_records
from frappe_books.setup import ensure_default_records, ensure_number_series, ensure_roles

SERIES_DEFAULTS = {
	"sales_invoice_number_series": "SINV-",
	"purchase_invoice_number_series": "PINV-",
	"journal_entry_number_series": "JV-",
	"payment_number_series": "PAY-",
	"stock_movement_number_series": "SMOV-",
	"shipment_number_series": "SHPM-",
	"purchase_receipt_number_series": "PREC-",
	"sales_quote_number_series": "SQUOT-",
}


def run_setup(wizard):
	ensure_roles()
	ensure_number_series()
	ensure_default_records()
	ensure_standard_coa()
	ensure_regional_records(wizard.country)
	bank_account = ensure_bank_account(wizard.bank_name)
	discount_account = ensure_discount_account()
	ensure_currency(wizard.currency)
	_update_accounting_settings(wizard, discount_account)
	_update_system_settings(wizard)
	_update_print_settings(wizard)
	_update_inventory_settings()
	_update_pos_settings()
	_update_defaults(bank_account)
	frappe.db.set_single_value("Books Setup Wizard", "completed", 1)
	return {"setup_complete": True, "bank_account": bank_account}


def ensure_currency(currency):
	if not currency or frappe.db.exists("Books Currency", currency):
		return
	core_currency = (
		frappe.db.get_value(
			"Currency",
			currency,
			["symbol", "fraction", "fraction_units", "smallest_currency_fraction_value"],
			as_dict=True,
		)
		or {}
	)
	frappe.get_doc(
		{
			"doctype": "Books Currency",
			"name": currency,
			"symbol": core_currency.get("symbol") or currency,
			"fraction": core_currency.get("fraction") or "Cent",
			"fraction_units": 0 if currency == "JPY" else core_currency.get("fraction_units", 100),
			"smallest_value": 1
			if currency == "JPY"
			else (
				core_currency.get("smallest_currency_fraction_value") or 10 ** -currency_precision(currency)
			),
		}
	).insert(ignore_permissions=True)


def _update_accounting_settings(wizard, discount_account):
	settings = frappe.get_single("Books Accounting Settings")
	settings.update(
		{
			"fullname": wizard.fullname,
			"company_name": wizard.company_name,
			"bank_name": wizard.bank_name,
			"country": wizard.country,
			"email": wizard.email,
			"write_off_account": "Write Off",
			"round_off_account": "Round Off",
			"discount_account": discount_account,
			"fiscal_year_start": wizard.fiscal_year_start,
			"fiscal_year_end": wizard.fiscal_year_end,
			"setup_complete": 1,
		}
	)
	settings.save(ignore_permissions=True)


def _update_print_settings(wizard):
	settings = frappe.get_single("Books Print Settings")
	settings.update(
		{
			"logo": wizard.logo,
			"company_name": wizard.company_name,
			"email": wizard.email,
			"display_logo": bool(wizard.logo),
		}
	)
	settings.save(ignore_permissions=True)


def _update_system_settings(wizard):
	settings = frappe.get_single("Books System Settings")
	settings.update(
		{
			"currency": wizard.currency,
			"display_precision": currency_precision(wizard.currency),
			"country_code": _country_code(wizard.country),
			"locale": "en-IN" if wizard.country == "India" else "en-US",
		}
	)
	settings.save(ignore_permissions=True)


def _update_inventory_settings():
	settings = frappe.get_single("Books Inventory Settings")
	settings.update(
		{
			"default_location": "Stores",
			"stock_in_hand": "Stock In Hand",
			"stock_received_but_not_billed": "Stock Received But Not Billed",
			"cost_of_goods_sold": "Cost of Goods Sold",
		}
	)
	settings.save(ignore_permissions=True)


def _update_pos_settings():
	settings = frappe.get_single("Books Pos Settings")
	settings.update(
		{
			"inventory": "Stores",
			"cash_account": "Cash",
			"write_off_account": "Write Off",
			"default_account": "Debtors",
		}
	)
	settings.save(ignore_permissions=True)
	frappe.db.set_value("Books Payment Method", "Cash", "account", "Cash", update_modified=False)


def _update_defaults(bank_account):
	defaults = frappe.get_single("Books Defaults")
	defaults.update(
		{
			"sales_payment_account": "Cash",
			"purchase_payment_account": bank_account,
			"shipment_location": "Stores",
			"purchase_receipt_location": "Stores",
			**SERIES_DEFAULTS,
		}
	)
	defaults.save(ignore_permissions=True)


def _country_code(country):
	return {"India": "in", "Switzerland": "ch"}.get(country, "-")
