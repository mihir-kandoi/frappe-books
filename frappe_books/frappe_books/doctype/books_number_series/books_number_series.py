# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from frappe_books.series import next_name, validate_series


class BooksNumberSeries(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		current: DF.Int
		pad_zeros: DF.Int
		reference_type: DF.Literal[
			"-",
			"SalesInvoice",
			"SalesQuote",
			"PurchaseInvoice",
			"Payment",
			"JournalEntry",
			"StockMovement",
			"Shipment",
			"PurchaseReceipt",
			"PricingRule",
		]
		start: DF.Int
	# end: auto-generated types

	def validate(self):
		validate_series(self)

	def next(self):
		return next_name(self.name)
