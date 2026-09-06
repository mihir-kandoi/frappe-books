# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from decimal import Decimal

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import now_datetime

from frappe_books.frappe_books.doctype.books_purchase_receipt.test_books_purchase_receipt import (
	set_inventory_accounts,
)
from frappe_books.inventory.stock import stock_quantity
from frappe_books.tests.accounting import ledger_entries, make_account, make_item, make_party


class IntegrationTestBooksShipment(IntegrationTestCase):
	def test_shipment_removes_stock_posts_cogs_and_reverses(self):
		stock = make_account("Stock", account_type="Stock")
		received = make_account("Received", root_type="Liability")
		cogs = make_account("COGS", root_type="Expense", account_type="Cost of Goods Sold")
		income = make_account("Income", root_type="Income")
		expense = make_account("Expense", root_type="Expense")
		receivable = make_account("Receivable", account_type="Receivable")
		party = make_party(receivable.name)
		item = make_item(income.name, expense.name, track_item=1)
		set_inventory_accounts(stock.name, received.name, cogs.name)
		seed_stock(item.name, quantity=4, rate=25)

		shipment = frappe.get_doc(
			{
				"doctype": "Books Shipment",
				"party": party.name,
				"date": now_datetime(),
				"items": [{"item": item.name, "location": "Stores", "quantity": 2, "rate": 25}],
			}
		).insert()
		shipment.submit()

		self.assertEqual(stock_quantity(item.name, "Stores"), 2)
		entries = ledger_entries(shipment.doctype, shipment.name)
		self.assertEqual(sum(Decimal(str(row.debit or 0)) for row in entries), Decimal("50"))
		self.assertEqual(sum(Decimal(str(row.credit or 0)) for row in entries), Decimal("50"))

		shipment.cancel()
		self.assertEqual(stock_quantity(item.name, "Stores"), 4)
		self.assertEqual(len(ledger_entries(shipment.doctype, shipment.name)), 4)


def seed_stock(item, quantity, rate):
	movement = frappe.get_doc(
		{
			"doctype": "Books Stock Movement",
			"movement_type": "MaterialReceipt",
			"date": now_datetime(),
			"items": [{"item": item, "to_location": "Stores", "quantity": quantity, "rate": rate}],
		}
	).insert(ignore_permissions=True)
	movement.submit()
