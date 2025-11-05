__version__ = "0.0.1"

# highskills_erpnext/__init__.py

# This is the single most reliable way to force execution of startup code
# because the framework must import this file to load the app.
try:
    from .patches.pdf_sign_patch import apply_patch
    apply_patch()
except Exception:
    # Handle this gracefully if run outside of a Frappe environment (e.g., CI/local tests)
    pass