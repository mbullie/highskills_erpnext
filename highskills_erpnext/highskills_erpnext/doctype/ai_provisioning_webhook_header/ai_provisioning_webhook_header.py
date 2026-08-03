# Copyright (c) 2026, Highskills and more LTD
# For license information, please see license.txt

from frappe.model.document import Document


class AIProvisioningWebhookHeader(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		key: DF.SmallText | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		value: DF.SmallText | None
	# end: auto-generated types

	pass
