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


class IntegrationTestBooksAddress(IntegrationTestCase):
	def test_address_display_and_indian_place_of_supply(self):
		address = frappe.get_doc(
			{
				"doctype": "Books Address",
				"name": unique_name("Office"),
				"address_line1": "42 Market Road",
				"city": "Mumbai",
				"state": "Maharashtra",
				"country": "India",
				"postal_code": "400001",
			}
		).insert()
		self.assertEqual(address.pos, "Maharashtra")
		self.assertEqual(address.address_display, "42 Market Road, Mumbai, Maharashtra, India, 400001")
