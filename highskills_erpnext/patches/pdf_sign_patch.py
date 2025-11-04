"""Monkeypatch frappe.utils.pdf.get_pdf to sign generated PDFs using PyHanko.

Behavior:
- If `options` contains `sign=True` OR site config `pdf_sign.enabled` is true,
  the produced PDF bytes (when no `output` writer is provided) will be passed
  to the application's `sign_pdf_bytes` helper.
- PFX path/password can be provided via options keys `sign_pfx_path` and
  `sign_pfx_password`, or via site config under `pdf_sign` (pfx_path, pfx_password),
  or via env vars (PDF_SIGN_PFX_PATH / PDF_SIGN_PFX_PASSWORD).

This module is intentionally defensive: failures in signing are logged but do
not break PDF generation.
"""
from __future__ import annotations

import os
import frappe
from frappe import logger
import inspect

try:
    # import our helper; if not available, we'll skip signing
    from highskills_erpnext.utils.pdf_sign import sign_pdf_bytes
except Exception:
    sign_pdf_bytes = None


def _should_sign(options: dict | None) -> bool:
    # Signing is controlled exclusively via site_config.json under `pdf_sign`.
    try:
        site_cfg = frappe.get_conf().get("pdf_sign", {}) or {}
    except Exception:
        site_cfg = {}

    return bool(site_cfg.get("enabled"))


def _sign_bytes_if_needed(pdf_bytes: bytes, options: dict | None) -> bytes:
    if sign_pdf_bytes is None:
        logger("pdf").error("PDF signing requested but signing helper is not available")
        return pdf_bytes

    # Read all signing configuration from site_config.json under `pdf_sign`.
    try:
        site_cfg = frappe.get_conf().get("pdf_sign", {}) or {}
    except Exception:
        site_cfg = {}

    pfx = site_cfg.get("pfx_path")
    pfx_pass = site_cfg.get("pfx_password")
    visible = bool(site_cfg.get("visible"))
    page_number = site_cfg.get("page_number", 0)
    box = site_cfg.get("box")
    stamp_image = site_cfg.get("stamp_image_path")
    stamp_text = site_cfg.get("stamp_text")

    if not pfx:
        logger("pdf").error("PDF signing requested but no PFX path configured in site_config.json under 'pdf_sign.pfx_path'")
        return pdf_bytes

    try:
        return sign_pdf_bytes(
            pdf_bytes,
            p12_path=pfx,
            p12_password=pfx_pass,
            visible=visible,
            page_number=page_number,
            box=tuple(box) if box else None,
            stamp_image_path=stamp_image,
            stamp_text=stamp_text,
        )
    except Exception:
        logger("pdf").error("PDF signing failed", exc_info=True)
        return pdf_bytes


def _validate_site_config_or_fail():
    """Validate that required pdf_sign settings exist when enabled.

    This function will raise RuntimeError with a clear message if required
    configuration fields are missing or point to non-existent files. It's
    intended to run at startup (app import) so failures are visible early.
    """
    try:
        site_cfg = frappe.get_conf().get("pdf_sign", {}) or {}
    except Exception:
        # If frappe.get_conf is not available, skip validation (not running in site)
        return

    if not site_cfg.get("enabled"):
        return

    missing = []

    pfx = site_cfg.get("pfx_path")
    if not pfx:
        missing.append("pdf_sign.pfx_path")
    else:
        if not os.path.exists(pfx):
            raise RuntimeError(f"PDF signing enabled but PFX file not found at '{pfx}'. Please set 'pdf_sign.pfx_path' in site_config.json and ensure the file is readable by the bench user.")

    visible = bool(site_cfg.get("visible"))
    if visible:
        stamp_image = site_cfg.get("stamp_image_path")
        if not stamp_image:
            missing.append("pdf_sign.stamp_image_path (required when pdf_sign.visible is true)")
        else:
            if not os.path.exists(stamp_image):
                raise RuntimeError(f"PDF signing visible stamp image not found at '{stamp_image}'. Please set 'pdf_sign.stamp_image_path' in site_config.json and ensure the file is readable by the bench user.")

    if missing:
        raise RuntimeError(
            "Missing PDF signing configuration in site_config.json: " + ", ".join(missing) + ".\nPlease add these keys under 'pdf_sign' or disable pdf signing by setting 'pdf_sign.enabled' to false."
        )


def apply_patch():
    """Patch frappe.utils.pdf. at runtime."""
    try:
        import frappe.utils.pdf as fpdf
    except Exception:
        # Not running inside a frappe environment
        logger("pdf").error("Failed to import frappe.utils.pdf - not in Frappe environment")
        return

    # Validate site_config and fail fast if required fields are missing.
    _validate_site_config_or_fail()

    # Avoid double-patching
    if getattr(fpdf.get_pdf, "_patched_for_signing", False):
        return

    original_get_pdf = fpdf.get_pdf

    def wrapped_get_pdf(html, options=None, output=None, *args, **kwargs):

        # Call original implementation
        res = original_get_pdf(html, options=options, output=output, *args, **kwargs)

        # If caller provided an output PdfWriter, original appended pages to it
        # and returned it — don't sign in that case.
        if output:
            return res

        # Only sign when we have bytes result and signing is requested
        if isinstance(res, (bytes, bytearray)) and _should_sign(options):
            return _sign_bytes_if_needed(bytes(res), options)

        return res

    wrapped_get_pdf._patched_for_signing = True
    fpdf.get_pdf = wrapped_get_pdf


    """Patch frappe.utils.print_format. at runtime."""
    try:
        import frappe.utils.print_format as fpdfpf
    except Exception:
        # Not running inside a frappe environment
        logger("pdf").error("Failed to import frappe.utils.print_format - not in Frappe environment")
        return

    # Validate site_config and fail fast if required fields are missing.
    _validate_site_config_or_fail()

    # Avoid double-patching
    if getattr(fpdfpf.download_pdf, "_patched_for_signing", False):
        return

    original_download_pdf = fpdfpf.download_pdf

    def wrapped_download_pdf(html, options=None, output=None, *args, **kwargs):

        # Call original implementation
        res = original_download_pdf(html, options=options, output=output, *args, **kwargs)

        # If caller provided an output PdfWriter, original appended pages to it
        # and returned it — don't sign in that case.
        if output:
            return res

        # Only sign when we have bytes result and signing is requested
        if isinstance(res, (bytes, bytearray)) and _should_sign(options):
            return _sign_bytes_if_needed(bytes(res), options)

        return res

    wrapped_download_pdf._patched_for_signing = True
    fpdfpf.download_pdf = wrapped_download_pdf


# Apply the patch eagerly
apply_patch()
