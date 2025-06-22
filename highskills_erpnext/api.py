import frappe
from frappe import _

@frappe.whitelist(allow_guest=True)
def custom_update_password(key=None, old_password=None, new_password=None, logout_all_sessions=0):
    # Ensure logout_all_sessions is an integer and valid
    try:
        if isinstance(logout_all_sessions, str) and logout_all_sessions.isdigit():
            logout_all_sessions = int(logout_all_sessions)
        elif isinstance(logout_all_sessions, int):
            pass
        else:
            logout_all_sessions = 0
    except Exception:
        logout_all_sessions = 0
    # Call the original method with correct argument order
    from frappe.core.doctype.user.user import update_password as orig_update_password
    result = orig_update_password(
        new_password=new_password,
        logout_all_sessions=logout_all_sessions,
        key=key,
        old_password=old_password
    )
    # Return your custom redirect URL instead of /me
    return "/update-profile"
