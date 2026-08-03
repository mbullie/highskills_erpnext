import html

import frappe
from frappe.email.queue import flush

# Web Page routes whose content is genuinely per-user (resolves price list
# from the logged-in Customer's default_price_list) but render through
# content_type="Page Builder", which has no equivalent to the automatic
# no_cache detection frappe.website.doctype.web_page.web_page.WebPage.
# render_dynamic() applies to Jinja in "Rich Text"/"HTML" pages. Without this,
# Frappe's website page cache (frappe.website.utils.cache_html, keyed only by
# URL path - no user/session dimension at all) would serve whichever
# visitor's render happened to be cached first to every subsequent visitor,
# regardless of their own price list/country.
NO_CACHE_WEBSITE_PATHS = ("/shop",)


def disable_cache_for_dynamic_pages():
    """Registered via hooks.py `before_request`.

    frappe.website.utils.can_cache() treats frappe.local.no_cache as an
    unconditional bypass, checked before both the cache-read and cache-write
    steps - setting it here, before routing/rendering, disables caching for
    just these paths. Deliberately not context_script on the Web Page (would
    need Server Scripts enabled site-wide) or frappe.conf.disable_website_cache
    (would disable caching for every page on the site, not just this one).
    """
    if frappe.request and frappe.request.path in NO_CACHE_WEBSITE_PATHS:
        frappe.local.no_cache = True


def unescape_html_entities(text):
    """Registered via hooks.py `jinja.filters`, used only in print formats.

    api_signup.py HTML-escapes company/contact names before storing them
    (e.g. `"` -> `&quot;`) - reversing that here, for display only, keeps
    the stored value and every other rendering surface (Desk, emails,
    bank-transfer page) untouched.
    """
    return html.unescape(text) if text else text


def trigger_immediate_flush(doc, method=None):
    """
    This wrapper catches the 'doc' and 'method' arguments 
    from the hook so the TypeError doesn't happen.
    """
    # Use enqueue to avoid slowing down the user's UI
    # and enqueue_after_commit to ensure the email is saved in the DB first
    frappe.enqueue(
        "frappe.email.queue.flush", 
        queue="short", 
        timeout=300, 
        enqueue_after_commit=True
    )
