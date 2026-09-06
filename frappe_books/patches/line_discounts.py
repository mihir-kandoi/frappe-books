"""Preserve per-unit discounts as line discounts during upgrade."""

from frappe_books.migrations import convert_line_discounts


def execute():
	convert_line_discounts()
