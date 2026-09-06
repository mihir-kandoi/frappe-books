frappe.query_reports["Books Stock Ledger"] = {
	filters: [
		{ fieldname: "from_date", label: __("From Date"), fieldtype: "Date", default: frappe.datetime.add_months(frappe.datetime.get_today(), -12) },
		{ fieldname: "to_date", label: __("To Date"), fieldtype: "Date", default: frappe.datetime.get_today() },
		{ fieldname: "item", label: __("Item"), fieldtype: "Link", options: "Books Item" },
		{ fieldname: "location", label: __("Location"), fieldtype: "Link", options: "Books Location" },
		{ fieldname: "batch", label: __("Batch"), fieldtype: "Link", options: "Books Batch" },
		{ fieldname: "serial_number", label: __("Serial Number"), fieldtype: "Link", options: "Books Serial Number" },
	],
};
