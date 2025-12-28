import frappe
from frappe.email.queue import flush

def trigger_immediate_flush(doc, method=None):
    """
    This wrapper catches the 'doc' and 'method' arguments 
    from the hook so the TypeError doesn't happen.
    """
    # Use enqueue to avoid slowing down the user's UI
    # and enqueue_after_commit to ensure the email is saved in the DB first
    frappe.enqueue(
        "frappe.email.queue.flush", 
        queue="short", 
        timeout=300, 
        enqueue_after_commit=True
    )
