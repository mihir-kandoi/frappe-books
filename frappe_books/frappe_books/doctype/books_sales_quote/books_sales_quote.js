// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Books Sales Quote", {
	refresh(frm) {
		if (frm.doc.docstatus !== 1) return;
		frm.add_custom_button(__("Sales Invoice"), async () => {
			const { message } = await frappe.call({
				method: "frappe_books.document_actions.make_sales_invoice",
				args: { quote_name: frm.doc.name },
				freeze: true,
			});
			frappe.model.sync(message);
			frappe.set_route("Form", message.doctype, message.name);
		}, __("Create"));
	},
});
