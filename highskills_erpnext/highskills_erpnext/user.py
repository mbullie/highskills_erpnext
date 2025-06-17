import frappe
from frappe import _
from frappe.model.naming import append_number_if_name_exists
from frappe.website.utils import cleanup_page_name
from frappe.website.utils import is_signup_disabled
from frappe.utils import random_string, escape_html
from highskills_erpnext.highskills_erpnext.utils import get_country_code


def validate_username_duplicates(doc, method):
	while not doc.username or doc.username_exists():
		doc.username = append_number_if_name_exists(
			doc.doctype, cleanup_page_name(doc.full_name), fieldname="username"
		)
	if " " in doc.username:
		doc.username = doc.username.replace(" ", "")

	if len(doc.username) < 4:
		doc.username = doc.email.replace("@", "").replace(".", "")


@frappe.whitelist(allow_guest=True)
def sign_up(email, full_name):
	if is_signup_disabled():
		frappe.throw(_("Sign Up is disabled"), _("Not Allowed"))

	user = frappe.db.get("User", {"email": email})
	if user:
		if user.enabled:
			return 0, _("Already Registered")
		else:
			return 0, _("Registered but disabled")
	else:
		if frappe.db.get_creation_count("User", 60) > 300:
			frappe.respond_as_web_page(
				_("Temporarily Disabled"),
				_(
					"Too many users signed up recently, so the registration is disabled. Please try back in an hour"
				),
				http_status_code=429,
			)

	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": escape_html(full_name),
			"country": "",
			"enabled": 1,
			"new_password": random_string(10),
			"user_type": "Website User",
		}
	)
	user.flags.ignore_permissions = True
	user.flags.ignore_password_policy = True
	user.insert()

	# set default signup role as per Portal Settings
	default_role = frappe.db.get_single_value("Portal Settings", "default_role")
	if not default_role:
		default_role = "Customer"
	if default_role:
		user.add_roles(default_role)

	set_country_from_ip(None, user.name)

	if user.flags.email_sent:
		return 1, _("Please check your email for verification")
	else:
		return 2, _("Please ask your administrator to verify your sign-up")


def set_country_from_ip(login_manager=None, user=None):
	if not user and login_manager:
		user = login_manager.user
	frappe.db.set_value("User", user, "country", get_country_code())
	return
