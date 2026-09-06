frappe.query_reports["Books GSTR 2"] = {
	filters: [
		{ fieldname: "transfer_type", label: __("Transfer Type"), fieldtype: "Select", options: "\nB2B" },
		{ fieldname: "place_of_supply", label: __("Place of Supply"), fieldtype: "Data" },
		{ fieldname: "from_date", label: __("From Date"), fieldtype: "Date", default: frappe.datetime.add_months(frappe.datetime.get_today(), -3) },
		{ fieldname: "to_date", label: __("To Date"), fieldtype: "Date", default: frappe.datetime.get_today() },
	],
};
