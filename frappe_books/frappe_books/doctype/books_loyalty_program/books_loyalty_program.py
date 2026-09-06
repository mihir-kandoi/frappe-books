# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from frappe_books.commerce.loyalty import validate_program


class BooksLoyaltyProgram(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from frappe_books.frappe_books.doctype.books_collection_rules_items.books_collection_rules_items import (
			BooksCollectionRulesItems,
		)

		collection_rules: DF.Table[BooksCollectionRulesItems]
		conversion_factor: DF.Float
		expense_account: DF.Link
		expiry_duration: DF.Int
		from_date: DF.Date
		is_enabled: DF.Check
		maximum_use: DF.Int
		to_date: DF.Date
		used: DF.Int
	# end: auto-generated types

	_DOCTYPE_NAME = "Books Loyalty Program"

	def validate(self):
		validate_program(self)
