import frappe

@frappe.whitelist(allow_guest=True)
def sign_quotation_api(quotation_name, signature_image_base64, company_name, company_id, role_in_company, customer_name):
    try:
        quotation = frappe.get_doc("Quotation", quotation_name)

        # Update the quotation with the new signature and status
        #quotation.db_set("custom_signature", signature_image_base64.split("base64,")[1])
        quotation.db_set("custom_signature", signature_image_base64)
        # "Ordered" is the status for signed quotations
        quotation.db_set("status", "Ordered") 

        quotation.db_set("company", company_name) 

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

        customer.db_set("customer_details", role_in_company)
        customer.db_set("customer_name", customer_name)

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
