import frappe

def execute():
    # Add Company field if it doesn't exist
    if not frappe.db.exists("Custom Field", {"dt": "User", "fieldname": "company"}):
        frappe.get_doc({
            "doctype": "Custom Field",
            "dt": "User",
            "fieldname": "company",
            "label": "Company",
            "fieldtype": "Data",
            "insert_after": "last_name",
        }).insert(ignore_permissions=True)

