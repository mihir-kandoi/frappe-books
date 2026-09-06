"""Regression coverage for document IDs returned to the linked entries panel."""

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from frappe_books.tests.accounting import make_account
from frappe_books.ui_bridge.database import BooksDatabaseBridge


class IntegrationTestLinkedEntries(IntegrationTestCase):
	def setUp(self):
		self.bridge = BooksDatabaseBridge()

	def test_numeric_record_names_are_strings_in_list_responses(self):
		for schema in ("AccountingLedgerEntry", "StockLedgerEntry", "ItemEnquiry"):
			with self.subTest(schema=schema), patch("frappe.get_list", return_value=[{"name": 193}]):
				rows = self.bridge.get_all(schema, {"fields": ["name"]})
				self.assertEqual(rows, [{"name": "193"}])

	def test_numeric_record_names_are_strings_in_document_responses(self):
		for schema, doctype in (
			("AccountingLedgerEntry", "Books Ledger Entry"),
			("StockLedgerEntry", "Books Stock Ledger Entry"),
			("ItemEnquiry", "Books Item Enquiry"),
		):
			with self.subTest(schema=schema):
				doc = frappe.get_doc({"doctype": doctype, "name": 193})
				self.assertEqual(self.bridge._to_source_document(schema, doc, ["name"]), {"name": "193"})

	def test_linked_ledger_names_can_be_used_to_fetch_display_details(self):
		account = make_account("Linked entry IDs")
		entry = frappe.get_doc(
			{
				"doctype": "Books Ledger Entry",
				"account": account.name,
				"posting_date": "2026-09-06",
				"debit": 12.5,
			}
		).insert()
		links = self.bridge.get_all(
			"AccountingLedgerEntry", {"fields": ["name", "created"], "filters": {"account": account.name}}
		)
		self.assertEqual([row["name"] for row in links], [str(entry.name)])
		details = self.bridge.get_all(
			"AccountingLedgerEntry",
			{
				"fields": ["name", "date", "account", "debit", "credit"],
				"filters": {"name": ["in", [row["name"] for row in links]]},
			},
		)
		self.assertEqual(details[0]["name"], str(entry.name))
		self.assertEqual(details[0]["debit"], 12.5)
		self.assertEqual(self.bridge.get("AccountingLedgerEntry", str(entry.name))["name"], str(entry.name))
