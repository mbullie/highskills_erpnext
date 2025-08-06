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

        # Security Check: Ensure the user is the customer.
        if frappe.session.user == "Guest" or not customer_email or customer_email != frappe.session.user:
            frappe.throw("You are not authorized to sign this quotation.", frappe.PermissionError)

        context.quotation = quotation
        context.title = f"Sign Quotation: {quotation.name}"

    except frappe.DoesNotExistError:
        frappe.throw(f"Quotation {quotation_name} not found.")
    except frappe.PermissionError:
        frappe.throw("Permission Denied.")
