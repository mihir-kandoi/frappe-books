# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class BooksItemEnquiry(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		contact: DF.Data | None
		customer: DF.Data | None
		description: DF.Text | None
		item: DF.Data
		name: DF.Int | None
		similar_product: DF.Data | None
	# end: auto-generated types

	_DOCTYPE_NAME = "Books Item Enquiry"
