# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class BooksPrintTemplate(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		height: DF.Float
		is_custom: DF.Check
		template: DF.Code
		type: DF.Autocomplete
		width: DF.Float
	# end: auto-generated types

	_DOCTYPE_NAME = "Books Print Template"
