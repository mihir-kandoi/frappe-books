"""Persist Books form customizations in hosted Frappe DocTypes."""

from __future__ import annotations

from contextlib import contextmanager

import frappe

from frappe_books.ui_bridge.mapping import (
	CUSTOM_FIELD_PREFIX,
	custom_target_field,
	target_doctype,
	target_field,
	target_reference,
)

FIELD_TYPE_MAP = {
	"AttachImage": "Attach Image",
	"Attachment": "Attach",
	"AutoComplete": "Autocomplete",
	"DynamicLink": "Dynamic Link",
}


def sync_all_custom_forms():
	if not frappe.db.table_exists("Books Custom Form"):
		return

	for name in frappe.get_all("Books Custom Form", pluck="name"):
		sync_custom_form(frappe.get_doc("Books Custom Form", name))


def sync_custom_form(doc):
	"""Create hosted columns for one Books Custom Form document."""
	target = target_doctype(doc.name)
	definitions = [_custom_field_definition(doc.name, row, doc.custom_fields) for row in doc.custom_fields]

	_upsert_custom_fields(target, definitions)
	_remove_stale_custom_fields(target, {field["fieldname"] for field in definitions})
	frappe.clear_cache(doctype=target)


def remove_custom_fields(source_schema: str):
	target = target_doctype(source_schema)
	_remove_stale_custom_fields(target, set())
	frappe.clear_cache(doctype=target)


def _custom_field_definition(source_schema: str, row, rows) -> dict:
	if row.fieldname in frappe_books_fields(source_schema):
		frappe.throw(f"Field {row.fieldname} already exists in Books schema {source_schema}")

	fieldtype = FIELD_TYPE_MAP.get(row.fieldtype, row.fieldtype)
	definition = {
		"fieldname": custom_target_field(row.fieldname),
		"label": row.label,
		"fieldtype": fieldtype,
		# Existing rows have no value yet, so a column is only required when a default can fill it.
		"reqd": bool(row.is_required and row.default is not None),
		"default": row.default,
		"is_system_generated": 1,
	}

	if fieldtype in {"Link", "Table"} and row.target:
		definition["options"] = target_reference(row.target)
	elif fieldtype == "Dynamic Link" and row.references:
		definition["options"] = _reference_target(source_schema, row.references, rows)
	elif row.options:
		definition["options"] = row.options

	return definition


def frappe_books_fields(source_schema: str) -> set[str]:
	from frappe_books.ui_bridge.mapping import schema_mapping

	return set(schema_mapping()[source_schema]["fields"])


def _reference_target(source_schema: str, references: str, rows) -> str:
	if any(row.fieldname == references for row in rows):
		return custom_target_field(references)
	return target_field(source_schema, references)


def _upsert_custom_fields(target: str, definitions: list[dict]):
	if not definitions:
		return

	previous_flag = frappe.flags.in_create_custom_fields
	frappe.flags.in_create_custom_fields = True
	try:
		for definition in definitions:
			name = frappe.db.exists(
				"Custom Field",
				{"dt": target, "fieldname": definition["fieldname"]},
			)
			if name:
				field = frappe.get_doc("Custom Field", name)
				field.update(definition)
				field.save(ignore_permissions=True)
				continue

			field = frappe.get_doc(
				{
					"doctype": "Custom Field",
					"dt": target,
					"permlevel": 0,
					**definition,
				}
			)
			field.insert(ignore_permissions=True)
	finally:
		frappe.flags.in_create_custom_fields = previous_flag

	frappe.clear_cache(doctype=target)
	frappe.db.updatedb(target)


def _remove_stale_custom_fields(target: str, desired: set[str]):
	existing = frappe.get_all(
		"Custom Field",
		filters={"dt": target, "fieldname": ["like", f"{CUSTOM_FIELD_PREFIX}%"]},
		fields=["name", "fieldname"],
	)
	stale = [field.name for field in existing if field.fieldname not in desired]
	if not stale:
		return

	with _as_administrator():
		for name in stale:
			frappe.delete_doc("Custom Field", name, ignore_permissions=True)
	frappe.db.updatedb(target)


@contextmanager
def _as_administrator():
	"""Books owns its generated fields, but Frappe only lets Administrator delete fields it created."""
	user = frappe.session.user
	frappe.set_user("Administrator")
	try:
		yield
	finally:
		frappe.set_user(user)
