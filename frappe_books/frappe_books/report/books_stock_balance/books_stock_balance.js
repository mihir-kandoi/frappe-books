frappe.query_reports["Books Stock Balance"] = {
	filters: [
		{ fieldname: "from_date", label: __("From Date"), fieldtype: "Date", default: frappe.datetime.year_start() },
		{ fieldname: "to_date", label: __("To Date"), fieldtype: "Date", default: frappe.datetime.get_today() },
		{ fieldname: "item", label: __("Item"), fieldtype: "Link", options: "Books Item" },
		{ fieldname: "location", label: __("Location"), fieldtype: "Link", options: "Books Location" },
		{ fieldname: "batch", label: __("Batch"), fieldtype: "Link", options: "Books Batch" },
	],
};
