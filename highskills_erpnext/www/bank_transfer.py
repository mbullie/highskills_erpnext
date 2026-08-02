# Copyright (c) 2026, Highskills and more LTD
# License: MIT

"""PO confirmation + bank-transfer instructions + proof-of-payment upload for
Company (B2B) webshop checkout.

Reached via the "Pay" button on the customer's `/orders/<name>` page (webshop
core, unmodified - already generic across Quotation/Sales Order/Sales
Invoice), which goes through `make_payment_request` ->
highskills_erpnext.overrides.payment_request.custom_make_payment_request,
which redirects here whenever the paying customer's type has no Payment
Gateway Account configured in Webshop Settings > Payment Method Rules (the
manual bank-transfer path).

Everything here operates on the Quotation, never on a Sales Order, and never
gates one upload on the other: `highskills_erpnext.overrides.cart.
custom_place_order` no longer auto-creates a Sales Order for these customer
types - it just submits the Quotation. Staff manually convert the Quotation
to a Sales Order in Desk (entering the customer's PO number) once they've
reviewed the uploaded PO and/or received it by email - this can happen hours
or days after the customer uploads their PO, and independently of whether
payment proof has been uploaded yet. So the customer can upload their PO
and/or their payment proof here at any time, in any order, without waiting
on staff to have processed anything yet. No Payment Request/gateway is ever
created for this flow - Accounts reconciles the wire transfer manually and
posts a Payment Entry, same as any other B2B invoice.
"""

import frappe
from frappe import _

from highskills_erpnext.webshop_payments import get_company_bank_account

no_cache = 1


def get_context(context):
	dt = frappe.form_dict.get("dt")
	dn = frappe.form_dict.get("dn")

	if not dt or not dn or dt not in ("Sales Order", "Sales Invoice", "Quotation"):
		frappe.throw(_("Not Permitted"), frappe.PermissionError)

	ref_doc = frappe.get_doc(dt, dn)

	if not frappe.has_website_permission(ref_doc):
		frappe.throw(_("Not Permitted"), frappe.PermissionError)

	context.no_header = False
	context.title = _("Purchase Order & Bank Details")
	context.doc = ref_doc
	context.reference_doctype = dt
	context.reference_name = dn
	context.amount_due = ref_doc.get("outstanding_amount") or ref_doc.get("grand_total")
	context.currency = ref_doc.get("currency")

	# PO upload only makes sense before the order is confirmed - once a Sales
	# Order/Invoice exists, the PO has already served its purpose.
	context.show_po_upload = dt == "Quotation"
	context.po_already_uploaded = bool(ref_doc.get("po_uploaded"))
	context.already_uploaded = bool(ref_doc.get("payment_proof_uploaded"))

	cart_settings = frappe.get_cached_doc("Webshop Settings")
	bank_account = get_company_bank_account(ref_doc.get("company") or cart_settings.company)
	context.bank_account = bank_account

	# Raw, unchecked read - same pattern as bank_account/cart_settings above,
	# not frappe.get_doc()+check_permission(), so no risk of re-hitting the
	# Item/Account-style permission wall for a Customer-role viewer.
	context.support_email = frappe.db.get_value("Email Account", {"default_outgoing": 1}, "email_id")


@frappe.whitelist()
def upload_payment_proof(dt, dn, file_type="proof"):
	if frappe.session.user == "Guest":
		frappe.throw(_("Not Permitted"), frappe.PermissionError)

	if dt not in ("Sales Order", "Sales Invoice", "Quotation"):
		frappe.throw(_("Not Permitted"), frappe.PermissionError)

	if file_type not in ("po", "proof"):
		frappe.throw(_("Not Permitted"), frappe.PermissionError)

	ref_doc = frappe.get_doc(dt, dn)

	if not frappe.has_website_permission(ref_doc):
		frappe.throw(_("Not Permitted"), frappe.PermissionError)

	uploaded_file = frappe.request.files.get("file")
	if not uploaded_file:
		frappe.throw(_("Please choose a file to upload"))

	from frappe.utils.file_manager import save_file

	save_file(
		uploaded_file.filename,
		uploaded_file.stream.read(),
		dt,
		dn,
		is_private=1,
	)

	flag_field = "po_uploaded" if file_type == "po" else "payment_proof_uploaded"
	if ref_doc.meta.has_field(flag_field):
		ref_doc.db_set(flag_field, 1, update_modified=False)

	return {"success": True}
