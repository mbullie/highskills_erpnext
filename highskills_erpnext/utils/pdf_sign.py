import io
import os
from typing import Optional, Tuple

try:
    # pyhanko high-level signing API
    from pyhanko.sign import signers
    from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
    from pyhanko.sign import PdfSignatureMetadata
except Exception:  # pragma: no cover - runtime import guard
    signers = None
    IncrementalPdfFileWriter = None
    PdfSignatureMetadata = None


def sign_pdf_bytes(
    pdf_bytes: bytes,
    p12_path: Optional[str] = None,
    p12_password: Optional[str] = None,
    field_name: str = "Signature1",
    reason: str = "Document digitally signed",
    location: str = "",
    *,
    visible: bool = False,
    # page_number is 0-based. If None, PyHanko will place on first available page.
    page_number: Optional[int] = 0,
    # box in PDF user space units: (x1, y1, x2, y2)
    box: Optional[Tuple[float, float, float, float]] = None,
    # Path to an image to use as a visual stamp (PNG/JPEG).
    # NOTE: This is required when `visible=True` per app configuration policy.
    stamp_image_path: Optional[str] = None,
    stamp_text: Optional[str] = None,
) -> bytes:
    """
    Sign PDF bytes using PyHanko and a PKCS#12 (PFX) keyfile.

    Inputs:
    - pdf_bytes: original PDF as bytes
    - p12_path: path to .p12/.pfx file (if not provided, read from environment variable PDF_SIGN_PFX_PATH)
    - p12_password: password for the PFX (or from env PDF_SIGN_PFX_PASSWORD)
    - field_name, reason, location: signature metadata

    Returns:
    - signed PDF bytes

    Notes:
    - This helper uses PyHanko's high-level signing API. Ensure PyHanko is installed
      (it was added to pyproject.toml). Depending on PyHanko version some import
      names may differ; adjust imports if needed.
    - Keep the private key (PFX) protected and restrict filesystem access.
    """
    if signers is None:
        raise RuntimeError("pyhanko is not available; install pyhanko to use PDF signing")

    p12_path = p12_path or os.environ.get("PDF_SIGN_PFX_PATH")
    p12_password = p12_password or os.environ.get("PDF_SIGN_PFX_PASSWORD")

    if not p12_path:
        raise ValueError("Path to PFX/PKCS12 file must be provided via p12_path or PDF_SIGN_PFX_PATH env var")

    # Load signer from PKCS#12 file
    # Note: pyhanko expects password as bytes or None
    p12_pass_bytes = p12_password.encode("utf-8") if p12_password is not None else None
    signer = signers.SimpleSigner.load_pkcs12(p12_path, p12_pass_bytes)

    # Signature metadata
    meta = PdfSignatureMetadata(field_name=field_name, reason=reason, location=location)

    # Prepare for incremental signing
    w = IncrementalPdfFileWriter(io.BytesIO(pdf_bytes))
    out = io.BytesIO()

    # If visible signature requested, try to use PyHanko visible signature APIs.
    if visible:
        try:
            # Import optional visible-signing helpers
            from pyhanko.sign.fields import SigFieldSpec

            # Build signature field spec
            field_spec = SigFieldSpec(field_name, on_page=page_number, box=box) if box is not None else SigFieldSpec(field_name, on_page=page_number)

            # Require an image for visible signatures per site configuration policy.
            if not stamp_image_path:
                raise ValueError("Visible signatures require a stamp image path (stamp_image_path) as configured in site_config.json")

            if not os.path.exists(stamp_image_path):
                raise ValueError(f"Stamp image not found at path: {stamp_image_path}")

            # Use SimpleStampBuilder (common in pyhanko) to create an image-based appearance
            try:
                from pyhanko.stamp import SimpleStampBuilder

                stamp_builder = SimpleStampBuilder(stamp_image_path)
            except Exception:
                # If we cannot build an image-based stamp, surface a clear error to caller
                raise

            # Create PdfSigner with a new field spec and image appearance
            signer_kwargs = {"new_field_spec": field_spec, "stamp_style": stamp_builder}

            pdf_signer = signers.PdfSigner(meta, signer=signer, **signer_kwargs)
            pdf_signer.sign_pdf(w, output=out)
            return out.getvalue()
        except Exception:
            # If visible signing APIs are not available or fail, log and fall back
            # to invisible signing below.
            import logging

            logging.getLogger("pdf").warning("Visible PDF signing not available or failed; falling back to invisible signature", exc_info=True)

    # Invisible signing (or fallback)
    pdf_signer = signers.PdfSigner(meta, signer=signer)
    pdf_signer.sign_pdf(w, output=out)

    return out.getvalue()
