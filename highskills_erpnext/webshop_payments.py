"""Shared helpers for per-customer-type payment routing.

Payment method per customer type (Individual -> PayPal, Company -> manual bank
transfer, or whatever an admin configures) is driven entirely by the
"Payment Method Rules" table on Webshop Settings (see
fixtures/custom_field.json and the Webshop Payment Method Rule child
doctype). Nothing here is hardcoded - editing rows in that table is the
supported way to change payment methods per customer type in the future.
"""

from contextlib import contextmanager

import frappe


@contextmanager
def as_administrator():
	"""Temporarily elevate to Administrator for a privileged system operation.

	Used around core ERPNext calls that assume an internal, accounting-privileged
	caller (e.g. payment_request.make_payment_request, Payment
	Request.on_payment_authorized) but are, in the webshop flow, reached via the
	customer's own (deliberately minimal) session or an unauthenticated payment
	gateway callback. The real authorization question in each caller - "is this
	genuinely this customer's own order", "did the gateway actually confirm this
	payment" - should already be answered before entering this context; this only
	elevates the actual privileged write.
	"""
	current_user = frappe.session.user
	try:
		frappe.set_user("Administrator")
		yield
	finally:
		frappe.set_user(current_user)


def get_payment_method_rule(customer_type):
	"""Return the Webshop Payment Method Rule row configured for a customer type, or None."""
	if not customer_type:
		return None

	cart_settings = frappe.get_cached_doc("Webshop Settings")
	for row in cart_settings.get("payment_method_rules") or []:
		if row.customer_type == customer_type:
			return row

	return None


def get_customer_for_reference(reference_doctype, reference_name):
	"""Resolve the Customer linked to a Sales Order / Sales Invoice / Quotation."""
	if not reference_doctype or not reference_name:
		return None

	fieldname = "party_name" if reference_doctype == "Quotation" else "customer"
	customer = frappe.db.get_value(reference_doctype, reference_name, fieldname)

	if customer and frappe.db.exists("Customer", customer):
		return customer

	return None


def get_customer_type_for_reference(reference_doctype, reference_name):
	customer = get_customer_for_reference(reference_doctype, reference_name)
	if not customer:
		return None

	return frappe.db.get_value("Customer", customer, "customer_type")


def get_company_bank_account(company):
	"""Return the company's Bank Account doc used to display bank-transfer instructions."""
	bank_account_name = frappe.db.get_value(
		"Bank Account",
		{"is_company_account": 1, "company": company},
		"name",
	)

	if not bank_account_name:
		return None

	return frappe.get_doc("Bank Account", bank_account_name)
