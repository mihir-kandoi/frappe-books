"""Native Frappe print formats for Books documents."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils.print_utils import get_print

from frappe_books.tests.accounting import make_account, make_invoice, make_item, make_party


class IntegrationTestPrinting(IntegrationTestCase):
	def test_native_print_format_renders_invoice(self):
		receivable = make_account("Print Receivable", account_type="Receivable")
		income = make_account("Print Sales", root_type="Income", account_type="Income Account")
		expense = make_account("Print Expense", root_type="Expense", account_type="Expense Account")
		frappe.db.set_single_value("Books Accounting Settings", "discount_account", expense.name)
		party = make_party(receivable.name)
		item = make_item(income.name, expense.name)
		invoice = make_invoice("Books Sales Invoice", party.name, receivable.name, item.name, income.name)
		invoice.submit()

		html = get_print(invoice.doctype, invoice.name, print_format="Frappe Books - Sales Invoice")

		self.assertIn(invoice.name, html)
		self.assertIn(party.name, html)
		self.assertIn("Grand Total", html)
