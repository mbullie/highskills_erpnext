import frappe
from frappe import _

@frappe.whitelist(allow_guest=True)
def custom_update_password(key=None, old_password=None, new_password=None, logout_all_sessions=0):
    logout_all_sessions = 0  # Dont force logout all sessions
        
    # Call the original method with correct argument order
    from frappe.core.doctype.user.user import update_password as orig_update_password
    result = orig_update_password(
        new_password=new_password,
        logout_all_sessions=logout_all_sessions,
        key=key,
        old_password=old_password
    )
    # Return your custom redirect URL instead of /me
    user = frappe.session.user
    return f"/update-profile/{user}/edit"

def quotation_notify_support(doc, method=None):
    # Get support or admin email from default outgoing Email Account only
    support_email = frappe.db.get_value("Email Account", {"default_outgoing": 1}, "email_id")
    if not support_email:
        return  # No default outgoing email account set
    # Collect all items from the Quotation
    items = doc.get("items", [])
    if not items:
        return
    item_lines = [f"- {item.item_name or item.item_code} (Qty: {item.qty})" for item in items]
    item_list = "\n".join(item_lines)
    subject = f"New Quotation #{doc.name} from {doc.customer_name or doc.customer or 'Unknown Customer'}"
    message = f"A new quotation has been created.\n\nItems:\n{item_list}\n\nTotal: {doc.grand_total} {doc.currency}"
    # Send the email
    frappe.sendmail(
        recipients=[support_email],
        subject=subject,
        message=message
    )

