frappe.query_reports["Books General Ledger"] = {
	filters: [
		{ fieldname: "from_date", label: __("From Date"), fieldtype: "Date", default: frappe.datetime.add_months(frappe.datetime.get_today(), -12) },
		{ fieldname: "to_date", label: __("To Date"), fieldtype: "Date", default: frappe.datetime.get_today() },
		{ fieldname: "account", label: __("Account"), fieldtype: "Link", options: "Books Account" },
		{ fieldname: "party", label: __("Party"), fieldtype: "Link", options: "Books Party" },
		{ fieldname: "voucher_type", label: __("Voucher Type"), fieldtype: "Link", options: "DocType" },
		{ fieldname: "voucher_no", label: __("Voucher"), fieldtype: "Dynamic Link", options: "voucher_type" },
	],
};
