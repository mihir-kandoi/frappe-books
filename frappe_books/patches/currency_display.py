"""Set currency display defaults for existing companies."""

from frappe_books.migrations import update_currency_display


def execute():
	update_currency_display()
