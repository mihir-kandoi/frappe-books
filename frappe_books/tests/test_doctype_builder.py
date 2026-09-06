"""Unit coverage for generated Frappe DocType definitions."""

from frappe.tests import UnitTestCase

from frappe_books.dev.doctype_builder import build_fields, build_naming


class TestDocTypeBuilder(UnitTestCase):
	def test_autoincrement_uses_sqlite_safe_numeric_format(self):
		self.assertEqual(
			build_naming({"name": "ItemEnquiry", "naming": "autoincrement"}),
			{"autoname": "format:{##########}"},
		)

	def test_ledger_lookup_fields_are_indexed(self):
		schema = {
			"name": "AccountingLedgerEntry",
			"fields": [
				{"fieldname": "account", "fieldtype": "Link", "target": "Account"},
				{"fieldname": "referenceName", "fieldtype": "DynamicLink", "references": "referenceType"},
				{"fieldname": "referenceType", "fieldtype": "Select", "options": []},
				{"fieldname": "debit", "fieldtype": "Currency"},
			],
		}
		indexed = {
			field["fieldname"] for field in build_fields(schema, {"Account"}) if field.get("search_index")
		}
		self.assertEqual(indexed, {"account", "voucher_no"})
