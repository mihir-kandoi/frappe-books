from frappe_books.reporting.inventory import stock_ledger


def execute(filters=None):
	return stock_ledger(filters)
