# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from frappe_books.commerce.pos import close_shift, prepare_closing_shift


class BooksPosClosingShift(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from frappe_books.frappe_books.doctype.books_closing_amounts.books_closing_amounts import (
			BooksClosingAmounts,
		)
		from frappe_books.frappe_books.doctype.books_closing_cash.books_closing_cash import (
			BooksClosingCash,
		)

		closing_amounts: DF.Table[BooksClosingAmounts]
		closing_cash: DF.Table[BooksClosingCash]
		closing_date: DF.Datetime | None
		opening_shift: DF.Link | None
	# end: auto-generated types

	_DOCTYPE_NAME = "Books Pos Closing Shift"

	def before_insert(self):
		prepare_closing_shift(self)

	def after_insert(self):
		close_shift(self)
