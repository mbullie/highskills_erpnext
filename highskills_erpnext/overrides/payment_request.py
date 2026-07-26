"""Per-customer-type payment routing for the webshop checkout "Pay" button.

Registered via hooks.py `override_whitelisted_methods` in place of
erpnext.accounts.doctype.payment_request.payment_request.make_payment_request.
Webshop's own "Pay" button (webshop/templates/pages/order.html) links straight
to that whitelisted method, so intercepting it here - rather than duplicating
webshop's order.html - is the smallest, most upgrade-safe way to branch
payment method by Customer.customer_type using the Webshop Payment Method
Rule table on Webshop Settings (see webshop_payments.py).
"""

from urllib.parse import quote

import frappe

from erpnext.accounts.doctype.payment_request.payment_request import (
	make_payment_request as core_make_payment_request,
)

from highskills_erpnext.webshop_payments import (
	get_customer_type_for_reference,
	get_payment_method_rule,
)


@frappe.whitelist()
def custom_make_payment_request(**args):
	args = frappe._dict(args)

	# Only shopping-cart checkout is customer-type-aware; every other caller
	# (Desk users creating a Payment Request against a Purchase Order, etc.)
	# keeps stock behaviour untouched.
	if args.get("order_type") != "Shopping Cart":
		return core_make_payment_request(**args)

	customer_type = get_customer_type_for_reference(args.get("dt"), args.get("dn"))
	rule = get_payment_method_rule(customer_type)

	# No rule configured at all (Webshop Payment Method Rules table empty) ->
	# fall back to stock single-gateway behaviour so an unconfigured site
	# keeps working exactly as before.
	if rule is None:
		return core_make_payment_request(**args)

	if not rule.payment_gateway_account:
		# This customer type is on the manual bank-transfer flow: no Payment
		# Request/gateway involved at all, send them to the instructions page.
		frappe.local.response["type"] = "redirect"
		frappe.local.response["location"] = frappe.utils.get_url(
			"/bank-transfer?dt={0}&dn={1}".format(quote(args.dt), quote(args.dn))
		)
		return

	args["payment_gateway_account"] = rule.payment_gateway_account
	return core_make_payment_request(**args)
