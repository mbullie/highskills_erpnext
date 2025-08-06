import frappe
from frappe.utils.file_manager import save_file

@frappe.whitelist(allow_guest=True)
def sign_quotation_api(quotation_name, signature_image_base64):
    try:
        quotation = frappe.get_doc("Quotation", quotation_name)

        # CRITICAL Security Check
        customer_email = getattr(quotation, "contact_email", None)
        if not customer_email and getattr(quotation, "customer", None):
            customer_doc = frappe.get_doc("Customer", quotation.customer)
            customer_email = getattr(customer_doc, "email_id", None)

        if frappe.session.user == "Guest" or not customer_email or customer_email != frappe.session.user:
            frappe.throw("You are not authorized to sign this quotation.", frappe.PermissionError)

        # Save the Base64 signature as an image file
        file_doc = save_file(
            fname=f"quotation_signature_{quotation_name}.png",
            content=signature_image_base64.split("base64,")[1],
            docname=quotation_name,
            folder="Home/Attachments",
            is_private=1,
            decode=True,
            is_whitelisted=True
        )

        # Update the quotation with the new signature and status
        quotation.db_set("custom_signature", file_doc.file_url)
        quotation.db_set("status", "Accepted") # Or your custom status field

        frappe.db.commit()
        return {"success": True, "redirect_url": "/quotations/" + quotation_name}

    except frappe.PermissionError:
        frappe.log_error(f"Permission denied for signing quotation {quotation_name}", "Sign Quotation API Error")
        frappe.db.rollback()
        return {"success": False, "error": "Permission Denied."}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Sign Quotation API Error")
        frappe.db.rollback()
        return {"success": False, "error": str(e)}
