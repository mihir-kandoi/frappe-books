# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class BooksCustomField(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		default: DF.Data | None
		fieldname: DF.Data
		fieldtype: DF.Literal[
			"Data",
			"Select",
			"Link",
			"Date",
			"Datetime",
			"Table",
			"AutoComplete",
			"Check",
			"AttachImage",
			"DynamicLink",
			"Int",
			"Float",
			"Currency",
			"Text",
			"Color",
			"Attachment",
		]
		is_required: DF.Check
		label: DF.Data
		options: DF.Text | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		references: DF.Autocomplete | None
		section: DF.Data | None
		tab: DF.Data | None
		target: DF.Autocomplete | None
	# end: auto-generated types

	_DOCTYPE_NAME = "Books Custom Field"
