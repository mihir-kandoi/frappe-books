# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from decimal import Decimal

import frappe
from frappe import _
from frappe.model.document import Document

from frappe_books.series import SeriesNamingMixin


class BooksJournalEntry(SeriesNamingMixin, Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from frappe_books.frappe_books.doctype.books_journal_entry_account.books_journal_entry_account import (
			BooksJournalEntryAccount,
		)

		accounts: DF.Table[BooksJournalEntryAccount]
		amended_from: DF.Link | None
		attachment: DF.Attach | None
		entry_type: DF.Literal[
			"Journal Entry",
			"Bank Entry",
			"Cash Entry",
			"Credit Card Entry",
			"Debit Note",
			"Credit Note",
			"Contra Entry",
			"Excise Entry",
			"Write Off Entry",
			"Opening Entry",
			"Depreciation Entry",
		]
		number_series: DF.Link
		posting_date: DF.Date
		reference_date: DF.Date | None
		reference_number: DF.Data | None
		total_credit: DF.Currency
		total_debit: DF.Currency
		user_remark: DF.Text | None
	# end: auto-generated types

	_DOCTYPE_NAME = "Books Journal Entry"

	def validate(self):
		self._validate_accounts()
		self.total_debit, self.total_credit = self._get_totals()

		if self.total_debit == 0:
			frappe.throw(_("Journal entry total must be greater than zero."))
		if self.total_debit != self.total_credit:
			frappe.throw(
				_("Total debit {0} must equal total credit {1}.").format(
					self.total_debit,
					self.total_credit,
				)
			)

	def on_submit(self):
		for row in self.accounts:
			self._make_ledger_entry(
				account=row.account,
				debit=to_decimal(row.debit),
				credit=to_decimal(row.credit),
			)

	def on_cancel(self):
		entries = frappe.get_all(
			"Books Ledger Entry",
			filters={
				"voucher_type": self.doctype,
				"voucher_no": self.name,
				"reverted": 0,
			},
			fields=["name", "account", "debit", "credit"],
		)
		for entry in entries:
			frappe.db.set_value("Books Ledger Entry", entry.name, "reverted", 1, update_modified=False)
			self._make_ledger_entry(
				account=entry.account,
				debit=to_decimal(entry.credit),
				credit=to_decimal(entry.debit),
				reverts=entry.name,
			)

	def on_trash(self):
		frappe.db.delete(
			"Books Ledger Entry",
			{"voucher_type": self.doctype, "voucher_no": self.name},
		)

	def _validate_accounts(self):
		if len(self.accounts) < 2:
			frappe.throw(_("Journal entry requires at least two account rows."))

		account_names = {row.account for row in self.accounts if row.account}
		account_map = {
			account.name: account
			for account in frappe.get_all(
				"Books Account",
				filters={"name": ["in", list(account_names)]},
				fields=["name", "is_group"],
			)
		}
		for row in self.accounts:
			self._validate_account_row(row, account_map)

	def _validate_account_row(self, row, account_map):
		account = account_map.get(row.account)
		if not account:
			frappe.throw(_("Account {0} does not exist.").format(row.account))
		if account.is_group:
			frappe.throw(_("Group account {0} cannot receive a posting.").format(row.account))

		debit = to_decimal(row.debit)
		credit = to_decimal(row.credit)
		if debit < 0 or credit < 0:
			frappe.throw(_("Debit and credit amounts cannot be negative."))
		if (debit == 0) == (credit == 0):
			frappe.throw(_("Each account row must contain either a debit or a credit."))

	def _get_totals(self):
		debit = sum((to_decimal(row.debit) for row in self.accounts), Decimal())
		credit = sum((to_decimal(row.credit) for row in self.accounts), Decimal())
		return debit, credit

	def _make_ledger_entry(self, account, debit, credit, reverts=None):
		frappe.get_doc(
			{
				"doctype": "Books Ledger Entry",
				"posting_date": self.posting_date,
				"account": account,
				"debit": debit,
				"credit": credit,
				"voucher_type": self.doctype,
				"voucher_no": self.name,
				"reverted": bool(reverts),
				"reverts": reverts,
			}
		).insert(ignore_permissions=True)


def to_decimal(value):
	return Decimal(str(value or 0))
