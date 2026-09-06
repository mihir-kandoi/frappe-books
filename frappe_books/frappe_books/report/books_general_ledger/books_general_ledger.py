from frappe_books.reporting.financial import general_ledger


def execute(filters=None):
	return general_ledger(filters)
