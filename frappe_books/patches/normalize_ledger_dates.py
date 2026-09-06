"""Repair ledger dates that early SQLite sites stored as timestamps."""

from frappe_books.migrations import normalize_ledger_dates


def execute():
	normalize_ledger_dates()
