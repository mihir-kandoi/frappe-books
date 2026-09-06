# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class BooksCurrency(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		fraction: DF.Data | None
		fraction_units: DF.Int
		smallest_value: DF.Currency
		symbol: DF.Data | None
	# end: auto-generated types

	_DOCTYPE_NAME = "Books Currency"
