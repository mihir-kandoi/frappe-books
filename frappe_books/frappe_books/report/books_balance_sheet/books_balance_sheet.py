from frappe_books.reporting.financial import balance_sheet


def execute(filters=None):
	return balance_sheet(filters)
