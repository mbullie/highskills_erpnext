import frappe

@frappe.whitelist(allow_guest=True)
def sign_quotation_api(quotation_name, signature_image_base64, company_name, company_id, role_in_company, customer_name):
    try:
        quotation = frappe.get_doc("Quotation", quotation_name)
        # Update the quotation with the new signature and status
        # store only the base64 payload if a data URI was provided
        if signature_image_base64 and "base64," in signature_image_base64:
            signature_payload = signature_image_base64.split("base64,")[1]
        else:
            signature_payload = signature_image_base64

        quotation.custom_signature = signature_payload
        # "Ordered" is the status for signed quotations
        quotation.status = "Ordered"
        quotation.company = company_name

        # use save() so document events / notifications (Value Change) are triggered
        quotation.save(ignore_permissions=True)
        frappe.db.commit()

        # Update company 
        #if not frappe.db.exists("Company", company_name):
        #    company = frappe.get_doc(
		#		{
		#			"doctype": "Company",
		#			"company_name": company_name,
		#			"country": "Israel",
		#			"default_currency": "ILS",
		#		}
		#	)
        #    company = company.save()
        #
        #company = frappe.get_doc("Company", company_name)

        #company.db_set("registration_details", company_id)
        #quotation.db_set("company", company_name) 

        #frappe.db.commit()

        # Update company and personal information
        customer = frappe.get_doc("Customer", quotation.party_name)

        customer.customer_details = "Role in company: " + role_in_company + ",Company name: " + company_name + ",Company ID: " + company_id
        customer.customer_name = customer_name

        # save so any customer doc events also run
        customer.save(ignore_permissions=True)
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
