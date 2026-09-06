# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class BooksInventorySettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		cost_of_goods_sold: DF.Link | None
		default_location: DF.Link | None
		enable_barcodes: DF.Check
		enable_batches: DF.Check
		enable_point_of_sale: DF.Check
		enable_serial_number: DF.Check
		enable_uom_conversions: DF.Check
		stock_in_hand: DF.Link | None
		stock_received_but_not_billed: DF.Link | None
	# end: auto-generated types

	_DOCTYPE_NAME = "Books Inventory Settings"
