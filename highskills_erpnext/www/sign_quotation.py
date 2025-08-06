import frappe

def get_context(context):
    quotation_name = frappe.request.args.get('name')
    if not quotation_name:
        frappe.throw("Quotation name is missing.")

    try:
        quotation = frappe.get_doc("Quotation", quotation_name)
        # Security Check: Ensure the user is the customer.
        # This is a basic check. For public links, use a secure hash instead of name.
        if frappe.session.user == "Guest" or quotation.customer_email != frappe.session.user:
            frappe.throw("You are not authorized to sign this quotation.", frappe.PermissionError)

        context.quotation = quotation
        context.title = f"Sign Quotation: {quotation.name}"

    except frappe.DoesNotExistError:
        frappe.throw(f"Quotation {quotation_name} not found.")
    except frappe.PermissionError:
        frappe.throw("Permission Denied.")
