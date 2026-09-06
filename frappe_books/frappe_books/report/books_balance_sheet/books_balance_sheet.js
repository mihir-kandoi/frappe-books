frappe.query_reports["Books Balance Sheet"] = {
	filters: [
		{ fieldname: "to_date", label: __("As On Date"), fieldtype: "Date", default: frappe.datetime.get_today(), reqd: 1 },
	],
};
