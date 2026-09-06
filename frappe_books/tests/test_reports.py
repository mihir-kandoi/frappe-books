"""Integration coverage for native Books reports."""

from decimal import Decimal

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, now_datetime, nowdate

from frappe_books.coa import ensure_standard_coa
from frappe_books.frappe_books.doctype.books_stock_movement.test_books_stock_movement import (
	make_movement,
)
from frappe_books.regional import ensure_regional_records
from frappe_books.reporting.financial import balance_sheet, general_ledger, profit_and_loss, trial_balance
from frappe_books.reporting.gstr import execute as execute_gstr
from frappe_books.reporting.inventory import stock_balance, stock_ledger
from frappe_books.tests.accounting import make_account, make_invoice, make_item, make_party, unique_name


class IntegrationTestFinancialReports(IntegrationTestCase):
	def setUp(self):
		self.receivable = make_account("Report Receivable", account_type="Receivable")
		self.income = make_account("Report Sales", root_type="Income", account_type="Income Account")
		self.expense = make_account("Report Expense", root_type="Expense", account_type="Expense Account")
		frappe.db.set_single_value("Books Accounting Settings", "discount_account", self.expense.name)
		self.party = make_party(self.receivable.name)
		self.item = make_item(self.income.name, self.expense.name)
		self.invoice = make_invoice(
			"Books Sales Invoice",
			self.party.name,
			self.receivable.name,
			self.item.name,
			self.income.name,
		)
		self.invoice.submit()
		self.filters = {"from_date": add_days(nowdate(), -1), "to_date": add_days(nowdate(), 1)}

	def test_general_ledger_and_trial_balance(self):
		_, ledger = general_ledger({**self.filters, "account": self.receivable.name})
		self.assertEqual(len(ledger), 1)
		self.assertEqual(Decimal(str(ledger[0]["balance"])), Decimal("180.00"))

		_, trial = trial_balance(self.filters)
		receivable = next(row for row in trial if row["account"] == self.receivable.name)
		self.assertEqual(Decimal(str(receivable["closing_debit"])), Decimal("180.00"))
		self.assertEqual(Decimal(str(receivable["closing_credit"])), Decimal("0.00"))

	def test_profit_and_loss_and_balance_sheet(self):
		_, profit_rows = profit_and_loss(self.filters)
		income = next(row for row in profit_rows if row["account"] == self.income.name)
		expense = next(row for row in profit_rows if row["account"] == self.expense.name)
		self.assertEqual(Decimal(str(income["amount"])), Decimal("200.00"))
		self.assertEqual(Decimal(str(expense["amount"])), Decimal("20.00"))

		_, balance_rows = balance_sheet({"to_date": add_days(nowdate(), 1)})
		earnings = next(row for row in balance_rows if row["account"] == "Current Period Earnings")
		self.assertGreaterEqual(Decimal(str(earnings["amount"])), Decimal("180.00"))


class IntegrationTestInventoryReports(IntegrationTestCase):
	def test_fifo_stock_ledger_and_balance(self):
		income = make_account("Stock Report Income", root_type="Income")
		expense = make_account("Stock Report Expense", root_type="Expense")
		item = make_item(income.name, expense.name, track_item=1)
		receipt = make_movement(
			"MaterialReceipt",
			[{"item": item.name, "to_location": "Stores", "quantity": 5, "rate": 10}],
		)
		receipt.submit()
		issue = make_movement(
			"MaterialIssue",
			[{"item": item.name, "from_location": "Stores", "quantity": 2, "rate": 10}],
		)
		issue.submit()

		_, ledger = stock_ledger({"item": item.name, "location": "Stores"})
		self.assertEqual(len(ledger), 2)
		self.assertEqual(ledger[-1]["balance_quantity"], 3)
		self.assertEqual(Decimal(str(ledger[-1]["balance_value"])), Decimal("30.00"))

		_, balances = stock_balance({"item": item.name, "location": "Stores"})
		self.assertEqual(len(balances), 1)
		self.assertEqual(balances[0]["balance_quantity"], 3)
		self.assertEqual(Decimal(str(balances[0]["valuation_rate"])), Decimal("10.00"))


class IntegrationTestGstrReports(IntegrationTestCase):
	def test_gstr_1_uses_regional_invoice_data(self):
		ensure_standard_coa()
		ensure_regional_records("India")
		frappe.db.set_single_value("Books Accounting Settings", "gstin", "27AAAAA0000A1Z5")
		receivable = make_account("GST Receivable", account_type="Receivable")
		income = make_account("GST Sales", root_type="Income", account_type="Income Account")
		expense = make_account("GST Expense", root_type="Expense", account_type="Expense Account")
		frappe.db.set_single_value("Books Accounting Settings", "discount_account", expense.name)
		party = make_party(receivable.name)
		party.update({"gst_type": "Registered Regular", "gstin": "29AAAAA0000A1Z5"})
		party.save()
		item = make_item(income.name, expense.name, tax="IGST-18", hsn_code="1234")
		invoice = make_invoice(
			"Books Sales Invoice",
			party.name,
			receivable.name,
			item.name,
			income.name,
			date=now_datetime(),
		)
		invoice.submit()

		_, rows = execute_gstr("GSTR-1", {"transfer_type": "B2B"})
		row = next(row for row in rows if row["invoice_no"] == invoice.name)
		self.assertEqual(row["gstin"], party.gstin)
		self.assertEqual(row["place_of_supply"], "Karnataka")
		self.assertEqual(Decimal(str(row["integrated_tax"])), Decimal("32.40"))
		self.assertEqual(row["central_tax"], 0)
