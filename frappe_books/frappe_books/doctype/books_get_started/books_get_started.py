# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class BooksGetStarted(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		bill_created: DF.Check
		chart_of_accounts_reviewed: DF.Check
		company_setup: DF.Check
		customer_created: DF.Check
		invoice_created: DF.Check
		onboarding_complete: DF.Check
		opening_balance_checked: DF.Check
		print_setup: DF.Check
		purchase_item_created: DF.Check
		sales_item_created: DF.Check
		supplier_created: DF.Check
		system_setup: DF.Check
		taxes_added: DF.Check
	# end: auto-generated types

	_DOCTYPE_NAME = "Books Get Started"
