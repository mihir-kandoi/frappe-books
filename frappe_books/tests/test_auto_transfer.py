"""Integration coverage for invoice-driven stock transfers."""

import frappe
from frappe.tests import IntegrationTestCase

from frappe_books.frappe_books.doctype.books_stock_movement.test_books_stock_movement import (
	make_movement,
)
from frappe_books.inventory.stock import stock_quantity
from frappe_books.tests.accounting import make_account, make_invoice, make_item, make_party


class IntegrationTestAutoTransfer(IntegrationTestCase):
	def test_sales_invoice_creates_and_cancels_shipment(self):
		receivable = make_account("Auto Receivable", account_type="Receivable")
		income = make_account("Auto Sales", root_type="Income", account_type="Income Account")
		cogs = make_account("Auto COGS", root_type="Expense", account_type="Cost of Goods Sold")
		stock = make_account("Auto Stock", account_type="Stock")
		received = make_account("Auto Received", root_type="Liability")
		frappe.db.set_single_value("Books Accounting Settings", "discount_account", cogs.name)
		frappe.db.set_single_value("Books Inventory Settings", "cost_of_goods_sold", cogs.name)
		frappe.db.set_single_value("Books Inventory Settings", "stock_in_hand", stock.name)
		frappe.db.set_single_value("Books Inventory Settings", "stock_received_but_not_billed", received.name)
		frappe.db.set_single_value("Books Defaults", "shipment_location", "Stores")
		party = make_party(receivable.name)
		item = make_item(income.name, cogs.name, track_item=1, rate=10)
		receipt = make_movement(
			"MaterialReceipt",
			[{"item": item.name, "to_location": "Stores", "quantity": 5, "rate": 10}],
		)
		receipt.submit()

		invoice = make_invoice(
			"Books Sales Invoice",
			party.name,
			receivable.name,
			item.name,
			income.name,
			make_auto_stock_transfer=1,
		)
		invoice.submit()

		shipment = frappe.get_doc("Books Shipment", invoice.reload().back_reference)
		self.assertEqual(shipment.docstatus, 1)
		self.assertEqual(shipment.back_reference, invoice.name)
		self.assertEqual(stock_quantity(item.name, "Stores"), 3)

		invoice.cancel()
		self.assertEqual(frappe.db.get_value("Books Shipment", shipment.name, "docstatus"), 2)
		self.assertEqual(stock_quantity(item.name, "Stores"), 5)
