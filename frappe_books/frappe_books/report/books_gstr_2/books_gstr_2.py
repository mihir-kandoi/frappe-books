from frappe_books.reporting.gstr import execute as execute_gstr


def execute(filters=None):
	return execute_gstr("GSTR-2", filters)
