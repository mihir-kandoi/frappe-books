# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from frappe_books.setup_service import run_setup


class IntegrationTestBooksSetupWizard(IntegrationTestCase):
	def test_rejects_invalid_fiscal_year(self):
		wizard = frappe.get_single("Books Setup Wizard")
		wizard.update(
			{
				"company_name": "Test Books Company",
				"fullname": "Test Owner",
				"email": "owner@example.com",
				"country": "India",
				"currency": "INR",
				"bank_name": "Test Primary Bank",
				"chart_of_accounts": "Standard",
				"fiscal_year_start": "2027-04-01",
				"fiscal_year_end": "2027-03-31",
			}
		)
		with self.assertRaises(frappe.ValidationError):
			wizard.save(ignore_permissions=True)

	def test_setup_creates_standard_accounts_and_defaults(self):
		wizard = frappe.get_single("Books Setup Wizard")
		wizard.update(
			{
				"company_name": "Test Books Company",
				"fullname": "Test Owner",
				"email": "owner@example.com",
				"country": "India",
				"currency": "INR",
				"bank_name": "Test Primary Bank",
				"chart_of_accounts": "Standard",
				"fiscal_year_start": "2026-04-01",
				"fiscal_year_end": "2027-03-31",
			}
		)
		wizard.save(ignore_permissions=True)
		run_setup(wizard)

		self.assertTrue(frappe.db.exists("Books Account", "Debtors"))
		self.assertEqual(
			frappe.db.get_value("Books Account", "Test Primary Bank", "parent_books_account"),
			"Bank Accounts",
		)
		self.assertEqual(
			frappe.db.get_single_value("Books Accounting Settings", "company_name"),
			"Test Books Company",
		)
		self.assertEqual(
			frappe.db.get_single_value("Books Defaults", "sales_invoice_number_series"),
			"SINV-",
		)
		self.assertTrue(frappe.db.exists("Books Currency", "INR"))
		self.assertTrue(frappe.db.exists("Books Account", "CGST"))
		self.assertTrue(frappe.db.exists("Books Tax", "GST-18"))
		gst = frappe.get_doc("Books Tax", "GST-18")
		self.assertEqual([(row.account, row.rate) for row in gst.details], [("CGST", 9), ("SGST", 9)])
