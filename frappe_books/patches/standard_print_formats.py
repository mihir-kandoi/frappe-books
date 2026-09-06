"""Replace the app-generated Print Formats with the standard module files."""

import frappe

PRINT_FORMATS = (
	"Frappe Books - Sales Quote",
	"Frappe Books - Sales Invoice",
	"Frappe Books - Purchase Invoice",
	"Frappe Books - Payment",
	"Frappe Books - Journal Entry",
	"Frappe Books - Shipment",
	"Frappe Books - Purchase Receipt",
	"Frappe Books - Stock Movement",
)


def execute():
	for name in PRINT_FORMATS:
		if frappe.db.get_value("Print Format", name, "standard") == "No":
			frappe.delete_doc("Print Format", name, force=True, ignore_permissions=True)
