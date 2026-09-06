# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from frappe_books.commerce.pos import activate_opening_shift, prepare_opening_shift, prevent_open_shift_delete


class BooksPosOpeningShift(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from frappe_books.frappe_books.doctype.books_opening_amounts.books_opening_amounts import (
			BooksOpeningAmounts,
		)
		from frappe_books.frappe_books.doctype.books_opening_cash.books_opening_cash import (
			BooksOpeningCash,
		)

		opening_amounts: DF.Table[BooksOpeningAmounts]
		opening_cash: DF.Table[BooksOpeningCash]
		opening_date: DF.Datetime | None
	# end: auto-generated types

	_DOCTYPE_NAME = "Books Pos Opening Shift"

	def before_insert(self):
		prepare_opening_shift(self)

	def after_insert(self):
		activate_opening_shift(self)

	def on_trash(self):
		prevent_open_shift_delete(self)
