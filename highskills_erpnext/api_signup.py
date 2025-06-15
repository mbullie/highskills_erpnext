import frappe
from frappe.core.doctype.user.user import sign_up

@frappe.whitelist(allow_guest=True)
def custom_sign_up(full_name, email, username, password, signup_company=None, signup_phone=None):
    # Create the user using Frappe's built-in sign_up
    user = sign_up(email, full_name, password)
    # Set username, company, and phone if provided
    doc = frappe.get_doc("User", user)
    if username:
        doc.username = username
    if signup_company:
        doc.company = signup_company
    if signup_phone:
        doc.phone = signup_phone
    doc.save(ignore_permissions=True)
    return {"message": "OK"}
