"""Integration coverage for promotions, loyalty programs, and POS shifts."""

from decimal import Decimal
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate, now_datetime, nowdate

from frappe_books.commerce.loyalty import expire_programs_and_points
from frappe_books.commerce.pos import transacted_amounts
from frappe_books.frappe_books.doctype.books_stock_movement.test_books_stock_movement import (
	make_movement,
)
from frappe_books.inventory.stock import stock_quantity
from frappe_books.tests.accounting import (
	ledger_entries,
	make_account,
	make_invoice,
	make_item,
	make_party,
	unique_name,
)
from frappe_books.ui_bridge.bespoke import BooksBespokeQueries


class IntegrationTestCommerce(IntegrationTestCase):
	def setUp(self):
		self.receivable = make_account("Commerce Receivable", account_type="Receivable")
		self.income = make_account("Commerce Sales", root_type="Income", account_type="Income Account")
		self.expense = make_account("Commerce Expense", root_type="Expense", account_type="Expense Account")
		frappe.db.set_single_value("Books Accounting Settings", "discount_account", self.expense.name)
		self.party = make_party(self.receivable.name)
		self.item = make_item(self.income.name, self.expense.name)

	def test_price_discount_and_coupon_usage(self):
		frappe.db.set_single_value("Books Accounting Settings", "enable_pricing_rule", 1)
		rule = self._pricing_rule(
			is_coupon_code_based=1,
			price_discount_type="percentage",
			discount_percentage=25,
		)
		coupon = frappe.get_doc(
			{
				"doctype": "Books Coupon Code",
				"coupon_name": "Save Twenty Five",
				"pricing_rule": rule.name,
				"valid_from": add_days(nowdate(), -1),
				"valid_to": add_days(nowdate(), 1),
				"maximum_use": 2,
			}
		).insert()
		invoice = make_invoice(
			"Books Sales Invoice",
			self.party.name,
			self.receivable.name,
			self.item.name,
			self.income.name,
			coupons=[{"coupons": coupon.name}],
		)

		self.assertEqual(coupon.name, "SAVETWEN")
		self.assertEqual(Decimal(str(invoice.grand_total)), Decimal("150"))
		self.assertEqual(invoice.items[0].pricing_rule, rule.name)
		invoice.submit()
		self.assertEqual(frappe.db.get_value("Books Coupon Code", coupon.name, "used"), 1)
		invoice.cancel()
		self.assertEqual(frappe.db.get_value("Books Coupon Code", coupon.name, "used"), 0)

	def test_coupon_accepts_iso_date_values(self):
		valid_from = getdate(add_days(nowdate(), -1))
		valid_to = getdate(add_days(nowdate(), 30))
		rule = self._pricing_rule(
			is_coupon_code_based=1,
			price_discount_type="percentage",
			discount_percentage=10,
			valid_from=valid_from,
			valid_to=valid_to,
		)
		coupon = frappe.get_doc(
			{
				"doctype": "Books Coupon Code",
				"coupon_name": unique_name("ISO Date Coupon"),
				"pricing_rule": rule.name,
				"valid_from": valid_from.isoformat(),
				"valid_to": valid_to.isoformat(),
				"maximum_use": 1,
			}
		).insert()

		self.assertEqual(getdate(coupon.valid_from), valid_from)
		self.assertEqual(getdate(coupon.valid_to), valid_to)

	def test_product_discount_adds_free_item(self):
		frappe.db.set_single_value("Books Accounting Settings", "enable_pricing_rule", 1)
		free_item = make_item(self.income.name, self.expense.name)
		rule = self._pricing_rule(
			discount_type="Product Discount",
			free_item=free_item.name,
			free_item_quantity=1,
			free_item_unit="Unit",
		)
		invoice = make_invoice(
			"Books Sales Invoice",
			self.party.name,
			self.receivable.name,
			self.item.name,
			self.income.name,
		)

		self.assertEqual(len(invoice.items), 2)
		free_row = next(row for row in invoice.items if row.is_free_item)
		self.assertEqual(free_row.item, free_item.name)
		self.assertEqual(free_row.pricing_rule, rule.name)
		self.assertEqual(invoice.grand_total, 180)

	def test_loyalty_earning_redemption_and_cancel(self):
		program = self._loyalty_program()
		invoice = make_invoice(
			"Books Sales Invoice",
			self.party.name,
			self.receivable.name,
			self.item.name,
			self.income.name,
			loyalty_program=program.name,
		)
		invoice.submit()
		self.assertEqual(frappe.db.get_value("Books Party", self.party.name, "loyalty_points"), 180)

		redemption = make_invoice(
			"Books Sales Invoice",
			self.party.name,
			self.receivable.name,
			self.item.name,
			self.income.name,
			loyalty_program=program.name,
			redeem_loyalty_points=1,
			loyalty_points=20,
		)
		self.assertEqual(Decimal(str(redemption.grand_total)), Decimal("170"))
		redemption.submit()
		self.assertEqual(frappe.db.get_value("Books Party", self.party.name, "loyalty_points"), 160)
		entries = ledger_entries(redemption.doctype, redemption.name)
		self.assertEqual(sum(Decimal(str(row.debit or 0)) for row in entries), Decimal("200"))
		self.assertEqual(sum(Decimal(str(row.credit or 0)) for row in entries), Decimal("200"))
		redemption.cancel()
		self.assertEqual(frappe.db.get_value("Books Party", self.party.name, "loyalty_points"), 180)

	def test_expiry_job_disables_program_and_expires_points(self):
		program = self._loyalty_program()
		frappe.db.set_value(
			"Books Loyalty Program",
			program.name,
			{"from_date": add_days(nowdate(), -2), "to_date": add_days(nowdate(), -1)},
		)
		frappe.get_doc(
			{
				"doctype": "Books Loyalty Point Entry",
				"loyalty_program": program.name,
				"customer": self.party.name,
				"invoice": self._submitted_invoice().name,
				"loyalty_points": 50,
				"purchase_amount": 50,
				"posting_date": add_days(nowdate(), -2),
				"expiry_date": add_days(nowdate(), -1),
			}
		).insert()
		frappe.db.set_value("Books Party", self.party.name, "loyalty_points", 50)

		expire_programs_and_points()

		self.assertEqual(frappe.db.get_value("Books Loyalty Program", program.name, "is_enabled"), 0)
		self.assertEqual(frappe.db.get_value("Books Party", self.party.name, "loyalty_points"), 0)

	def _pricing_rule(self, **values):
		data = {
			"doctype": "Books Pricing Rule",
			"title": unique_name("Promotion"),
			"applied_items": [{"item": self.item.name, "unit": "Unit"}],
			"discount_type": "Price Discount",
			"price_discount_type": "amount",
			"discount_amount": 10,
			"priority": "10",
			**values,
		}
		return frappe.get_doc(data).insert()

	def _loyalty_program(self):
		return frappe.get_doc(
			{
				"doctype": "Books Loyalty Program",
				"name": unique_name("Rewards"),
				"from_date": add_days(nowdate(), -1),
				"to_date": add_days(nowdate(), 30),
				"conversion_factor": 0.5,
				"expiry_duration": 30,
				"expense_account": self.expense.name,
				"collection_rules": [{"tier_name": "Base", "collection_factor": 1, "minimum_total_spent": 0}],
			}
		).insert()

	def _submitted_invoice(self):
		invoice = make_invoice(
			"Books Sales Invoice",
			self.party.name,
			self.receivable.name,
			self.item.name,
			self.income.name,
		)
		invoice.submit()
		return invoice


class IntegrationTestPosShift(IntegrationTestCase):
	def setUp(self):
		self.counter = make_account("POS Counter", account_type="Cash")
		self.write_off = make_account("POS Write Off", root_type="Expense", account_type="Expense Account")
		settings = frappe.get_single("Books Pos Settings")
		settings.cash_account = self.counter.name
		settings.write_off_account = self.write_off.name
		settings.default_account = self.counter.name
		settings.is_shift_open = 0
		settings.save()
		if not frappe.db.exists("Books Account", "Cash"):
			frappe.get_doc(
				{
					"doctype": "Books Account",
					"account_name": "Cash",
					"root_type": "Asset",
					"account_type": "Cash",
				}
			).insert()
		if not frappe.db.exists("Books Payment Method", "Bank"):
			frappe.get_doc(
				{
					"doctype": "Books Payment Method",
					"name": "Bank",
					"type": "Bank",
				}
			).insert()

	def test_open_and_close_shift_reconciles_cash(self):
		with patch("frappe_books.commerce.pos._open_shift_name", return_value=None):
			opening = frappe.get_doc(
				{
					"doctype": "Books Pos Opening Shift",
					"opening_date": now_datetime(),
					"opening_cash": [{"denomination": 50, "count": 2}],
					"opening_amounts": [
						{"payment_method": "Cash", "amount": 100},
						{"payment_method": "Bank", "amount": 0},
					],
				}
			).insert()
		self.assertEqual(frappe.db.get_single_value("Books Pos Settings", "is_shift_open"), 1)

		closing = frappe.get_doc(
			{
				"doctype": "Books Pos Closing Shift",
				"opening_shift": opening.name,
				"closing_date": now_datetime(),
				"closing_cash": [{"denomination": 50, "count": 2}],
				"closing_amounts": [
					{"payment_method": "Cash", "closing_amount": 100},
					{"payment_method": "Bank", "closing_amount": 0},
				],
			}
		).insert()
		cash_row = next(row for row in closing.closing_amounts if row.payment_method == "Cash")
		self.assertEqual(cash_row.expected_amount, 100)
		self.assertEqual(cash_row.difference_amount, 0)
		self.assertEqual(frappe.db.get_single_value("Books Pos Settings", "is_shift_open"), 0)
		self.assertEqual(frappe.db.count("Books Journal Entry", {"user_remark": ["like", "POS % shift%"]}), 2)

	def test_interface_expected_amounts_match_closing_shift_totals(self):
		receivable = make_account("POS Receivable", account_type="Receivable")
		income = make_account("POS Income", root_type="Income", account_type="Income Account")
		expense = make_account("POS Expense", root_type="Expense", account_type="Expense Account")
		frappe.db.set_single_value("Books Accounting Settings", "discount_account", expense.name)
		party = make_party(receivable.name)
		item = make_item(income.name, expense.name)
		start = now_datetime()
		invoice = make_invoice(
			"Books Sales Invoice", party.name, receivable.name, item.name, income.name, is_pos=1
		)
		invoice.submit()
		self._cash_payment(invoice, party, receivable).submit()
		end = add_days(now_datetime(), 1)

		amounts = BooksBespokeQueries().pos_transacted_amount(start.isoformat(), end.isoformat())

		self.assertEqual(amounts, transacted_amounts(start, end))
		self.assertEqual(amounts["Cash"], invoice.base_grand_total)

	def _cash_payment(self, invoice, party, account):
		return frappe.get_doc(
			{
				"doctype": "Books Payment",
				"party": party.name,
				"date": now_datetime(),
				"payment_type": "Receive",
				"account": account.name,
				"payment_account": self.counter.name,
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

	def tearDown(self):
		frappe.db.set_single_value("Books Pos Settings", "is_shift_open", 0)
