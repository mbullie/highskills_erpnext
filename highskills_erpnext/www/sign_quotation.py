import frappe

def get_context(context):

    quotation_name = frappe.request.args.get('name')
    # Debug: print session user to logs
    frappe.logger().info(f"[sign_quotation] frappe.session.user: {frappe.session.user}")
    # 1. If user not logged in, always redirect to login (with or without quotation name)
    if frappe.session.user == "Guest":
        redirect_url = "/sign_quotation"
        if quotation_name:
            redirect_url += f"?name={quotation_name}"
        frappe.local.response['type'] = 'redirect'
        frappe.local.response['location'] = f'/login?redirect_to={redirect_url}'
        return

    # 2. If no quotation name supplied (and user is logged in), show error message and return immediately
    if not quotation_name:
        context.error_message = "Quotation not found or does not exist."
        context.quotation = None
        return

    # 3. Try to get the quotation
    try:
        quotation = frappe.get_doc("Quotation", quotation_name)
    except frappe.DoesNotExistError:
        context.error_message = f"Quotation {quotation_name} not found."
        context.quotation = None
        return

    # 4. Get customer email
    customer_email = getattr(quotation, "contact_email", None)
    if not customer_email and getattr(quotation, "customer", None):
        customer_doc = frappe.get_doc("Customer", quotation.customer)
        customer_email = getattr(customer_doc, "email_id", None)

    # 5. If user is not the customer, show unauthorized message
    if not customer_email or customer_email != frappe.session.user:
        context.error_message = "You are not authorized to sign this quotation."
        context.quotation = None
        return

    # 6. If all checks pass, show signature fields
    context.quotation = quotation
    context.title = f"Sign Quotation: {quotation.name}"
