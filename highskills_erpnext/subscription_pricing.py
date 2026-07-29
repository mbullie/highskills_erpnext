"""Prepaid-term pricing for SaaS/subscription items.

Design: the admin enters the natural MONTHLY rate in Item Price (per price
list, exactly like any other item - this is what already gives us the
ILS/USD split via the standard price_list mechanism, nothing new needed
there). For any item with `Subscription Term (Months)` set, this module
computes the actual one-time charge as `monthly_rate * term_months` and
writes that onto the transaction's line rate/amount - always recomputed
fresh from Item Price, never multiplied in place, so re-running validate()
on a draft (which happens repeatedly as a customer edits their cart) can
never compound the price.

Hooked onto Quotation and Sales Order via `before_validate` (hooks.py
doc_events) - deliberately *before* validate, not on validate itself, so the
adjusted rate is in place before the standard calculate_taxes_and_totals()
runs during the controller's own validate(). That's also why tax needs no
special handling: it's a percentage applied to whatever the line total is
by the time it runs, so it naturally applies to the full term price once
this has already adjusted it.
"""

import frappe
from frappe import _
from frappe.utils import flt


def apply_subscription_term_pricing(doc, method=None):
	if not doc.get("selling_price_list"):
		return

	for item in doc.get("items") or []:
		term_months = frappe.db.get_value("Item", item.item_code, "term_months")
		if not term_months or term_months <= 1:
			continue

		monthly_rate = frappe.db.get_value(
			"Item Price",
			{
				"item_code": item.item_code,
				"price_list": doc.selling_price_list,
				"selling": 1,
			},
			"price_list_rate",
		)
		if not monthly_rate:
			continue

		total_rate = flt(monthly_rate) * term_months

		item.price_list_rate = total_rate
		item.rate = total_rate
		item.discount_percentage = 0
		item.discount_amount = 0
		item.amount = flt(total_rate * item.qty)

		if item.meta.has_field("term_price_breakdown"):
			item.term_price_breakdown = _(
				"{0}/month x {1} months = {2}"
			).format("%.2f" % flt(monthly_rate), term_months, "%.2f" % total_rate)
