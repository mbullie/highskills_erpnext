"""Bypass a core-ERPNext Item permission check that blocks Customer-role
shoppers from using the cart/checkout flow.

Registered via hooks.py `override_whitelisted_methods` in place of several
webshop.webshop.shopping_cart.cart whitelisted functions.

erpnext/stock/get_item_details.py::get_item_details() calls
`item.check_permission()` for every item on the cart quotation - a raw
doctype-level "read" check on Item. Out of the box the Customer role carries
no read/select grant on Item at all (webshop's own product browsing goes
through "Website Item" instead, which does), so this has always failed for a
genuine Customer-role session; it just went unexercised until real customer
accounts were used end-to-end.

Widening the Customer role's standing permissions on Item was considered and
rejected: unlike Account (see fixtures/custom_docperm.json, where
erpnext.accounts.party.get_party_account's permission check goes through the
low-level frappe.permissions.has_permission() with no bypass other than
Administrator), the Item check here goes through
frappe.model.document.Document.has_permission(), which honours
`doc.flags.ignore_permissions` on the specific Document instance before ever
evaluating role permissions. frappe.get_cached_doc() reuses the same
in-request cached instance across repeated calls for the same doctype+name,
so pre-fetching and flagging every Item already on the cart - before handing
off to the real core function - satisfies every later internal check reached
during that same request, without granting Customer any standing access to
Item.

This isn't specific to update_cart: AccountsController.validate() (erpnext/
controllers/accounts_controller.py) unconditionally recomputes item details
on every save/submit of a Quotation or Sales Order, so *any* cart/checkout
endpoint that saves or submits the cart quotation hits the same check -
confirmed by reading webshop/webshop/shopping_cart/cart.py in full. Every
whitelisted function there that does so is wrapped below; the two that don't
touch save/submit (get_shipping_addresses, get_billing_addresses, etc.) are
left untouched.
"""

import frappe

from webshop.webshop.shopping_cart.cart import _get_cart_quotation
from webshop.webshop.shopping_cart.cart import apply_coupon_code as core_apply_coupon_code
from webshop.webshop.shopping_cart.cart import apply_shipping_rule as core_apply_shipping_rule
from webshop.webshop.shopping_cart.cart import get_cart_quotation as core_get_cart_quotation
from webshop.webshop.shopping_cart.cart import place_order as core_place_order
from webshop.webshop.shopping_cart.cart import request_for_quotation as core_request_for_quotation
from webshop.webshop.shopping_cart.cart import update_cart as core_update_cart
from webshop.webshop.shopping_cart.cart import update_cart_address as core_update_cart_address

from highskills_erpnext.webshop_payments import get_customer_type_for_reference, get_payment_method_rule


def _flag_cart_items_ignore_permissions(quotation):
	for item in quotation.get("items") or []:
		frappe.get_cached_doc("Item", item.item_code).flags.ignore_permissions = True


@frappe.whitelist()
def custom_update_cart(item_code, qty, additional_notes=None, with_items=False):
	quotation = _get_cart_quotation()
	_flag_cart_items_ignore_permissions(quotation)
	if item_code:
		frappe.get_cached_doc("Item", item_code).flags.ignore_permissions = True

	return core_update_cart(
		item_code=item_code, qty=qty, additional_notes=additional_notes, with_items=with_items
	)


@frappe.whitelist()
def custom_place_order():
	"""For manual-bank-transfer customer types (e.g. Company), stop short of
	creating a Sales Order - just submit the Quotation. Staff manually
	convert it to a Sales Order in Desk once the customer's PO is confirmed
	(uploaded at /bank-transfer, or sent by email) - this can happen well
	after checkout, so nothing here should assume a Sales Order exists yet.
	See www/bank_transfer.py module docstring for the full flow.

	Every other customer type (e.g. Individual/PayPal) is unaffected - core
	update_cart already creates+submits a Sales Order immediately, matching
	PayPal's instant/automatic payment.
	"""
	quotation = _get_cart_quotation()
	_flag_cart_items_ignore_permissions(quotation)

	customer_type = get_customer_type_for_reference("Quotation", quotation.name)
	rule = get_payment_method_rule(customer_type)

	if rule is not None and not rule.payment_gateway_account:
		cart_settings = frappe.get_cached_doc("Webshop Settings")
		quotation.company = cart_settings.company
		quotation.flags.ignore_permissions = True

		if not (quotation.shipping_address_name or quotation.customer_address):
			frappe.throw(frappe._("Set Shipping Address or Billing Address"))

		# Set directly here (not via fetch_from) - party_name is a Dynamic
		# Link (Customer or Lead depending on quotation_to), so a plain
		# fetch_from can't reliably resolve it. We already have customer_type
		# from the payment-method-rule lookup above, so just use it - lets a
		# Quotation "On Submit" Notification condition on Individual vs
		# Company via plain `doc.customer_type` attribute access, since
		# Notification conditions have no frappe.db access at all (confirmed
		# via notification.py's own get_context(), which only exposes
		# frappe.utils - not frappe.db).
		if quotation.meta.has_field("customer_type"):
			quotation.customer_type = customer_type

		# Set explicitly, not left to any assumed auto-stamping - confirmed
		# via bench console that frappe.new_doc() never populates `language`
		# on its own, and nothing in webshop/erpnext's checkout flow sets it
		# either, so every Quotation through this flow ended up with
		# language=None until something else (most likely staff opening/
		# saving it in Desk later, from their own admin session) stamped it
		# "en" regardless of the customer's actual language. This is the one
		# point in the flow with reliable access to the customer's own
		# session language - Notification's attach_print and our print
		# formats' is_rtl() both key off this field, so it needs to actually
		# reflect the customer, not whoever last touched the document in Desk.
		if quotation.meta.has_field("language"):
			quotation.language = frappe.local.lang

		quotation.submit()

		if hasattr(frappe.local, "cookie_manager"):
			frappe.local.cookie_manager.delete_cookie("cart_count")

		# webshop/templates/pages/cart.js's place_order() callback hardcodes
		# `window.location.href = '/orders/' + r.message` - that route
		# (erpnext/hooks.py website_route_rules) hardcodes doctype="Sales
		# Order" for whatever name it's given, so redirecting it at a
		# Quotation name fails (frappe.get_doc("Sales Order", "SAL-QTN-...")
		# doesn't exist - Frappe's website page framework maps that to a 403
		# rather than a 404, to avoid leaking record existence). Returning a
		# structured object here instead of a bare name lets our own JS
		# override (public/js/highskills_erpnext-web.bundle.js) redirect
		# straight to /bank-transfer instead. The Individual/PayPal branch
		# below (core_place_order) is untouched and still returns a bare
		# Sales Order name string, matching what cart.js already expects.
		return {"name": quotation.name, "doctype": "Quotation"}

	return core_place_order()


@frappe.whitelist()
def custom_update_cart_address(address_type, address_name):
	_flag_cart_items_ignore_permissions(_get_cart_quotation())
	return core_update_cart_address(address_type=address_type, address_name=address_name)


@frappe.whitelist()
def custom_apply_shipping_rule(shipping_rule):
	_flag_cart_items_ignore_permissions(_get_cart_quotation())
	return core_apply_shipping_rule(shipping_rule=shipping_rule)


@frappe.whitelist(allow_guest=True)
def custom_apply_coupon_code(applied_code, applied_referral_sales_partner=None):
	_flag_cart_items_ignore_permissions(_get_cart_quotation())
	return core_apply_coupon_code(
		applied_code=applied_code, applied_referral_sales_partner=applied_referral_sales_partner
	)


@frappe.whitelist()
def custom_request_for_quotation():
	_flag_cart_items_ignore_permissions(_get_cart_quotation())
	return core_request_for_quotation()


@frappe.whitelist()
def custom_get_cart_quotation(doc=None):
	_flag_cart_items_ignore_permissions(_get_cart_quotation())
	return core_get_cart_quotation(doc=doc)
