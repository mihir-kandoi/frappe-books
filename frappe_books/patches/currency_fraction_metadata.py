"""Apply shared currency metadata after the earlier currency-display patch."""

from frappe_books.migrations import update_currency_display


def execute():
	update_currency_display()
