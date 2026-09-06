"""General ledger and financial-statement report calculations."""

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import getdate

from frappe_books.accounting.money import as_decimal, rounded


def general_ledger(filters=None):
	filters = frappe._dict(filters or {})
	entries = _ledger_entries(filters)
	opening = as_decimal(0)
	if filters.from_date:
		opening = _opening_balance(filters)
	balance = opening
	data = []
	if opening:
		data.append({"account": _("Opening"), "balance": rounded(opening)})
	for entry in entries:
		balance += as_decimal(entry.debit) - as_decimal(entry.credit)
		data.append({**entry, "balance": rounded(balance)})
	return _general_ledger_columns(), data


def trial_balance(filters=None):
	filters = frappe._dict(filters or {})
	opening = _account_totals(_ledger_entries(filters, before_from=True)) if filters.from_date else {}
	period = _account_totals(_ledger_entries(filters))
	values = {}
	for account in set(opening) | set(period):
		opening_amounts = opening.get(account, {})
		opening_balance = as_decimal(opening_amounts.get("debit", 0)) - as_decimal(
			opening_amounts.get("credit", 0)
		)
		opening_debit, opening_credit = _split_balance(opening_balance)
		period_debit = rounded(period.get(account, {}).get("debit", 0))
		period_credit = rounded(period.get(account, {}).get("credit", 0))
		closing_debit, closing_credit = _split_balance(
			as_decimal(opening_debit) - as_decimal(opening_credit) + period_debit - period_credit
		)
		values[account] = {
			"opening_debit": opening_debit,
			"opening_credit": opening_credit,
			"debit": period_debit,
			"credit": period_credit,
			"closing_debit": closing_debit,
			"closing_credit": closing_credit,
		}
	data = _roll_up(values)
	return _trial_balance_columns(), data


def profit_and_loss(filters=None):
	filters = frappe._dict(filters or {})
	entries = _ledger_entries(filters)
	totals = _account_totals(entries)
	root_types = _root_types(totals)
	values = {}
	for account, amounts in totals.items():
		root_type = root_types.get(account)
		if root_type == "Income":
			values[account] = {"amount": rounded(amounts["credit"] - amounts["debit"])}
		elif root_type == "Expense":
			values[account] = {"amount": rounded(amounts["debit"] - amounts["credit"])}
	data = _roll_up(values, root_types={"Income", "Expense"})
	income = sum(
		(
			as_decimal(row["amount"])
			for row in data
			if row["root_type"] == "Income" and not row["parent_account"]
		),
		as_decimal(0),
	)
	expense = sum(
		(
			as_decimal(row["amount"])
			for row in data
			if row["root_type"] == "Expense" and not row["parent_account"]
		),
		as_decimal(0),
	)
	data.extend(
		[
			{"account": _("Total Income"), "root_type": "Income", "amount": rounded(income), "is_total": 1},
			{
				"account": _("Total Expense"),
				"root_type": "Expense",
				"amount": rounded(expense),
				"is_total": 1,
			},
			{"account": _("Net Profit / Loss"), "amount": rounded(income - expense), "is_total": 1},
		]
	)
	return _profit_and_loss_columns(), data


def balance_sheet(filters=None):
	filters = frappe._dict(filters or {})
	filters.from_date = None
	totals = _account_totals(_ledger_entries(filters))
	root_types = _root_types(totals)
	values = {}
	period_profit = as_decimal(0)
	for account, amounts in totals.items():
		root_type = root_types.get(account)
		if root_type == "Asset":
			values[account] = {"amount": rounded(amounts["debit"] - amounts["credit"])}
		elif root_type in {"Liability", "Equity"}:
			values[account] = {"amount": rounded(amounts["credit"] - amounts["debit"])}
		elif root_type == "Income":
			period_profit += amounts["credit"] - amounts["debit"]
		elif root_type == "Expense":
			period_profit -= amounts["debit"] - amounts["credit"]
	data = _roll_up(values, root_types={"Asset", "Liability", "Equity"})
	if period_profit:
		data.append(
			{
				"account": _("Current Period Earnings"),
				"root_type": "Equity",
				"amount": rounded(period_profit),
				"is_total": 1,
			}
		)
	return _balance_sheet_columns(), data


def _ledger_entries(filters, before_from=False):
	db_filters = {"reverted": 0}
	if filters.get("account"):
		db_filters["account"] = filters.account
	if filters.get("party"):
		db_filters["party"] = filters.party
	if filters.get("voucher_type"):
		db_filters["voucher_type"] = filters.voucher_type
	if filters.get("voucher_no"):
		db_filters["voucher_no"] = filters.voucher_no
	if before_from:
		db_filters["posting_date"] = ["<", getdate(filters.from_date)]
	else:
		if filters.get("from_date") and filters.get("to_date"):
			db_filters["posting_date"] = [
				"between",
				[getdate(filters.from_date), getdate(filters.to_date)],
			]
		elif filters.get("from_date"):
			db_filters["posting_date"] = [">=", getdate(filters.from_date)]
		elif filters.get("to_date"):
			db_filters["posting_date"] = ["<=", getdate(filters.to_date)]
	return frappe.get_all(
		"Books Ledger Entry",
		filters=db_filters,
		fields=[
			"posting_date",
			"account",
			"party",
			"debit",
			"credit",
			"voucher_type",
			"voucher_no",
		],
		order_by="posting_date asc, creation asc",
	)


def _opening_balance(filters):
	entries = _ledger_entries(filters, before_from=True)
	return sum((as_decimal(row.debit) - as_decimal(row.credit) for row in entries), as_decimal(0))


def _root_types(accounts):
	if not accounts:
		return {}
	rows = frappe.get_all(
		"Books Account", filters={"name": ["in", list(accounts)]}, fields=["name", "root_type"]
	)
	return {row.name: row.root_type for row in rows}


def _account_totals(entries):
	totals = defaultdict(lambda: {"debit": as_decimal(0), "credit": as_decimal(0)})
	for entry in entries:
		totals[entry.account]["debit"] += as_decimal(entry.debit)
		totals[entry.account]["credit"] += as_decimal(entry.credit)
	return totals


def _roll_up(values, root_types=None):
	accounts = frappe.get_all(
		"Books Account",
		fields=["name", "parent_books_account", "root_type", "is_group", "lft"],
		order_by="lft asc",
	)
	account_map = {row.name: row for row in accounts}
	rolled = defaultdict(lambda: defaultdict(as_decimal))
	for account, fields in values.items():
		current = account
		while current and current in account_map:
			for fieldname, amount in fields.items():
				rolled[current][fieldname] += as_decimal(amount)
			current = account_map[current].parent_books_account
	data = []
	for account in accounts:
		if root_types and account.root_type not in root_types:
			continue
		if account.name not in rolled:
			continue
		row = {
			"account": account.name,
			"parent_account": account.parent_books_account,
			"root_type": account.root_type,
			"is_group": account.is_group,
			"indent": _account_depth(account, account_map),
		}
		row.update({key: rounded(value) for key, value in rolled[account.name].items()})
		data.append(row)
	return data


def _account_depth(account, account_map):
	depth = 0
	parent = account.parent_books_account
	while parent and parent in account_map:
		depth += 1
		parent = account_map[parent].parent_books_account
	return depth


def _split_balance(balance):
	balance = rounded(balance)
	return (balance, 0) if balance >= 0 else (0, abs(balance))


def _general_ledger_columns():
	return [
		{"label": _("Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
		{
			"label": _("Account"),
			"fieldname": "account",
			"fieldtype": "Link",
			"options": "Books Account",
			"width": 200,
		},
		{
			"label": _("Party"),
			"fieldname": "party",
			"fieldtype": "Link",
			"options": "Books Party",
			"width": 160,
		},
		{"label": _("Debit"), "fieldname": "debit", "fieldtype": "Currency", "width": 120},
		{"label": _("Credit"), "fieldname": "credit", "fieldtype": "Currency", "width": 120},
		{"label": _("Balance"), "fieldname": "balance", "fieldtype": "Currency", "width": 120},
		{
			"label": _("Voucher Type"),
			"fieldname": "voucher_type",
			"fieldtype": "Link",
			"options": "DocType",
			"width": 170,
		},
		{
			"label": _("Voucher"),
			"fieldname": "voucher_no",
			"fieldtype": "Dynamic Link",
			"options": "voucher_type",
			"width": 160,
		},
	]


def _trial_balance_columns():
	return [
		{
			"label": _("Account"),
			"fieldname": "account",
			"fieldtype": "Link",
			"options": "Books Account",
			"width": 240,
		},
		{"label": _("Opening (Dr)"), "fieldname": "opening_debit", "fieldtype": "Currency", "width": 120},
		{"label": _("Opening (Cr)"), "fieldname": "opening_credit", "fieldtype": "Currency", "width": 120},
		{"label": _("Debit"), "fieldname": "debit", "fieldtype": "Currency", "width": 120},
		{"label": _("Credit"), "fieldname": "credit", "fieldtype": "Currency", "width": 120},
		{"label": _("Closing (Dr)"), "fieldname": "closing_debit", "fieldtype": "Currency", "width": 120},
		{"label": _("Closing (Cr)"), "fieldname": "closing_credit", "fieldtype": "Currency", "width": 120},
	]


def _profit_and_loss_columns():
	return [
		{"label": _("Account"), "fieldname": "account", "fieldtype": "Data", "width": 280},
		{"label": _("Type"), "fieldname": "root_type", "fieldtype": "Data", "width": 110},
		{"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 140},
	]


def _balance_sheet_columns():
	return _profit_and_loss_columns()
