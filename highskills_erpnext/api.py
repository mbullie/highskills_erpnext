import frappe

@frappe.whitelist(allow_guest=True)
def sign_quotation_api(quotation_name, signature_image_base64, company_name, company_id, role_in_company, customer_name, contact_phone):
    try:
        quotation = frappe.get_doc("Quotation", quotation_name)
            # Update the quotation with the new signature
        quotation.db_set("custom_signature", signature_image_base64)
        frappe.db.commit()

        create_signed_quotation_document(quotation_name, signature_image_base64, company_name, company_id, role_in_company, customer_name, quotation.party_name, quotation.contact_person, contact_phone)

        # Trigger Frappe's notification system
        #quotation.notify_update()


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
        #customer = frappe.get_doc("Customer", quotation.party_name)

        #customer.db_set("customer_details", "Role in company: "+ role_in_company + ",Company name: " + company_name + ",Company ID: " + company_id+ ",customer_name : " + customer_name)
        #customer.db_set("customer_name", customer_name)

        #frappe.db.commit()

        return {"success": True, "redirect_url": "/quotations/" + quotation_name}

    except frappe.PermissionError:
        frappe.log_error(f"Permission denied for signing quotation {quotation_name}", "Sign Quotation API Error")
        frappe.db.rollback()
        return {"success": False, "error": "Permission Denied."}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Sign Quotation API Error")
        frappe.db.rollback()
        return {"success": False, "error": str(e)}


@frappe.whitelist(allow_guest=True)
def create_signed_quotation_document(quotation_name, signature_data, company_name, company_id, role, customer_name, party_name, contact_person,contact_phone):
    """
    Creates and saves a new document in the 'Signed Quotation' DocType 
    with the required field data, including the base64 signature image.

    :param quotation_id: The name/ID of the original Quotation.
    :param signature_data: The base64 string of the signature image.
    :param company_name: The name of the signing company.
    :param company_id: The ID/registration number of the company.
    :param role: The role of the person signing in the company.
    :param customer_name: The name of the customer/client.
    :param party_name: The name of the party_name on the quotation.
    :param contact_phone: The name of the contact_phone on the quotation.
    :return: The name of the newly created document.
    """
    try:
        # 1. Initialize the new document object
        contact = frappe.get_doc("Contact", contact_person)
        new_doc = frappe.get_doc({
            "doctype": "Signed Quotation",
            
            # 2. Set the field values
            "quotation_id": quotation_name,
            "contact": contact_person,
            "customer": party_name,
            "custom_signature": signature_data,
            "company_name": company_name,
            "company_id": company_id,
            "role_in_company": role,
            "customer_name": customer_name,
            "contact_phone": contact_phone,
            "contact_mail": contact.email_id,
            
            # Optional: Adding a timestamp for when the signature was captured
            "date_signed": frappe.utils.now_datetime()
        })

        # 3. Insert and save the document to the database
        new_doc.insert(ignore_permissions=True) # Use ignore_permissions if running from a privileged context
        new_doc.save()
        frappe.db.commit()

        frappe.msgprint(frappe._("Quotation has been signed."))
        
        return new_doc.name

    except Exception as e:
        frappe.log_error(
            title="Signed Quotation Creation Failed", 
            message=f"Error creating DocType for Quotation {quotation_name}: {str(e)}"
        )
        frappe.db.rollback() # Rollback the transaction on error
        frappe.throw(f"Error creating Signed Quotation: {e}")