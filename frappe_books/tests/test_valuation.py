"""FIFO valuation of the stock ledger."""

from decimal import Decimal

from frappe.tests import IntegrationTestCase

from frappe_books.frappe_books.doctype.books_stock_movement.test_books_stock_movement import (
	make_movement,
)
from frappe_books.inventory.valuation import computed_entries
from frappe_books.tests.accounting import make_account, make_item


class IntegrationTestValuation(IntegrationTestCase):
	def test_fifo_balances_follow_receipts_and_issues(self):
		income = make_account("Valuation Income", root_type="Income")
		expense = make_account("Valuation Expense", root_type="Expense")
		item = make_item(income.name, expense.name, track_item=1)
		make_movement(
			"MaterialReceipt",
			[{"item": item.name, "to_location": "Stores", "quantity": 5, "rate": 10}],
		).submit()
		make_movement(
			"MaterialIssue",
			[{"item": item.name, "from_location": "Stores", "quantity": 2, "rate": 10}],
		).submit()

		entries = computed_entries([item.name])

		self.assertEqual(len(entries), 2)
		self.assertEqual(entries[-1]["balance_quantity"], 3)
		self.assertEqual(Decimal(str(entries[-1]["balance_value"])), Decimal("30.00"))
		self.assertEqual(Decimal(str(entries[-1]["valuation_rate"])), Decimal("10.00"))
