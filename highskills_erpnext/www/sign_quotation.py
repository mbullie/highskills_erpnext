import frappe
import json
from urllib.parse import quote, urlencode


def get_context(context):
    quotation_name = frappe.request.args.get('name')

    # 1. If no quotation name supplied show error message and return immediately
    if not quotation_name:
        context.error_message = "Missing quotation."
        context.quotation = None
        return context

    # 2. If user not logged in, always redirect to login (with or without quotation name)
    if frappe.session.user == "Guest":
        # Redirect to login with the current URL as the redirect target
        frappe.redirect("/login?redirect-to=" + frappe.request.url)
        return 

        
    # 3. Try to get the quotation
    try:
        quotation = frappe.get_doc("Quotation", quotation_name)
        context.quotation = quotation
        context.title = f"Sign Quotation: {quotation.name}"
        #print(f"quotation.customer_name {quotation.customer_name} quotation.contact_person {quotation.contact_person} quotation.contact_display {quotation.contact_display} quotation.contact_email {quotation.contact_email}" , flush=True)
    except frappe.DoesNotExistError:
        context.error_message = f"Quotation {quotation_name} not found."
        context.quotation = None
        return context
    
    # 4. If user is not the customer, show unauthorized message
    # Use frappe.db.exists() to check for a user's role
    has_sales_manager_role = frappe.db.exists("Has Role", {
        "parent": frappe.session.user,
        "role": "Sales Manager"
    })
    if not quotation.contact_email or (quotation.contact_email != frappe.session.user and not has_sales_manager_role):
        context.error_message = "You are not authorized to sign this quotation."
        context.quotation = None
        return

    return context

    
def encode_params(params):
    """
    Encode a dict of params into a query string.

    Use `quote_via=urllib.parse.quote` so that whitespaces will be encoded as
    `%20` instead of as `+`. This is needed because oauthlib cannot handle `+`
    as a whitespace.
    """
    return urlencode(params, quote_via=quote)

