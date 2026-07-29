"""Bypass a core-ERPNext Item permission check that blocks Customer-role
shoppers from adding anything to their cart.

Registered via hooks.py `override_whitelisted_methods` in place of
webshop.webshop.shopping_cart.cart.update_cart.

erpnext/stock/get_item_details.py::get_item_details() calls
`item.check_permission()` for every item already on the cart quotation on
every single update_cart call (not just the item being added/changed) - a
raw doctype-level "read" check on Item. Out of the box the Customer role
carries no read/select grant on Item at all (webshop's own product browsing
goes through "Website Item" instead, which does), so this has always failed
for a genuine Customer-role session; it just went unexercised until real
customer accounts were used end-to-end.

Widening the Customer role's standing permissions on Item was considered and
rejected: unlike Account (see fixtures/custom_docperm.json, where
erpnext.accounts.party.get_party_account's permission check goes through the
low-level frappe.permissions.has_permission() with no bypass other than
Administrator), the Item check here goes through
frappe.model.document.Document.has_permission(), which honours
`doc.flags.ignore_permissions` on the specific Document instance before ever
evaluating role permissions. frappe.get_cached_doc() reuses the same
in-request cached instance across repeated calls for the same doctype+name,
so pre-fetching and flagging every Item that will end up on the cart - before
handing off to the real update_cart - satisfies the later internal check
without granting Customer any standing access to Item.
"""

import frappe

from webshop.webshop.shopping_cart.cart import _get_cart_quotation
from webshop.webshop.shopping_cart.cart import update_cart as core_update_cart


@frappe.whitelist()
def custom_update_cart(item_code, qty, additional_notes=None, with_items=False):
	quotation = _get_cart_quotation()
	item_codes = {d.item_code for d in (quotation.get("items") or [])}
	if item_code:
		item_codes.add(item_code)

	for code in item_codes:
		frappe.get_cached_doc("Item", code).flags.ignore_permissions = True

	return core_update_cart(
		item_code=item_code, qty=qty, additional_notes=additional_notes, with_items=with_items
	)
