__version__ = "0.0.1"

# Apply runtime monkeypatches (non-breaking if frappe is not importable)
try:  # pragma: no cover - runtime only when frappe is available
	from .patches import pdf_sign_patch  # noqa: F401
except Exception:
	# If frappe isn't present in this environment (tests, packaging), ignore
	pass
