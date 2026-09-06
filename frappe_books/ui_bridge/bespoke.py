"""Aggregate queries used by the Books web interface."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

import frappe
from frappe.utils import get_datetime, getdate

from frappe_books.accounting.money import as_decimal, rounded
from frappe_books.commerce.pos import transacted_amounts
from frappe_books.setup import max_numeric_name
from frappe_books.ui_bridge.mapping import target_doctype

NUMERIC_AUTONAME = re.compile(r"format:\{#+\}")


class BooksBespokeQueries:
	def call(self, method: str, args: list[Any]) -> Any:
		if not isinstance(method, str) or not isinstance(args, list):
			frappe.throw("Books aggregate queries require a method and argument list")
		handler = getattr(self, _METHODS.get(method, ""), None)
		if not handler:
			frappe.throw(f"Unsupported Books query: {method}")
		return handler(*args)

	def top_expenses(self, from_date: str, to_date: str):
		root_types = dict(frappe.get_list("Books Account", fields=["name", "root_type"], as_list=True))
		totals = defaultdict(as_decimal)
		for row in self._ledger(from_date, to_date):
			if root_types.get(row.account) == "Expense":
				totals[row.account] += as_decimal(row.debit) - as_decimal(row.credit)
		return [
			{"account": account, "total": rounded(total)}
			for account, total in sorted(totals.items(), key=lambda item: item[1], reverse=True)[:5]
		]

	def total_outstanding(self, source_schema: str, from_date: str, to_date: str):
		values = frappe.get_list(
			target_doctype(source_schema),
			filters={"docstatus": 1, "date": ["between", [from_date, to_date]]},
			fields=["base_grand_total", "outstanding_amount"],
		)
		return {
			"total": rounded(sum((abs(as_decimal(row.base_grand_total)) for row in values), as_decimal(0))),
			"outstanding": rounded(
				sum((abs(as_decimal(row.outstanding_amount)) for row in values), as_decimal(0))
			),
		}

	def cashflow(self, from_date: str, to_date: str):
		account_types = dict(frappe.get_list("Books Account", fields=["name", "account_type"], as_list=True))
		months = defaultdict(lambda: {"inflow": as_decimal(0), "outflow": as_decimal(0)})
		for row in self._ledger(from_date, to_date):
			if account_types.get(row.account) not in {"Cash", "Bank"}:
				continue
			month = str(row.posting_date)[:7]
			months[month]["inflow"] += as_decimal(row.debit)
			months[month]["outflow"] += as_decimal(row.credit)
		return [
			{"yearmonth": month, **{key: rounded(value) for key, value in values.items()}}
			for month, values in sorted(months.items())
		]

	def income_and_expenses(self, from_date: str, to_date: str):
		root_types = dict(frappe.get_list("Books Account", fields=["name", "root_type"], as_list=True))
		monthly = {"income": defaultdict(as_decimal), "expense": defaultdict(as_decimal)}
		for row in self._ledger(from_date, to_date):
			month = str(row.posting_date)[:7]
			if root_types.get(row.account) == "Income":
				monthly["income"][month] += as_decimal(row.credit) - as_decimal(row.debit)
			elif root_types.get(row.account) == "Expense":
				monthly["expense"][month] += as_decimal(row.debit) - as_decimal(row.credit)
		return {
			key: [
				{"yearmonth": month, "balance": rounded(balance)} for month, balance in sorted(values.items())
			]
			for key, values in monthly.items()
		}

	def total_credit_and_debit(self):
		totals = defaultdict(lambda: {"totalCredit": as_decimal(0), "totalDebit": as_decimal(0)})
		for row in self._ledger():
			totals[row.account]["totalCredit"] += as_decimal(row.credit)
			totals[row.account]["totalDebit"] += as_decimal(row.debit)
		return [
			{"account": account, **{key: rounded(value) for key, value in values.items()}}
			for account, values in totals.items()
		]

	def stock_quantity(
		self,
		item: str,
		location: str | None = None,
		from_date: str | None = None,
		to_date: str | None = None,
		batch: str | None = None,
		serial_numbers: list[str] | None = None,
	):
		filters: dict[str, Any] = {"item": item}
		if location:
			filters["location"] = location
		if batch:
			filters["batch"] = batch
		if serial_numbers:
			filters["serial_number"] = ["in", serial_numbers]
		if from_date and to_date:
			filters["date"] = ["between", [from_date, to_date]]
		elif from_date:
			filters["date"] = [">=", from_date]
		elif to_date:
			filters["date"] = ["<=", to_date]
		values = frappe.get_list("Books Stock Ledger Entry", filters=filters, pluck="quantity")
		if not values:
			return None
		return float(sum((as_decimal(value) for value in values), as_decimal(0)))

	def return_balance(self, source_schema: str, name: str):
		doc = frappe.get_doc(target_doctype(source_schema), name)
		doc.check_permission("read")
		balances = defaultdict(lambda: {"quantity": 0.0, "batches": {}, "serialNumbers": []})
		for row in doc.items:
			entry = balances[row.item]
			entry["quantity"] += abs(float(row.quantity or 0))
			if row.get("batch"):
				entry["batches"].setdefault(row.batch, {"quantity": 0.0, "serialNumbers": []})
				entry["batches"][row.batch]["quantity"] += abs(float(row.quantity or 0))
			self._add_serials(entry, row)
		return dict(balances)

	def pos_transacted_amount(self, from_date, to_date, _last_shift_closing_date=None):
		"""Return the same expected amounts the closing shift stores on the server."""
		if not frappe.has_permission("Books Payment", ptype="read"):
			raise frappe.PermissionError
		return transacted_amounts(get_datetime(from_date), get_datetime(to_date))

	def last_inserted(self, source_schema: str) -> int:
		"""Return the highest numeric name used by an autoincrement Books schema."""
		target = target_doctype(source_schema)
		if not NUMERIC_AUTONAME.fullmatch(frappe.get_meta(target).autoname or ""):
			frappe.throw(f"{source_schema} does not use numeric names")
		if not frappe.has_permission(target, ptype="read"):
			raise frappe.PermissionError
		return max_numeric_name(target)

	def _ledger(self, from_date=None, to_date=None):
		filters: dict[str, Any] = {"reverted": 0}
		if from_date and to_date:
			filters["posting_date"] = ["between", [getdate(from_date), getdate(to_date)]]
		return frappe.get_list(
			"Books Ledger Entry",
			filters=filters,
			fields=["posting_date", "account", "debit", "credit"],
		)

	def _add_serials(self, entry, row):
		serials = [
			value.strip() for value in str(row.get("serial_number") or "").splitlines() if value.strip()
		]
		entry["serialNumbers"].extend(serials)
		if row.get("batch"):
			entry["batches"][row.batch]["serialNumbers"].extend(serials)


_METHODS = {
	"getTopExpenses": "top_expenses",
	"getTotalOutstanding": "total_outstanding",
	"getCashflow": "cashflow",
	"getIncomeAndExpenses": "income_and_expenses",
	"getTotalCreditAndDebit": "total_credit_and_debit",
	"getStockQuantity": "stock_quantity",
	"getReturnBalanceItemsQty": "return_balance",
	"getPOSTransactedAmount": "pos_transacted_amount",
	"getLastInserted": "last_inserted",
}
