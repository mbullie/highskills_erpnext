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
    # Fetch all customer details from Customer DocType (one fetch)
    customer_doc = frappe.get_doc("Customer", doc.customer) if doc.customer else None
    customer_full_name = customer_doc.customer_name if customer_doc else doc.customer_name or doc.customer or "-"
    customer_group = customer_doc.customer_group if customer_doc else "-"
    territory = customer_doc.territory if customer_doc else "-"
    customer_type = customer_doc.customer_type if customer_doc else "-"
    tax_id = getattr(customer_doc, 'tax_id', "-") if customer_doc else "-"
    # Fetch primary Contact and Address in one query each
    contact = None
    address = None
    if customer_doc:
        links = frappe.get_all("Dynamic Link", filters={"link_doctype": "Customer", "link_name": customer_doc.name}, fields=["parent", "parenttype"])
        for link in links:
            if link["parenttype"] == "Contact" and not contact:
                contact = frappe.get_doc("Contact", link["parent"])
            elif link["parenttype"] == "Address" and not address:
                address = frappe.get_doc("Address", link["parent"])
            if contact and address:
                break
    # Get customer email and phone
    customer_email = doc.contact_email or (contact.email_id if contact else "-")
    customer_phone = doc.contact_mobile or (contact.phone if contact else "-")
    # Get customer address
    customer_address = doc.customer_address or (address.display if address and hasattr(address, 'display') else (address.address_line1 if address else "-"))
    # Collect all customer details
    customer_details = f"""
    <b>Customer Name:</b> {customer_full_name}<br>
    <b>Customer Group:</b> {customer_group}<br>
    <b>Territory:</b> {territory}<br>
    <b>Customer Type:</b> {customer_type}<br>
    <b>Tax ID:</b> {tax_id}<br>
    <b>Email:</b> {customer_email}<br>
    <b>Phone:</b> {customer_phone}<br>
    <b>Address:</b> {customer_address}<br>
    """
    # Collect all items from the Quotation
    items = doc.get("items", [])
    if not items:
        return
    item_rows = "".join([
        f"<tr>"
        f"<td>{item.item_code}</td>"
        f"<td>{item.item_name}</td>"
        f"<td>{item.qty}</td>"
        f"<td>{item.uom}</td>"
        f"<td>{frappe.utils.fmt_money(item.rate, currency=doc.currency)}</td>"
        f"<td>{frappe.utils.fmt_money(item.amount, currency=doc.currency)}</td>"
        f"</tr>"
        for item in items
    ])
    items_table = f"""
    <table border='1' cellpadding='5' cellspacing='0' style='border-collapse:collapse;'>
        <thead>
            <tr>
                <th>Item Code</th>
                <th>Item Name</th>
                <th>Qty</th>
                <th>UOM</th>
                <th>Rate</th>
                <th>Amount</th>
            </tr>
        </thead>
        <tbody>
            {item_rows}
        </tbody>
    </table>
    """
    # Taxes
    taxes = doc.get("taxes", [])
    tax_rows = "".join([
        f"<tr><td>{tax.account_head}</td><td>{tax.description or ''}</td><td>{frappe.utils.fmt_money(tax.tax_amount, currency=doc.currency)}</td></tr>"
        for tax in taxes
    ])
    taxes_table = f"""
    <table border='1' cellpadding='5' cellspacing='0' style='border-collapse:collapse;margin-top:10px;'>
        <thead>
            <tr><th>Tax Account</th><th>Description</th><th>Amount</th></tr>
        </thead>
        <tbody>
            {tax_rows}
        </tbody>
    </table>
    """ if taxes else "<i>No taxes applied.</i>"
    # Quotation time
    quotation_time = frappe.utils.format_datetime(doc.creation, "yyyy-MM-dd HH:mm:ss")
    # Get roles of the user who created the Quotation
    user_roles = []
    username = getattr(doc, 'owner', '-')
    if username:
        user_roles = frappe.get_roles(username)
    roles_str = ', '.join(user_roles) if user_roles else '-'
    user_roles_details = f"<b>Username:</b> {username}<br><b>User Roles:</b> {roles_str}<br>"
    # Email body
    message = f"""
    <h2>New Quotation Created</h2>
    <b>Quotation No:</b> {doc.name}<br>
    <b>Date & Time:</b> {quotation_time}<br>
    {customer_details}
    {user_roles_details}
    <h3>Items</h3>
    {items_table}
    <h3>Taxes</h3>
    {taxes_table}
    <h3>Total</h3>
    <b>Grand Total:</b> {frappe.utils.fmt_money(doc.grand_total, currency=doc.currency)}<br>
    <b>In Words:</b> {doc.in_words or ''}<br>
    """
    subject = f"New Quotation #{doc.name} from {doc.customer_name or doc.customer or 'Unknown Customer'}"
    frappe.sendmail(
        recipients=[support_email],
        subject=subject,
        message=message,
        delayed=False,
        as_markdown=False
    )

