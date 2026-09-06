# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from decimal import Decimal

from frappe.tests import IntegrationTestCase

from frappe_books.tests.accounting import (
	ledger_entries,
	make_account,
	make_invoice,
	make_item,
	make_party,
	make_tax,
)


class IntegrationTestBooksPurchaseInvoice(IntegrationTestCase):
	def test_purchase_posts_expense_tax_and_payable(self):
		payable = make_account("Payable", root_type="Liability", account_type="Payable")
		income = make_account("Income", root_type="Income", account_type="Income Account")
		expense = make_account("Purchase", root_type="Expense", account_type="Expense Account")
		tax_account = make_account("Input Tax", root_type="Asset", account_type="Tax")
		party = make_party(payable.name, role="Supplier")
		tax = make_tax(tax_account.name)
		item = make_item(income.name, expense.name, tax.name)
		invoice = make_invoice(
			"Books Purchase Invoice",
			party.name,
			payable.name,
			item.name,
			expense.name,
		)
		invoice.items[0].item_discount_percent = 0
		invoice.save()
		invoice.submit()

		entries = ledger_entries(invoice.doctype, invoice.name)
		self.assertEqual(sum(Decimal(str(row.debit or 0)) for row in entries), Decimal("220"))
		self.assertEqual(sum(Decimal(str(row.credit or 0)) for row in entries), Decimal("220"))
		self.assertEqual(Decimal(str(invoice.db_get("outstanding_amount"))), Decimal("220"))
