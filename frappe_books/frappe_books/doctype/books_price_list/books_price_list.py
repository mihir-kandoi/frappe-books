# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class BooksPriceList(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from frappe_books.frappe_books.doctype.books_price_list_item.books_price_list_item import (
			BooksPriceListItem,
		)

		is_enabled: DF.Check
		is_purchase: DF.Check
		is_sales: DF.Check
		price_list_item: DF.Table[BooksPriceListItem]
	# end: auto-generated types

	_DOCTYPE_NAME = "Books Price List"
