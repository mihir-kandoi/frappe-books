# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from decimal import Decimal

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import now_datetime

from frappe_books.tests.accounting import (
	ledger_entries,
	make_account,
	make_invoice,
	make_item,
	make_party,
)


class IntegrationTestBooksPayment(IntegrationTestCase):
	def test_payment_allocates_and_cancel_restores_invoice(self):
		receivable = make_account("Receivable", account_type="Receivable")
		cash = make_account("Cash", account_type="Cash")
		income = make_account("Income", root_type="Income", account_type="Income Account")
		expense = make_account("Expense", root_type="Expense", account_type="Expense Account")
		party = make_party(receivable.name)
		item = make_item(income.name, expense.name)
		invoice = make_invoice(
			"Books Sales Invoice",
			party.name,
			receivable.name,
			item.name,
			income.name,
		)
		invoice.items[0].item_discount_percent = 0
		invoice.save()
		invoice.submit()

		payment = frappe.get_doc(
			{
				"doctype": "Books Payment",
				"party": party.name,
				"date": now_datetime(),
				"payment_type": "Receive",
				"account": receivable.name,
				"payment_account": cash.name,
				"payment_method": "Cash",
				"amount": invoice.base_grand_total,
				"payment_references": [
					{
						"reference_type": invoice.doctype,
						"reference_name": invoice.name,
						"amount": invoice.base_grand_total,
					}
				],
			}
		).insert()
		payment.submit()

		self.assertEqual(invoice.db_get("outstanding_amount"), 0)
		entries = ledger_entries(payment.doctype, payment.name)
		self.assertEqual(sum(Decimal(str(row.debit or 0)) for row in entries), Decimal("200"))
		self.assertEqual(sum(Decimal(str(row.credit or 0)) for row in entries), Decimal("200"))

		payment.cancel()
		self.assertEqual(Decimal(str(invoice.db_get("outstanding_amount"))), Decimal("200"))

	def test_pay_credits_cash_and_debits_payable(self):
		payable = make_account("Payable", root_type="Liability", account_type="Payable")
		cash = make_account("Cash", account_type="Cash")
		income = make_account("Income", root_type="Income", account_type="Income Account")
		expense = make_account("Expense", root_type="Expense", account_type="Expense Account")
		party = make_party(payable.name, role="Supplier")
		item = make_item(income.name, expense.name)
		invoice = make_invoice(
			"Books Purchase Invoice",
			party.name,
			payable.name,
			item.name,
			expense.name,
		)
		invoice.items[0].item_discount_percent = 0
		invoice.save().submit()

		payment = frappe.get_doc(
			{
				"doctype": "Books Payment",
				"party": party.name,
				"date": now_datetime(),
				"payment_type": "Pay",
				"account": payable.name,
				"payment_account": cash.name,
				"payment_method": "Cash",
				"amount": invoice.base_grand_total,
				"payment_references": [
					{
						"reference_type": invoice.doctype,
						"reference_name": invoice.name,
						"amount": invoice.base_grand_total,
					}
				],
			}
		).insert()
		payment.submit()

		entries = ledger_entries(payment.doctype, payment.name)
		payable_entry = next(row for row in entries if row.account == payable.name)
		cash_entry = next(row for row in entries if row.account == cash.name)
		self.assertEqual(Decimal(str(payable_entry.debit)), Decimal("200"))
		self.assertEqual(Decimal(str(cash_entry.credit)), Decimal("200"))
