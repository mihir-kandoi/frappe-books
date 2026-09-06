"""FIFO stock valuation shared by stock postings and inventory reports."""

from collections import defaultdict, deque

import frappe

from frappe_books.accounting.money import as_decimal, rounded

STOCK_LEDGER_FIELDS = [
	"date",
	"item",
	"location",
	"batch",
	"serial_number",
	"quantity",
	"rate",
	"reference_type",
	"reference_name",
]


def transaction_stock_value(transaction):
	"""Return the FIFO cost of a stock transaction's ledger entries.

	Outgoing entries consume the oldest layers first. Incoming return entries
	are valued at the current rate of the stock they rejoin, or at their own rate
	when nothing is in stock.
	"""
	items = sorted({row.item for row in transaction.items if row.item})
	if not items:
		return as_decimal(0)
	total = as_decimal(0)
	for entry in computed_entries(items):
		if entry["reference_type"] == transaction.doctype and entry["reference_name"] == transaction.name:
			total += _entry_cost(entry)
	return rounded(total)


def computed_entries(items):
	"""Return the stock ledger rows of the given items with FIFO value changes and balances."""
	raw = frappe.get_all(
		"Books Stock Ledger Entry",
		filters={"item": ["in", items]},
		fields=STOCK_LEDGER_FIELDS,
		order_by="date asc, creation asc",
	)
	layers = defaultdict(deque)
	balances = defaultdict(lambda: {"quantity": as_decimal(0), "value": as_decimal(0)})
	computed = []
	for row in raw:
		key = (row.item, row.location, row.batch or "")
		quantity = as_decimal(row.quantity)
		rate = as_decimal(row.rate)
		opening = balances[key]
		value_change = _consume_layers(layers[key], quantity, rate)
		balance_quantity = opening["quantity"] + quantity
		balance_value = opening["value"] + value_change
		balances[key] = {"quantity": balance_quantity, "value": balance_value}
		computed.append(
			{
				**row,
				"incoming_rate": rounded(rate if quantity > 0 else 0),
				"value_change": rounded(value_change),
				"balance_quantity": balance_quantity,
				"balance_value": rounded(balance_value),
				"valuation_rate": rounded(_valuation_rate(balance_value, balance_quantity)),
				"opening_quantity": opening["quantity"],
				"opening_valuation_rate": _valuation_rate(opening["value"], opening["quantity"]),
			}
		)
	return computed


def _entry_cost(entry):
	quantity = as_decimal(entry["quantity"])
	if quantity < 0:
		return -as_decimal(entry["value_change"])
	if entry["opening_quantity"] > 0:
		return quantity * entry["opening_valuation_rate"]
	return quantity * as_decimal(entry["rate"])


def _consume_layers(queue, quantity, rate):
	if quantity > 0:
		queue.append([quantity, rate])
		return quantity * rate
	value_change = as_decimal(0)
	remaining = abs(quantity)
	while remaining and queue:
		layer_quantity, layer_rate = queue[0]
		taken = min(remaining, layer_quantity)
		value_change -= taken * layer_rate
		remaining -= taken
		if layer_quantity > taken:
			queue[0][0] = layer_quantity - taken
		else:
			queue.popleft()
	# Stock that was never received is valued at the entry's own rate.
	return value_change - remaining * rate


def _valuation_rate(value, quantity):
	return value / quantity if quantity else as_decimal(0)
