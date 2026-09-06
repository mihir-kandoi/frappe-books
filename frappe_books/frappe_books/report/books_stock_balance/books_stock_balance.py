from frappe_books.reporting.inventory import stock_balance


def execute(filters=None):
	return stock_balance(filters)
