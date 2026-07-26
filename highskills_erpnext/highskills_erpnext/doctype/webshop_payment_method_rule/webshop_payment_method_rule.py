# Copyright (c) 2026, Highskills and more LTD
# For license information, please see license.txt

from frappe.model.document import Document


class WebshopPaymentMethodRule(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		customer_type: DF.Literal["Individual", "Company"]
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		payment_gateway_account: DF.Link | None
	# end: auto-generated types

	pass
