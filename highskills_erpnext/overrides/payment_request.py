"""Per-customer-type payment routing for the webshop checkout "Pay" button.

Registered via hooks.py `override_whitelisted_methods` in place of
erpnext.accounts.doctype.payment_request.payment_request.make_payment_request.
Webshop's own "Pay" button (webshop/templates/pages/order.html) links straight
to that whitelisted method, so intercepting it here - rather than duplicating
webshop's order.html - is the smallest, most upgrade-safe way to branch
payment method by Customer.customer_type using the Webshop Payment Method
Rule table on Webshop Settings (see webshop_payments.py).

Ownership + privilege handling (see custom_make_payment_request below): core
`make_payment_request` (erpnext commit 78fc942, "fix: better permissions on
make payment request") now does `frappe.has_permission("Payment Request",
"create")` and `frappe.has_permission(args.dt, "read", args.dn)` against
whoever's session is calling it. That's the right check for an internal Desk
user creating a Payment Request against someone else's document, but wrong
for this endpoint: webshop's "Pay" button is hit directly by the customer's
own browser session, and a customer's Website User role was never meant to
carry blanket read/create access to Sales Order / Payment Request - nor
should it. Rather than widen what the `Customer` role can see (which would
let any customer read *any* Sales Order, not just their own), this validates
ownership the same way the rest of this app already does for portal pages
(`frappe.has_website_permission`, see www/bank_transfer.py), then performs
the actual privileged operation as Administrator on the customer's behalf -
the customer's own session never needs those permissions at all.

CustomPaymentRequest.on_payment_authorized (below) applies the same pattern
one level deeper: every payment gateway's confirmation callback ultimately
calls `<Payment Request doc>.run_method("on_payment_authorized", ...)`, which
in turn calls `PaymentRequest.set_as_paid()` -> `create_payment_entry()` ->
`get_account_details()` -> `frappe.has_permission("Payment Entry", ...)`.
Same assumption-mismatch, just one call deeper and gateway-agnostic - fixed
once here instead of per-gateway (e.g. in paypal_settings.confirm_payment,
which would need duplicating for every future gateway). By the time this
runs, the gateway has already confirmed the charge; recording that is a
system operation, not something the calling session's own permissions
should gate.
"""

from urllib.parse import quote

import frappe
from frappe import _

from erpnext.accounts.doctype.payment_request.payment_request import (
	make_payment_request as core_make_payment_request,
)
from webshop.webshop.doctype.override_doctype.payment_request import (
	PaymentRequest as WebshopPaymentRequest,
)

from highskills_erpnext.webshop_payments import (
	as_administrator,
	get_customer_type_for_reference,
	get_payment_method_rule,
)


class CustomPaymentRequest(WebshopPaymentRequest):
	def on_payment_authorized(self, status=None):
		with as_administrator():
			return super().on_payment_authorized(status)


@frappe.whitelist()
def custom_make_payment_request(**args):
	args = frappe._dict(args)

	# Only shopping-cart checkout is customer-type-aware; every other caller
	# (Desk users creating a Payment Request against a Purchase Order, etc.)
	# keeps stock behaviour untouched.
	if args.get("order_type") != "Shopping Cart":
		return core_make_payment_request(**args)

	ref_doc = frappe.get_doc(args.dt, args.dn)

	# The one real authorization check: is this genuinely the calling
	# customer's own order? Uses the portal-appropriate permission system,
	# not the internal Desk role system - see module docstring.
	if not frappe.has_website_permission(ref_doc):
		frappe.throw(_("Not Permitted"), frappe.PermissionError)

	customer_type = get_customer_type_for_reference(args.get("dt"), args.get("dn"))
	rule = get_payment_method_rule(customer_type)

	# No rule configured at all (Webshop Payment Method Rules table empty) ->
	# fall back to stock single-gateway behaviour so an unconfigured site
	# keeps working exactly as before.
	if rule is None:
		with as_administrator():
			return core_make_payment_request(**args)

	if not rule.payment_gateway_account:
		# This customer type is on the manual bank-transfer flow: no Payment
		# Request/gateway involved at all, send them to the instructions page.
		# (bank_transfer.py does its own has_website_permission check too,
		# so this redirect is safe even without the check above.)
		#
		# frappe.utils.get_url() deliberately not used here: site_config's
		# host_name is set to an internal Docker address (frontend:8080) so
		# wkhtmltopdf can reach its own assets during PDF generation - and
		# get_url() always prefers host_name when it's set, over the live
		# request's own Host header, for every caller site-wide. Correct for
		# wkhtmltopdf, wrong here: this redirect goes straight to the
		# customer's own browser, which can't resolve a Docker-internal
		# hostname. get_host_name_from_request() reads
		# frappe.local.request.host directly, bypassing host_name entirely -
		# always correct for a real browser-initiated request like this one.
		host = frappe.utils.get_host_name_from_request() or frappe.utils.get_url()
		frappe.local.response["type"] = "redirect"
		frappe.local.response["location"] = host + "/bank-transfer?dt={0}&dn={1}".format(
			quote(args.dt), quote(args.dn)
		)
		return

	args["payment_gateway_account"] = rule.payment_gateway_account
	with as_administrator():
		return core_make_payment_request(**args)
