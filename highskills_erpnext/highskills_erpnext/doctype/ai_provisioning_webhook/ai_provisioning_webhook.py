# Copyright (c) 2026, Highskills and more LTD
# For license information, please see license.txt

from urllib.parse import urlparse

import frappe
from frappe import _
from frappe.model.document import Document


class AIProvisioningWebhook(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from highskills_erpnext.highskills_erpnext.doctype.ai_provisioning_webhook_header.ai_provisioning_webhook_header import (
			AIProvisioningWebhookHeader,
		)

		condition: DF.SmallText | None
		enabled: DF.Check
		request_method: DF.Literal["POST", "PUT"]
		request_url: DF.SmallText
		rule_name: DF.Data
		webhook_headers: DF.Table[AIProvisioningWebhookHeader]
		webhook_json: DF.Code | None
	# end: auto-generated types

	def validate(self):
		self.validate_request_url()
		self.validate_condition()

	def validate_request_url(self):
		if not urlparse(self.request_url).netloc:
			frappe.throw(_("Check Request URL"))

	def validate_condition(self):
		if not self.condition:
			return

		from highskills_erpnext.ai_provisioning import get_condition_context

		dummy_payment_entry = frappe.new_doc("Payment Entry")
		dummy_order = frappe.new_doc("Sales Order")
		try:
			frappe.safe_eval(
				self.condition, eval_locals=get_condition_context(dummy_payment_entry, dummy_order)
			)
		except Exception as e:
			frappe.throw(_("Invalid Condition: {0}").format(str(e)))
