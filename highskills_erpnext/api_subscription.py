"""SaaS entitlement windows: prepaid term, not recurring billing.

Design note (why this doesn't use ERPNext's `Subscription` doctype):
`Subscription.validate_end_date()` throws unless `end_date` is strictly
after `start_date + (billing_interval * billing_interval_count)` - i.e. the
doctype requires at least one full billing cycle (and therefore one
auto-generated invoice) to complete before it can end. That's the opposite
of what this billing model needs: SaaS terms are already paid in full as a
single one-time charge at checkout, so a second, later invoice for the same
term would be pure duplication with no real fix available short of
patching core. Tracking the paid date range directly on the Sales Order
(via the `entitlement_start_date`/`entitlement_end_date` custom fields,
see fixtures/custom_field.json) sidesteps that constraint entirely and is
far simpler than fighting the recurring-billing engine to make it inert.

Entitlement windows are only ever opened by `on_payment_entry_submit`
(wired up in hooks.py `doc_events`) - never when the order is placed - so
access only begins once payment is actually confirmed:
- PayPal (Personal): a Payment Entry is submitted automatically the moment
  PayPal confirms payment.
- Bank transfer (Company): a Payment Entry only exists once Accounts
  manually reconciles the wire transfer against the uploaded proof.
"""

import frappe
from frappe.utils import add_months, getdate


def on_payment_entry_submit(doc, method=None):
	for reference in doc.get("references") or []:
		if reference.reference_doctype not in ("Sales Order", "Sales Invoice"):
			continue

		_open_entitlement_window(reference.reference_doctype, reference.reference_name)


def _open_entitlement_window(reference_doctype, reference_name):
	ref_doc = frappe.get_doc(reference_doctype, reference_name)

	if not ref_doc.meta.has_field("entitlement_start_date"):
		return

	if ref_doc.get("entitlement_start_date"):
		# Only the first confirmed payment opens the window - a later
		# Payment Entry against the same order (e.g. a top-up) must not
		# push the start date out.
		return

	term_months = _get_term_months(ref_doc)
	if not term_months:
		return

	start_date = getdate()
	end_date = add_months(start_date, term_months)

	ref_doc.db_set("entitlement_start_date", start_date, update_modified=False)
	ref_doc.db_set("entitlement_end_date", end_date, update_modified=False)


def _get_term_months(ref_doc):
	for item in ref_doc.get("items") or []:
		term_months = frappe.db.get_value("Item", item.item_code, "term_months")
		if term_months:
			return term_months

	return None


@frappe.whitelist()
def has_active_entitlement(customer: str | None = None):
	"""Called by the SaaS product to decide whether to allow or disallow
	use of the product for a given Customer, based purely on whether today
	falls within a paid Sales Order's entitlement window.
	"""
	if not customer:
		customer = frappe.db.get_value("Portal User", {"user": frappe.session.user}, "parent")

	if not customer:
		return {"active": False}

	today_date = getdate()
	filters = {
		"customer": customer,
		"docstatus": 1,
		"entitlement_start_date": ("<=", today_date),
		"entitlement_end_date": (">=", today_date),
	}
	fields = ["name", "entitlement_start_date", "entitlement_end_date"]

	matches = []
	for reference_doctype in ("Sales Order", "Sales Invoice"):
		matches += [
			{**row, "reference_doctype": reference_doctype}
			for row in frappe.get_all(
				reference_doctype,
				filters=filters,
				fields=fields,
				order_by="entitlement_end_date desc",
				limit_page_length=1,
			)
		]

	if not matches:
		return {"active": False}

	best = max(matches, key=lambda row: row["entitlement_end_date"])

	return {
		"active": True,
		"reference_doctype": best["reference_doctype"],
		"reference_name": best["name"],
		"start_date": best["entitlement_start_date"],
		"end_date": best["entitlement_end_date"],
	}
