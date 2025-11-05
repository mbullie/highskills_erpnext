__version__ = "0.0.1"

# highskills_erpnext/__init__.py

# This is the single most reliable way to force execution of startup code
# because the framework must import this file to load the app.
try:
    from frappe import logger
    logger("pdf").error("Initializing highskills_erpnext - attempting to apply PDF patch")
    
    # First try to import and patch the PDF modules
    import frappe.utils.pdf
    import frappe.utils.print_format
    
    # Now import and apply our patch
    from .patches.pdf_sign_patch import apply_patch
    apply_patch()
    
    logger("pdf").error("Successfully initialized PDF patching")
except Exception as e:
    try:
        from frappe import logger
        logger("pdf").error(f"Failed to apply PDF patch during module init: {str(e)}", exc_info=True)
    except Exception:
        pass  # Can't even log
    # Handle this gracefully if run outside of a Frappe environment (e.g., CI/local tests)
    pass