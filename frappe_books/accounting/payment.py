"""Payment validation, posting, and allocation behavior."""

import frappe
from frappe import _
from frappe.model.document import Document

from frappe_books.accounting.ledger import LedgerPosting, delete_entries, reverse_entries
from frappe_books.accounting.money import as_decimal, rounded
from frappe_books.accounting.outstanding import update_party_outstanding
from frappe_books.series import SeriesNamingMixin

REFERENCE_DOCTYPES = {
	"SalesInvoice": "Books Sales Invoice",
	"PurchaseInvoice": "Books Purchase Invoice",
	"Books Sales Invoice": "Books Sales Invoice",
	"Books Purchase Invoice": "Books Purchase Invoice",
}


class PaymentController(SeriesNamingMixin, Document):
	def before_validate(self):
		self.amount_paid = rounded(as_decimal(self.amount) - as_decimal(self.writeoff))
		for row in self.payment_references:
			row.reference_type = REFERENCE_DOCTYPES.get(row.reference_type, row.reference_type)

	def validate(self):
		if as_decimal(self.amount) <= 0:
			frappe.throw(_("Payment amount must be greater than zero."))
		if as_decimal(self.writeoff) < 0 or as_decimal(self.writeoff) > as_decimal(self.amount):
			frappe.throw(_("Write-off must be between zero and the payment amount."))
		_validate_allocations(self)

	def on_submit(self):
		posting = LedgerPosting(self)
		if self.payment_type == "Receive":
			posting.debit(self.payment_account, self.amount_paid, self.party)
			posting.credit(self.account, self.amount, self.party)
		else:
			posting.debit(self.account, self.amount, self.party)
			posting.credit(self.payment_account, self.amount_paid, self.party)
		_post_taxes(self, posting)
		_post_writeoff(self, posting)
		posting.post()
		_apply_allocations(self, reverse=False)
		update_party_outstanding(self.party)

	def on_cancel(self):
		reverse_entries(self)
		_apply_allocations(self, reverse=True)
		update_party_outstanding(self.party)

	def on_trash(self):
		delete_entries(self)


def _validate_allocations(payment):
	total = as_decimal(0)
	for row in payment.payment_references:
		if row.reference_type not in REFERENCE_DOCTYPES.values():
			frappe.throw(_("Select a sales or purchase invoice reference."))
		if not frappe.db.exists(row.reference_type, row.reference_name):
			frappe.throw(_("Referenced invoice {0} does not exist.").format(row.reference_name))
		outstanding = as_decimal(
			frappe.db.get_value(row.reference_type, row.reference_name, "outstanding_amount")
		)
		if as_decimal(row.amount) <= 0 or as_decimal(row.amount) > abs(outstanding):
			frappe.throw(_("Allocated amount exceeds the invoice outstanding amount."))
		total += as_decimal(row.amount)
	if total > as_decimal(payment.amount):
		frappe.throw(_("Payment allocations cannot exceed the settled amount, including the write-off."))


def _apply_allocations(payment, reverse):
	for row in payment.payment_references:
		outstanding = as_decimal(
			frappe.db.get_value(row.reference_type, row.reference_name, "outstanding_amount")
		)
		amount = as_decimal(row.amount)
		if outstanding < 0:
			updated = outstanding - amount if reverse else outstanding + amount
		else:
			updated = outstanding + amount if reverse else outstanding - amount
		frappe.db.set_value(
			row.reference_type,
			row.reference_name,
			"outstanding_amount",
			rounded(updated),
			update_modified=False,
		)


def _post_taxes(payment, posting):
	for tax in payment.taxes:
		if payment.payment_type == "Receive":
			posting.debit(tax.from_account, tax.amount)
			posting.credit(tax.account, tax.amount)
		else:
			posting.credit(tax.from_account, tax.amount)
			posting.debit(tax.account, tax.amount)


def _post_writeoff(payment, posting):
	writeoff = as_decimal(payment.writeoff)
	if writeoff == 0:
		return
	writeoff_account = frappe.db.get_single_value("Books Accounting Settings", "write_off_account")
	if not writeoff_account:
		frappe.throw(_("Set a write-off account in Books Accounting Settings."))
	if payment.payment_type == "Pay":
		posting.credit(writeoff_account, writeoff)
	else:
		posting.debit(writeoff_account, writeoff)
