// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Books Sales Invoice", {
	refresh(frm) {
		add_invoice_actions(frm);
	},
});

function add_invoice_actions(frm) {
	if (frm.doc.docstatus !== 1) return;
	if (Math.abs(frm.doc.outstanding_amount || 0) > 0) {
		frm.add_custom_button(__("Payment"), () => open_mapped_document(
			"frappe_books.document_actions.make_payment",
			{ invoice_doctype: frm.doctype, invoice_name: frm.doc.name }
		), __("Create"));
	}
	if (!frm.doc.return_against && !frm.doc.is_fully_returned) {
		frm.add_custom_button(__("Return / Credit Note"), () => open_mapped_document(
			"frappe_books.document_actions.make_return",
			{ invoice_doctype: frm.doctype, invoice_name: frm.doc.name }
		), __("Create"));
	}
}

async function open_mapped_document(method, args) {
	const { message } = await frappe.call({ method, args, freeze: true });
	frappe.model.sync(message);
	frappe.set_route("Form", message.doctype, message.name);
}
