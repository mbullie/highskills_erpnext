# Copyright (c) 2026, Highskills and more LTD
# License: MIT

"""Bank-transfer instructions + proof-of-payment upload for Company (B2B)
webshop checkout.

Reached via the redirect issued by
highskills_erpnext.overrides.payment_request.custom_make_payment_request
when the paying customer's type has no Payment Gateway Account configured
in Webshop Settings > Payment Method Rules (the manual bank-transfer path).
No Payment Request/gateway is ever created for this flow - Accounts
reconciles the wire transfer manually and posts a Payment Entry, same as any
other B2B invoice.
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
	context.title = _("Bank Transfer Instructions")
	context.doc = ref_doc
	context.reference_doctype = dt
	context.reference_name = dn
	context.amount_due = ref_doc.get("outstanding_amount") or ref_doc.get("grand_total")
	context.currency = ref_doc.get("currency")
	context.already_uploaded = bool(ref_doc.get("payment_proof_uploaded"))

	cart_settings = frappe.get_cached_doc("Webshop Settings")
	bank_account = get_company_bank_account(ref_doc.get("company") or cart_settings.company)
	context.bank_account = bank_account


@frappe.whitelist()
def upload_payment_proof(dt, dn):
	if frappe.session.user == "Guest":
		frappe.throw(_("Not Permitted"), frappe.PermissionError)

	if dt not in ("Sales Order", "Sales Invoice", "Quotation"):
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

	if ref_doc.meta.has_field("payment_proof_uploaded"):
		ref_doc.db_set("payment_proof_uploaded", 1, update_modified=False)

	return {"success": True}
