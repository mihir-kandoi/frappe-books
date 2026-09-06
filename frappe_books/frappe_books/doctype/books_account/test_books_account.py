# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase


class IntegrationTestBooksAccount(IntegrationTestCase):
	def test_child_inherits_root_type_from_group(self):
		parent = make_account("Test Assets", is_group=1)
		child = make_account(
			"Test Bank",
			root_type="Income",
			parent_books_account=parent.name,
		)

		self.assertEqual(child.root_type, "Asset")

	def test_leaf_account_cannot_be_parent(self):
		parent = make_account("Test Cash")
		child = frappe.get_doc(
			{
				"doctype": "Books Account",
				"account_name": unique_name("Test Bank"),
				"root_type": "Asset",
				"parent_books_account": parent.name,
			}
		)

		self.assertRaises(frappe.ValidationError, child.insert)


def make_account(account_name, **values):
	return frappe.get_doc(
		{
			"doctype": "Books Account",
			"account_name": unique_name(account_name),
			"root_type": "Asset",
			**values,
		}
	).insert()


def unique_name(account_name):
	return f"{account_name} {frappe.generate_hash(length=8)}"
