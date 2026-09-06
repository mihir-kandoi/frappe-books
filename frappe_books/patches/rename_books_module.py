"""Rename the original Books module before its controllers are synchronized."""

import frappe
from frappe.model.rename_doc import rename_doc

OLD_MODULE = "Frappe Books SQLite"
NEW_MODULE = "Frappe Books"


def execute():
	old_module = frappe.db.get_value("Module Def", OLD_MODULE, ["app_name", "custom"], as_dict=True)
	if not old_module:
		return

	new_module = frappe.db.get_value("Module Def", NEW_MODULE, ["app_name", "custom"], as_dict=True)
	for name, module in ((OLD_MODULE, old_module), (NEW_MODULE, new_module)):
		if module and (module.app_name != "frappe_books" or module.custom):
			frappe.throw(f"Cannot rename the Books module: {name} is not a standard module of frappe_books.")

	# Standard modules block interactive renames. Both module owners were checked above.
	rename_doc(
		"Module Def",
		OLD_MODULE,
		NEW_MODULE,
		merge=bool(new_module),
		ignore_permissions=True,
		validate=False,
		rebuild_search=False,
		show_alert=False,
	)
	# Schema sync uses the module map loaded before this patch ran.
	frappe.setup_module_map()
