"""Integration coverage for invoice-driven stock transfers."""

import frappe
from frappe.tests import IntegrationTestCase

from frappe_books.frappe_books.doctype.books_stock_movement.test_books_stock_movement import (
	make_movement,
)
from frappe_books.inventory.stock import stock_quantity
from frappe_books.tests.accounting import make_account, make_invoice, make_item, make_party, unique_name


class IntegrationTestAutoTransfer(IntegrationTestCase):
	def test_pos_shipment_uses_pos_inventory(self):
		self._check_pos_inventory(use_profile=False)

	def test_pos_shipment_uses_profile_inventory(self):
		self._check_pos_inventory(use_profile=True)

	def test_pos_shipment_still_rejects_insufficient_inventory(self):
		invoice, item, location = self._make_pos_invoice(use_profile=True, opening_quantity=1)
		with self.assertRaisesRegex(frappe.ValidationError, f"at {location.name}:"):
			invoice.submit()
		self.assertEqual(stock_quantity(item.name, location.name), 1)
		self.assertEqual(stock_quantity(item.name, "Stores"), 0)

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

	def _check_pos_inventory(self, use_profile):
		invoice, item, location = self._make_pos_invoice(use_profile)
		invoice.submit()
		shipment = frappe.get_doc("Books Shipment", invoice.reload().back_reference)
		self.assertEqual(shipment.docstatus, 1)
		self.assertEqual(shipment.items[0].location, location.name)
		self.assertEqual(stock_quantity(item.name, location.name), 3)
		self.assertEqual(stock_quantity(item.name, "Stores"), 0)
		invoice.cancel()
		self.assertEqual(stock_quantity(item.name, location.name), 5)

	def _make_pos_invoice(self, use_profile, opening_quantity=5):
		receivable = make_account("POS Receivable", account_type="Receivable")
		income = make_account("POS Sales", root_type="Income", account_type="Income Account")
		cogs = make_account("POS COGS", root_type="Expense", account_type="Cost of Goods Sold")
		stock = make_account("POS Stock", account_type="Stock")
		received = make_account("POS Received", root_type="Liability")
		frappe.db.set_single_value("Books Accounting Settings", "discount_account", cogs.name)
		frappe.db.set_single_value("Books Inventory Settings", "cost_of_goods_sold", cogs.name)
		frappe.db.set_single_value("Books Inventory Settings", "stock_in_hand", stock.name)
		frappe.db.set_single_value("Books Inventory Settings", "stock_received_but_not_billed", received.name)
		frappe.db.set_single_value("Books Defaults", "shipment_location", "Stores")
		location = frappe.get_doc({"doctype": "Books Location", "name": unique_name("POS Shelf")}).insert()
		profile = None
		if use_profile:
			profile = frappe.get_doc(
				{
					"doctype": "Books Pos Profile",
					"name": unique_name("POS Profile"),
					"inventory": location.name,
				}
			).insert()
		frappe.db.set_single_value("Books Pos Settings", "pos_profile", profile.name if profile else "")
		frappe.db.set_single_value("Books Pos Settings", "inventory", "Stores" if profile else location.name)
		party = make_party(receivable.name)
		item = make_item(income.name, cogs.name, track_item=1, rate=10)
		make_movement(
			"MaterialReceipt",
			[{"item": item.name, "to_location": location.name, "quantity": opening_quantity, "rate": 10}],
		).submit()
		invoice = make_invoice(
			"Books Sales Invoice",
			party.name,
			receivable.name,
			item.name,
			income.name,
			is_pos=1,
			make_auto_stock_transfer=1,
		)
		return invoice, item, location
