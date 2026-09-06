from frappe_books.reporting.financial import profit_and_loss


def execute(filters=None):
	return profit_and_loss(filters)
