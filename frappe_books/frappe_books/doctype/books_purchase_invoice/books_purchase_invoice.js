// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Books Purchase Invoice", {
	refresh(frm) {
		if (frm.doc.docstatus !== 1) return;
		if (Math.abs(frm.doc.outstanding_amount || 0) > 0) {
			frm.add_custom_button(__("Payment"), () => open_purchase_document(
				"frappe_books.document_actions.make_payment"
			), __("Create"));
		}
		if (!frm.doc.return_against && !frm.doc.is_fully_returned) {
			frm.add_custom_button(__("Purchase Return"), () => open_purchase_document(
				"frappe_books.document_actions.make_return"
			), __("Create"));
		}
	},
});

async function open_purchase_document(method) {
	const { message } = await frappe.call({
		method,
		args: { invoice_doctype: cur_frm.doctype, invoice_name: cur_frm.doc.name },
		freeze: true,
	});
	frappe.model.sync(message);
	frappe.set_route("Form", message.doctype, message.name);
}
