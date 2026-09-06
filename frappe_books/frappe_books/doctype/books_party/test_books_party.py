# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from frappe_books.tests.accounting import unique_name

# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]


class IntegrationTestBooksParty(IntegrationTestCase):
	def test_registered_party_requires_valid_gstin(self):
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "Books Party",
					"name": unique_name("GST Party"),
					"role": "Customer",
					"gst_type": "Registered Regular",
					"gstin": "invalid",
				}
			).insert()

		party = frappe.get_doc(
			{
				"doctype": "Books Party",
				"name": unique_name("GST Party"),
				"role": "Customer",
				"gst_type": "Registered Regular",
				"gstin": "27AAAAA0000A1Z5",
			}
		).insert()
		self.assertEqual(party.gstin, "27AAAAA0000A1Z5")

	def test_unregistered_party_clears_gstin(self):
		party = frappe.get_doc(
			{
				"doctype": "Books Party",
				"name": unique_name("GST Party"),
				"role": "Customer",
				"gst_type": "Unregistered",
				"gstin": "27AAAAA0000A1Z5",
			}
		).insert()
		self.assertFalse(party.gstin)
