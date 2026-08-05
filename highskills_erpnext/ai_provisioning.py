"""AI Provisioning Webhook: on Payment Entry submit, call the purchased
SaaS product's back-end and capture the response (API key + tenant URL)
for a Notification to email the customer.

Registered as an *additional* handler in hooks.py's Payment Entry
`on_submit` doc_events, alongside api_subscription.on_payment_entry_submit
(which owns entitlement windows and is untouched by this module).

Frappe's core Webhook doctype was considered and rejected: it's
fire-and-forget and can't capture a response - the whole point here is
relaying the returned key/URL back to the customer. `AI Provisioning
Webhook` mirrors Webhook's own request-building fields/behaviour as
closely as possible (condition, request_url, request_method, Jinja
webhook_json body, plain key/value headers - see
frappe/integrations/doctype/webhook/webhook.py for the pattern this
copies), but always fires on Payment Entry submit rather than exposing a
generic DocType/Doc Event picker, and always writes its result to `AI
Provisioning Result` instead of only logging it.

Payment Entry itself carries no line items - `references` (Payment Entry
Reference child table) is the only link back to what was actually bought,
and only resolves to a Sales Order/Sales Invoice, which does have `.items`
(same resolution api_subscription.py already does to open entitlement
windows). So every rule's `condition`/`webhook_json` is evaluated against
BOTH `doc` (the Payment Entry) and `order` (the resolved Sales Order/Sales
Invoice) - unlike core Webhook, which only ever exposes a single `doc`.
"""

import json

import frappe
import requests
from frappe.utils.safe_exec import get_safe_globals


def on_payment_entry_submit(doc, method=None):
	frappe.enqueue(
		"highskills_erpnext.ai_provisioning.run_provisioning_webhooks",
		queue="short",
		enqueue_after_commit=True,
		payment_entry_name=doc.name,
	)


def run_provisioning_webhooks(payment_entry_name):
	payment_entry = frappe.get_doc("Payment Entry", payment_entry_name)

	webhook_names = frappe.get_all("AI Provisioning Webhook", filters={"enabled": 1}, pluck="name")
	if not webhook_names:
		return
	webhooks = [frappe.get_doc("AI Provisioning Webhook", name) for name in webhook_names]

	for reference in payment_entry.get("references") or []:
		if reference.reference_doctype not in ("Sales Order", "Sales Invoice"):
			continue

		order = frappe.get_doc(reference.reference_doctype, reference.reference_name)

		language = _resolve_customer_language(order.customer)

		for webhook in webhooks:
			if not _condition_matches(webhook, payment_entry, order):
				continue

			result = fire_webhook(webhook, payment_entry, order)
			_log_result(webhook, payment_entry, order, result, language)


def _resolve_customer_language(customer):
	"""Background jobs have no request/session, so frappe.local.lang here
	is just the site's base language - not the customer's. order.language
	isn't reliable either (only ever set on the Quotation for the
	Company/bank-transfer flow, and not guaranteed to survive staff
	manually converting it to a Sales Order). The customer's own
	User.language, set once at signup (api_signup.py), is the one source
	that's always correct - reached the same way
	api_subscription.has_active_entitlement() looks up Portal User, just
	in the opposite direction (customer -> user, not user -> customer).
	"""
	portal_user = frappe.db.get_value("Portal User", {"parent": customer}, "user")
	if not portal_user:
		return frappe.local.lang
	return frappe.db.get_value("User", portal_user, "language") or frappe.local.lang


def get_condition_context(payment_entry, order):
	return {
		"doc": payment_entry,
		"order": order,
		"utils": get_safe_globals().get("frappe").get("utils"),
	}


def _condition_matches(webhook, payment_entry, order):
	if not webhook.condition:
		return True

	try:
		return bool(
			frappe.safe_eval(webhook.condition, eval_locals=get_condition_context(payment_entry, order))
		)
	except Exception:
		frappe.log_error(
			title="AI Provisioning Webhook condition failed",
			message=f"Rule: {webhook.name}\n\n{frappe.get_traceback()}",
		)
		return False


def _get_webhook_data(webhook, payment_entry, order):
	if not webhook.webhook_json:
		return {}

	rendered = frappe.render_template(webhook.webhook_json, get_condition_context(payment_entry, order))
	return json.loads(rendered)


def _get_webhook_headers(webhook):
	headers = {}
	for row in webhook.get("webhook_headers") or []:
		if row.get("key") and row.get("value"):
			headers[row.get("key")] = row.get("value")
	return headers


def fire_webhook(webhook, payment_entry, order):
	"""Makes the actual HTTP call and returns the fields to save on an `AI
	Provisioning Result` row. Shared by the main on_submit flow above and
	`AI Provisioning Result.retry()` - exactly one place builds and sends
	the request.
	"""
	result = {"success": 0, "status_code": None, "response_json": "", "api_key": "", "tenant_url": ""}

	try:
		data = _get_webhook_data(webhook, payment_entry, order)
		headers = _get_webhook_headers(webhook)
		request_url = frappe.render_template(
			webhook.request_url, get_condition_context(payment_entry, order)
		)

		response = requests.request(
			method=webhook.request_method or "POST",
			url=request_url,
			data=frappe.as_json(data),
			headers=headers,
			timeout=30,
		)
		result["status_code"] = response.status_code
		result["response_json"] = response.text

		response.raise_for_status()
		parsed = response.json()
		result["api_key"] = parsed.get("api_key") or ""
		result["tenant_url"] = parsed.get("tenant_url") or ""
		result["success"] = 1
	except Exception:
		result["response_json"] = result["response_json"] or frappe.get_traceback()

	return result


def _log_result(webhook, payment_entry, order, result, language):
	log = frappe.new_doc("AI Provisioning Result")
	log.update(
		{
			"provisioning_webhook": webhook.name,
			"payment_entry": payment_entry.name,
			"reference_doctype": order.doctype,
			"reference_name": order.name,
			"customer": order.get("customer"),
			"customer_email": order.get("contact_email"),
			"language": language,
			**result,
		}
	)
	log.flags.ignore_permissions = True

	# This insert triggers the customer-facing Notification (Document Event
	# = New) synchronously, as part of the doc-event hook chain - but this
	# whole function runs inside a background job (see on_payment_entry_
	# submit's frappe.enqueue), which has no request/session of its own, so
	# frappe.local.lang would otherwise just be the site's base language
	# regardless of the customer. print_language() scopes the customer's
	# resolved language to exactly this insert - see plan/session notes on
	# why this is safe despite print_language() itself lacking a
	# try/finally: an exception here aborts this job immediately, and
	# frappe.utils.background_jobs.execute_job() unconditionally calls
	# frappe.destroy() after every job (success or failure) before the
	# worker can pick up another one, so there's no cross-job leakage.
	from frappe.translate import print_language

	with print_language(language):
		log.insert()
