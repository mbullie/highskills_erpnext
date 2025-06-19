import frappe
from frappe import _

@frappe.whitelist(allow_guest=True)
def custom_update_password(key=None, old_password=None, new_password=None, logout_all_sessions=0):
    # Call the original method
    from frappe.core.doctype.user.user import update_password as orig_update_password
    result = orig_update_password(key, old_password, new_password, logout_all_sessions)
    # Return your custom redirect URL instead of /me
    return "/update-profile"
