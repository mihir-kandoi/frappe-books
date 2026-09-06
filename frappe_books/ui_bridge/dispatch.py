"""Argument checks shared by the Books interface dispatchers."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any

import frappe


def call_handler(handler: Callable[..., Any], method: str, args: list[Any]) -> Any:
	"""Call a dispatcher handler after checking that the argument count fits."""
	try:
		inspect.signature(handler).bind(*args)
	except TypeError:
		frappe.throw(f"Invalid arguments for Books operation {method}")
	return handler(*args)
