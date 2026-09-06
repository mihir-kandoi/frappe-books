"""Translate Books interface schemas into Frappe DocType definitions."""

from __future__ import annotations

import re
from collections.abc import Iterable
from copy import deepcopy
from typing import Any

Schema = dict[str, Any]

MODULE = "Frappe Books"
DOCTYPE_OVERRIDES = {
	"Account": "Books Account",
	"AccountingLedgerEntry": "Books Ledger Entry",
	"JournalEntry": "Books Journal Entry",
	"JournalEntryAccount": "Books Journal Entry Account",
}
FIELD_OVERRIDES = {
	("Account", "name"): "account_name",
	("Account", "parentAccount"): "parent_books_account",
	("Account", "isGroup"): "is_group",
	("AccountingLedgerEntry", "date"): "posting_date",
	("AccountingLedgerEntry", "referenceName"): "voucher_no",
	("AccountingLedgerEntry", "referenceType"): "voucher_type",
	("Item", "for"): "item_usage",
	("JournalEntry", "date"): "posting_date",
	("Payment", "for"): "payment_references",
}
FIELD_TYPE_MAP = {
	"AttachImage": "Attach Image",
	"Attachment": "Attach",
	"AutoComplete": "Autocomplete",
	"DynamicLink": "Dynamic Link",
	"Secret": "Password",
}
NUMBER_SERIES_DIGITS = 5
AUTOINCREMENT_DIGITS = 10


def build_doctype(schema: Schema, schema_names: Iterable[str]) -> dict[str, Any]:
	"""Build a complete standard DocType document from one Books schema."""
	schema_names = set(schema_names)
	name = doctype_name(schema["name"])
	definition: dict[str, Any] = {
		"doctype": "DocType",
		"name": name,
		"module": MODULE,
		"custom": 0,
		"istable": int(bool(schema.get("isChild"))),
		"issingle": int(bool(schema.get("isSingle"))),
		"is_submittable": int(bool(schema.get("isSubmittable"))),
		"is_tree": int(bool(schema.get("isTree"))),
		"track_changes": int(not schema.get("isChild", False)),
		"editable_grid": 1,
		"allow_rename": int(schema.get("naming") == "manual"),
		"fields": build_fields(schema, schema_names),
		"permissions": build_permissions(schema),
	}
	definition.update(build_naming(schema))

	if schema.get("isTree"):
		definition["nsm_parent_field"] = fieldname(schema["name"], "parentAccount")
		definition["fields"].extend(_tree_system_fields(name))

	search_fields = _mapped_field_list(schema, schema.get("keywordFields", []))
	if search_fields:
		definition["search_fields"] = ", ".join(search_fields)
	return definition


def build_fields(schema: Schema, schema_names: set[str]) -> list[dict[str, Any]]:
	fields: list[dict[str, Any]] = []
	seen_names: set[str] = set()
	current_tab = None
	current_section = None
	child = bool(schema.get("isChild"))

	for source_field in schema.get("fields", []):
		original_name = source_field["fieldname"]
		if original_name == "name" and schema["name"] != "Account":
			continue
		if source_field.get("abstract") or not source_field.get("fieldtype"):
			continue

		if not child:
			current_tab = _append_break_if_changed(fields, "Tab Break", source_field.get("tab"), current_tab)
			current_section = _append_break_if_changed(
				fields, "Section Break", source_field.get("section"), current_section
			)

		converted = _convert_field(schema, source_field, schema_names)
		if converted["fieldname"] in seen_names:
			raise ValueError(f"{schema['name']} has duplicate converted field {converted['fieldname']}")
		seen_names.add(converted["fieldname"])
		fields.append(converted)

	if schema["name"] == "JournalEntry":
		fields.extend(_journal_total_fields())
	return fields


def _convert_field(schema: Schema, source_field: dict[str, Any], schema_names: set[str]) -> dict[str, Any]:
	original_name = source_field["fieldname"]
	converted_name = fieldname(schema["name"], original_name)
	fieldtype = FIELD_TYPE_MAP.get(source_field["fieldtype"], source_field["fieldtype"])
	dynamic_reference_fields = {
		field.get("references")
		for field in schema.get("fields", [])
		if field.get("fieldtype") == "DynamicLink"
	}
	if original_name in dynamic_reference_fields:
		fieldtype = "Link"
	if schema["name"] == "AccountingLedgerEntry" and original_name == "date":
		fieldtype = "Date"

	converted: dict[str, Any] = {
		"fieldname": converted_name,
		"label": source_field.get("label") or _label_from_name(original_name),
		"fieldtype": fieldtype,
	}
	_copy_boolean_properties(source_field, converted)
	if source_field.get("computed"):
		converted["read_only"] = 1
	if source_field.get("placeholder"):
		converted["description"] = source_field["placeholder"]
	if "default" in source_field:
		default = source_field["default"]
		if original_name in dynamic_reference_fields and default in schema_names:
			default = doctype_name(default)
		converted["default"] = _convert_default(default)

	if fieldtype in {"Link", "Table"}:
		target = source_field.get("target")
		if original_name in dynamic_reference_fields:
			target = "DocType"
		if not target:
			raise ValueError(f"{schema['name']}.{original_name} has no target")
		converted["options"] = doctype_name(target) if target in schema_names else target
	elif fieldtype == "Dynamic Link":
		reference = source_field.get("references")
		if not reference:
			raise ValueError(f"{schema['name']}.{original_name} has no references field")
		converted["options"] = fieldname(schema["name"], reference)
	elif fieldtype in {"Select", "Autocomplete"}:
		options = _convert_options(source_field.get("options"))
		if fieldtype == "Select" and source_field.get("default") not in (None, ""):
			default = str(source_field["default"])
			option_values = options.splitlines()
			if default not in option_values:
				options = "\n".join([default, *option_values])
		if options:
			converted["options"] = options

	if original_name in schema.get("tableFields", []):
		converted["in_list_view"] = 1
	return converted


def build_naming(schema: Schema) -> dict[str, Any]:
	if schema.get("isChild") or schema.get("isSingle"):
		return {}

	naming = schema.get("naming", "random")
	if schema["name"] == "Account":
		return {"autoname": "field:account_name"}
	if naming == "manual":
		return {"autoname": "Prompt"}
	if naming == "autoincrement":
		return {"autoname": f"format:{{{'#' * AUTOINCREMENT_DIGITS}}}"}
	if naming == "numberSeries":
		prefix = _number_series_prefix(schema)
		return {"autoname": f"format:{prefix}{{{'#' * NUMBER_SERIES_DIGITS}}}"}
	return {"autoname": "hash"}


def build_permissions(schema: Schema) -> list[dict[str, Any]]:
	if schema.get("isChild"):
		return []
	manager_permission = {
		"role": "System Manager",
		"read": 1,
		"write": 1,
		"create": 1,
		"delete": 1,
		"print": 1,
		"email": 1,
		"report": 1,
		"export": 1,
		"share": 1,
	}
	if schema.get("create") is False and schema["name"] != "Account":
		manager_permission.update({"write": 0, "create": 0, "delete": 0})
	if schema.get("isSubmittable"):
		manager_permission.update({"submit": 1, "cancel": 1, "amend": 1})

	books_manager = deepcopy(manager_permission)
	books_manager["role"] = "Books Manager"
	books_user = deepcopy(manager_permission)
	books_user["role"] = "Books User"
	books_user.update({"delete": 0, "share": 0})
	if schema.get("isSingle") or schema.get("create") is False:
		books_user.update({"write": 0, "create": 0, "delete": 0})
		for action in ("submit", "cancel", "amend"):
			books_user.pop(action, None)
	return [manager_permission, books_manager, books_user]


def doctype_name(source_name: str) -> str:
	return DOCTYPE_OVERRIDES.get(source_name, f"Books {_label_from_name(source_name)}")


def fieldname(schema_name: str, source_name: str) -> str:
	return FIELD_OVERRIDES.get((schema_name, source_name), _snake_case(source_name))


def _copy_boolean_properties(source: dict[str, Any], target: dict[str, Any]) -> None:
	properties = {
		"required": "reqd",
		"readOnly": "read_only",
		"readonly": "read_only",
		"hidden": "hidden",
		"invisible": "hidden",
		"unique": "unique",
	}
	for source_key, target_key in properties.items():
		if source.get(source_key):
			target[target_key] = 1


def _append_break_if_changed(
	fields: list[dict[str, Any]], fieldtype: str, value: str | None, current: str | None
) -> str | None:
	if not value or value == current:
		return current
	slug = _snake_case(value)
	fields.append(
		{
			"fieldname": f"{slug}_{fieldtype.lower().replace(' ', '_')}_{len(fields) + 1}",
			"label": value,
			"fieldtype": fieldtype,
		}
	)
	return value


def _convert_options(options: Any) -> str:
	if not options:
		return ""
	if isinstance(options, str):
		return options
	values = [
		option.get("value", option.get("label", "")) if isinstance(option, dict) else option
		for option in options
	]
	return "\n".join(str(value) for value in values if value != "")


def _convert_default(value: Any) -> str | int | float:
	if isinstance(value, bool):
		return "1" if value else "0"
	return value


def _mapped_field_list(schema: Schema, names: Iterable[str]) -> list[str]:
	return [fieldname(schema["name"], name) for name in names if name != "name"]


def _number_series_prefix(schema: Schema) -> str:
	for source_field in schema.get("fields", []):
		if source_field["fieldname"] == "numberSeries" and source_field.get("default"):
			return str(source_field["default"])
	raise ValueError(f"{schema['name']} uses numberSeries naming without a default prefix")


def _journal_total_fields() -> list[dict[str, Any]]:
	return [
		{"fieldname": "total_debit", "label": "Total Debit", "fieldtype": "Currency", "read_only": 1},
		{"fieldname": "total_credit", "label": "Total Credit", "fieldtype": "Currency", "read_only": 1},
	]


def _tree_system_fields(doctype: str) -> list[dict[str, Any]]:
	return [
		{"fieldname": "lft", "label": "Left", "fieldtype": "Int", "read_only": 1, "hidden": 1, "no_copy": 1},
		{"fieldname": "rgt", "label": "Right", "fieldtype": "Int", "read_only": 1, "hidden": 1, "no_copy": 1},
		{
			"fieldname": "old_parent",
			"label": "Old Parent",
			"fieldtype": "Link",
			"options": doctype,
			"hidden": 1,
		},
	]


def _snake_case(value: str) -> str:
	value = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", value)
	value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
	return re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()


def _label_from_name(value: str) -> str:
	return _snake_case(value).replace("_", " ").title()


def clone_definition(definition: dict[str, Any]) -> dict[str, Any]:
	"""Return a safe copy for callers that mutate Frappe document input."""
	return deepcopy(definition)
