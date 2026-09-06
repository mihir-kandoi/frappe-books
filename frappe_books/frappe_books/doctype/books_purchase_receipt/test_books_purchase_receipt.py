# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from decimal import Decimal

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import now_datetime

from frappe_books.inventory.stock import stock_quantity
from frappe_books.tests.accounting import ledger_entries, make_account, make_item, make_party


class IntegrationTestBooksPurchaseReceipt(IntegrationTestCase):
	def test_receipt_adds_stock_and_posts_inventory_accounts(self):
		stock = make_account("Stock", account_type="Stock")
		received = make_account(
			"Received Not Billed", root_type="Liability", account_type="Stock Received But Not Billed"
		)
		cogs = make_account("COGS", root_type="Expense", account_type="Cost of Goods Sold")
		income = make_account("Income", root_type="Income")
		expense = make_account("Expense", root_type="Expense")
		payable = make_account("Payable", root_type="Liability", account_type="Payable")
		party = make_party(payable.name, role="Supplier")
		item = make_item(income.name, expense.name, track_item=1)
		set_inventory_accounts(stock.name, received.name, cogs.name)

		receipt = frappe.get_doc(
			{
				"doctype": "Books Purchase Receipt",
				"party": party.name,
				"date": now_datetime(),
				"items": [{"item": item.name, "location": "Stores", "quantity": 4, "rate": 25}],
			}
		).insert()
		receipt.submit()

		self.assertEqual(stock_quantity(item.name, "Stores"), 4)
		entries = ledger_entries(receipt.doctype, receipt.name)
		self.assertEqual(sum(Decimal(str(row.debit or 0)) for row in entries), Decimal("100"))
		self.assertEqual(sum(Decimal(str(row.credit or 0)) for row in entries), Decimal("100"))


def set_inventory_accounts(stock, received, cogs):
	frappe.db.set_single_value("Books Inventory Settings", "stock_in_hand", stock)
	frappe.db.set_single_value("Books Inventory Settings", "stock_received_but_not_billed", received)
	frappe.db.set_single_value("Books Inventory Settings", "cost_of_goods_sold", cogs)
