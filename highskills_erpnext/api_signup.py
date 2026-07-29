"""Custom webshop signup: Personal vs Company account types.

Replaces the stock 2-field (Full Name + Email) Frappe signup with a form that
collects everything the webshop needs up front - country (for price
list/tax selection, see webshop_payments.py sibling logic in Part B/C of the
implementation plan) and, for Company accounts, job title / company name /
company ID.

Every write below uses `ignore_permissions=True` inside this whitelisted,
`allow_guest=True` controller method - exactly the pattern
webshop.webshop.shopping_cart.cart.get_party() already uses to let a plain
Website User get a Customer/Contact record. No DocType permission changes
for Guest/Website User are made or needed anywhere.
"""

import frappe
from frappe import _
from frappe.utils import cint, escape_html
from frappe.utils.nestedset import get_root_of
from frappe.website.utils import is_signup_disabled

ISRAEL_PRICE_LIST = "Israel Selling (ILS)"
EXPORT_PRICE_LIST = "Export Selling (USD)"
INDIVIDUAL_CUSTOMER_GROUP = "Individual"
COMPANY_CUSTOMER_GROUP = "Commercial"


@frappe.whitelist(allow_guest=True)
def custom_sign_up(
	account_type: str,
	first_name: str,
	last_name: str,
	email: str,
	password: str,
	confirm_password: str,
	country: str,
	job_title: str | None = None,
	company_name: str | None = None,
	company_id: str | None = None,
	redirect_to: str | None = None,
):
	if is_signup_disabled():
		frappe.throw(_("Sign Up is disabled"), title=_("Not Allowed"))

	account_type = "Company" if account_type == "Company" else "Individual"

	_validate_required_fields(account_type, first_name, last_name, email, password, confirm_password, country, job_title, company_name, company_id)

	if password != confirm_password:
		frappe.throw(_("Password and Confirm Password do not match"))

	if frappe.db.exists("User", email):
		return 0, _("Already Registered")

	max_signups_allowed_per_hour = cint(frappe.get_system_settings("max_signups_allowed_per_hour") or 300)
	if frappe.db.get_creation_count("User", 60) >= max_signups_allowed_per_hour:
		frappe.respond_as_web_page(
			_("Temporarily Disabled"),
			_("Too many users signed up recently, so the registration is disabled. Please try back in an hour"),
			http_status_code=429,
		)
		return

	first_name = escape_html(first_name.strip())
	last_name = escape_html(last_name.strip())
	company_name = escape_html(company_name.strip()) if company_name else None
	job_title = escape_html(job_title.strip()) if job_title else None

	fullname = f"{first_name} {last_name}".strip()
	customer_name = company_name if account_type == "Company" else fullname

	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": first_name,
			"last_name": last_name,
			"enabled": 1,
			"new_password": password,
			"user_type": "Website User",
			"send_welcome_email": 0,
			"language": frappe.local.lang,
		}
	)
	user.flags.ignore_permissions = True
	user.insert()

	default_role = frappe.get_single_value("Portal Settings", "default_role")
	if default_role:
		user.add_roles(default_role)

	default_price_list = _get_default_price_list(country)

	customer = frappe.new_doc("Customer")
	customer.update(
		{
			"customer_name": customer_name,
			"customer_type": account_type,
			"customer_group": _get_default_customer_group(account_type),
			"territory": get_root_of("Territory"),
			"tax_id": company_id if account_type == "Company" else None,
			"default_price_list": default_price_list,
		}
	)
	customer.append("portal_users", {"user": email})
	customer.flags.ignore_permissions = True
	customer.flags.ignore_mandatory = True
	customer.insert()

	contact = frappe.new_doc("Contact")
	contact.update(
		{
			"first_name": first_name,
			"last_name": last_name,
			"email_ids": [{"email_id": email, "is_primary": 1}],
		}
	)
	if account_type == "Company":
		contact.designation = job_title
		contact.company_name = company_name
	contact.append("links", {"link_doctype": "Customer", "link_name": customer.name})
	contact.flags.ignore_permissions = True
	contact.flags.ignore_mandatory = True
	contact.insert()

	address = frappe.new_doc("Address")
	address.update(
		{
			"address_title": customer_name,
			"address_type": "Billing",
			"address_line1": customer_name,
			"country": country,
		}
	)
	address.append("links", {"link_doctype": "Customer", "link_name": customer.name})
	address.flags.ignore_permissions = True
	address.flags.ignore_mandatory = True
	address.insert()

	if redirect_to:
		from frappe.www.login import sanitize_redirect

		frappe.cache.hset("redirect_after_login", user.name, sanitize_redirect(redirect_to))

	# Log the customer straight in - the whole point of collecting a password
	# on the signup form is to skip the "check your email to set a password"
	# step. This populates frappe.local.response the same way a normal
	# cmd=login call does (message/home_page/redirect_to), so the existing
	# login.js "No App" response handler redirects them without any new
	# frontend code.
	frappe.local.login_manager.login_as(user.name)


def _validate_required_fields(
	account_type, first_name, last_name, email, password, confirm_password, country, job_title, company_name, company_id
):
	required = {
		"first_name": first_name,
		"last_name": last_name,
		"email": email,
		"password": password,
		"confirm_password": confirm_password,
		"country": country,
	}

	if account_type == "Company":
		required.update(
			{
				"job_title": job_title,
				"company_name": company_name,
				"company_id": company_id,
			}
		)

	missing = [key for key, value in required.items() if not value or not str(value).strip()]
	if missing:
		frappe.throw(_("Please fill in all required fields."))

	if not frappe.utils.validate_email_address(email):
		frappe.throw(_("Please enter a valid email address"))

	if not frappe.db.exists("Country", country):
		frappe.throw(_("Please select a valid country"))


def _get_default_customer_group(account_type):
	"""Company -> Commercial, Individual -> Individual.

	Falls back to the sitewide Webshop Settings default if the expected
	Customer Group doesn't exist on site, same defensive pattern as
	`_get_default_price_list`.
	"""
	group = COMPANY_CUSTOMER_GROUP if account_type == "Company" else INDIVIDUAL_CUSTOMER_GROUP

	if frappe.db.exists("Customer Group", group):
		return group

	from webshop.webshop.doctype.webshop_settings.webshop_settings import get_shopping_cart_settings

	return get_shopping_cart_settings().default_customer_group


def _get_default_price_list(country):
	"""Israel -> ILS price list, everyone else -> USD export price list.

	Setting this on the Customer at signup time means every later cart visit
	resolves the right price list for free, via webshop's existing
	`_set_price_list()` (Customer.default_price_list is the first thing it
	checks) - no changes to webshop's cart.py are needed.
	"""
	country_code = frappe.db.get_value("Country", country, "code")
	price_list = ISRAEL_PRICE_LIST if country_code == "il" else EXPORT_PRICE_LIST

	if frappe.db.exists("Price List", price_list):
		return price_list

	return None
