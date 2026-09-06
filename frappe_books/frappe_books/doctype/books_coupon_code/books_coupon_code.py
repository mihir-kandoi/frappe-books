# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import re

import frappe
from frappe.model.document import Document

from frappe_books.commerce.pricing import validate_coupon


class BooksCouponCode(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		coupon_name: DF.Data
		is_enabled: DF.Check
		max_amount: DF.Currency
		maximum_use: DF.Int
		min_amount: DF.Currency
		pricing_rule: DF.Link
		used: DF.Int
		valid_from: DF.Date
		valid_to: DF.Date
	# end: auto-generated types

	_DOCTYPE_NAME = "Books Coupon Code"

	def autoname(self):
		code = re.sub(r"\s+", "", self.coupon_name or "").upper()[:8]
		if not code:
			frappe.throw("Coupon Name must contain at least one non-space character.")
		self.name = code

	def validate(self):
		validate_coupon(self)
