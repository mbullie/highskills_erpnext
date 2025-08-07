import frappe

def get_context(context):
    quotation_name = frappe.request.args.get('name')
    if not quotation_name:
        frappe.throw("Quotation name is missing.")

    try:
        quotation = frappe.get_doc("Quotation", quotation_name)
        # Try to get the customer email from common Quotation fields
        customer_email = getattr(quotation, "contact_email", None)
        # If not found, try to fetch from linked Customer
        if not customer_email and getattr(quotation, "customer", None):
            customer_doc = frappe.get_doc("Customer", quotation.customer)
            customer_email = getattr(customer_doc, "email_id", None)



        # Security Check: Redirect to login if not logged in
        if frappe.session.user == "Guest":
            frappe.local.response['type'] = 'redirect'
            frappe.local.response['location'] = f'/login?redirect_to=/sign_quotation?name={quotation_name}'
            # Do not set context, return early to avoid template error
            return
        # Only allow if the user is the customer
        if not customer_email or customer_email != frappe.session.user:
            # Do not set context, return early to avoid template error
            frappe.local.response['type'] = 'redirect'
            frappe.local.response['location'] = '/login'
            return

        context.quotation = quotation
        context.title = f"Sign Quotation: {quotation.name}"

    except frappe.DoesNotExistError:
        frappe.throw(f"Quotation {quotation_name} not found.")
    except frappe.PermissionError:
        frappe.throw("Permission Denied.")
