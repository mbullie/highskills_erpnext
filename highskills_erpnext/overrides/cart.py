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
	_flag_cart_items_ignore_permissions(_get_cart_quotation())
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
