# Copyright (c) 2026, Highskills and more LTD
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class AIProvisioningResult(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		api_key: DF.Data | None
		customer: DF.Link | None
		customer_email: DF.Data | None
		payment_entry: DF.Link
		provisioning_webhook: DF.Link
		reference_doctype: DF.Literal["Sales Order", "Sales Invoice"]
		reference_name: DF.DynamicLink | None
		response_json: DF.Code | None
		status_code: DF.Int
		success: DF.Check
		tenant_url: DF.Data | None
	# end: auto-generated types

	@frappe.whitelist()
	def retry(self):
		"""Desk-side recovery for a failed attempt (e.g. the target app was
		briefly unreachable) - re-fires the exact same request and updates
		this same row in place, same request-building code as the original
		on_submit flow (highskills_erpnext.ai_provisioning.fire_webhook).
		"""
		from highskills_erpnext.ai_provisioning import fire_webhook

		webhook = frappe.get_doc("AI Provisioning Webhook", self.provisioning_webhook)
		payment_entry = frappe.get_doc("Payment Entry", self.payment_entry)
		order = frappe.get_doc(self.reference_doctype, self.reference_name)

		result = fire_webhook(webhook, payment_entry, order)
		self.update(result)
		self.save(ignore_permissions=True)

		return result
