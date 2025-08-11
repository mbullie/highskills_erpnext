import frappe
from frappe.utils.file_manager import save_file

@frappe.whitelist(allow_guest=True)
def sign_quotation_api(quotation_name, signature_image_base64):
    try:
        quotation = frappe.get_doc("Quotation", quotation_name)

        # Save the Base64 signature as an image file
        #file_doc = save_file(
        #    fname=f"quotation_signature_{quotation_name}.png",
        #    content=signature_image_base64.split("base64,")[1],
        #    dt="Quotation",
        #    dn=quotation_name,
        #    is_private=0,  # Set to 0 for public access, change as needed
        #    decode=True
        #)

        # Update the quotation with the new signature and status
        #quotation.db_set("custom_signature", file_doc.file_url)
        quotation.db_set("custom_signature", signature_image_base64.split("base64,")[1])
        # "Ordered" is the status for signed quotations
        quotation.db_set("status", "Ordered") 

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
