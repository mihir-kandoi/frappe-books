# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class BooksStockLedgerEntry(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		batch: DF.Link | None
		date: DF.Datetime | None
		item: DF.Link | None
		location: DF.Link | None
		name: DF.Int | None
		quantity: DF.Float
		rate: DF.Currency
		reference_name: DF.DynamicLink | None
		reference_type: DF.Link | None
		serial_number: DF.Link | None
	# end: auto-generated types

	_DOCTYPE_NAME = "Books Stock Ledger Entry"
