if (!document.cookie.includes("preferred_language=he")) {
    document.cookie = "preferred_language=he; path=/";
    location.reload(); // reload to apply language
}
document.addEventListener('DOMContentLoaded', function() {
    if (document.body.classList.contains('product-page')) {
        const targetNode = document.body;
        const config = { childList: true, subtree: true };

        const callback = function(mutationsList, observer) {
            for (const mutation of mutationsList) {
                if (mutation.type === 'childList') {
                   

                    // Your existing button fix code
                    const buttons = document.querySelectorAll('.btn-list-view, .btn-grid-view');
                    if (buttons.length > 0) {
                        buttons.forEach(button => {
                            if (button.id) {
                                button.setAttribute('title', button.id);
                            }
                        });
                    }
                }
            }
        };

        const observer = new MutationObserver(callback);
        observer.observe(targetNode, config);
    }
});


document.addEventListener("DOMContentLoaded", function () {
    const body = document.body;

    const isLoggedIn = body.getAttribute("frappe-session-status") === "logged-in";
    const isCartPath = body.getAttribute("data-path") === "cart";
    const isProductPage = body.classList.contains("product-page");

    if (isLoggedIn && isCartPath && isProductPage) {
        const button = document.querySelector(".btn-request-for-quotation");
        if (button) {
            button.addEventListener("click", function () {
                alert("הצעת מחיר נשלחה למייל שלך לאישור");
            });
        }
    }

    // --- 2. New Logic: Replace "Add to Quote" Text ---
    // Select all buttons that have the class 'btn-add-to-cart-list'
    const buttonsToUpdate = document.querySelectorAll(".btn-add-to-cart-list");

    buttonsToUpdate.forEach(button => {
        let innerHTML = button.innerHTML;
        let newInnerHTML = innerHTML;

        // Check and replace "Add to Quote" with "הוספה לסל"
        if (innerHTML.includes("Add to Quote")) {
            newInnerHTML = newInnerHTML.replace("Add to Quote", "הוספה לסל");
        }

        // Check and replace "Go to Quote" with "מעבר לסל הקניות"
        if (innerHTML.includes("Go to Quote")) {
            newInnerHTML = newInnerHTML.replace("Go to Quote", "מעבר לסל הקניות");
        }
        
        // Apply the updated content only if a replacement was made
        if (newInnerHTML !== innerHTML) {
            button.innerHTML = newInnerHTML;
        }
    });
});



   // Function to set a cookie
function setCookie(name, value, days) {
    const d = new Date();
    d.setTime(d.getTime() + (days * 24 * 60 * 60 * 1000));
    const expires = "expires=" + d.toUTCString();
    document.cookie = name + "=" + value + ";" + expires + ";path=/";
}

// Corrected Function to get a cookie
function getCookie(name) {
    const cname = name + "=";
    const decodedCookie = decodeURIComponent(document.cookie);
    const ca = decodedCookie.split(';');
    for(let i = 0; i < ca.length; i++) {
        let c = ca[i];
        while (c.charAt(0) === ' ') {
            c = c.substring(1);
        }
        if (c.indexOf(cname) === 0) {
            // Trim whitespace from the value before returning
            return c.substring(cname.length, c.length).trim(); 
        }
    }
    return "";
}

document.addEventListener('DOMContentLoaded', () => {
    // Change this ID from cookieConsentOverlay to cookieConsentBanner
    const overlay = document.getElementById('cookieConsentOverlay');
    const banner = document.getElementById('cookieConsentBanner');
    const acceptBtn = document.getElementById('acceptCookiesBtn');
    const consentCookieName = "user_consent";
    const cookieCheckbox = document.getElementById('consentCookies');
    const termsCheckbox = document.getElementById('consentTerms');
    const checkboxes = [cookieCheckbox, termsCheckbox];

    const hasConsent = getCookie(consentCookieName); 

    if (hasConsent === "accepted") {
        banner.classList.add('hidden');
        overlay.classList.add('hidden');
    } else {
        banner.classList.remove('hidden');
        overlay.classList.remove('hidden');
    }

    function areAllChecked() {
        return checkboxes.every(checkbox => checkbox.checked);
    }

    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', () => {
            acceptBtn.disabled = !areAllChecked();
        });
    });

    acceptBtn.addEventListener('click', () => {
        if (areAllChecked()) {
            setCookie(consentCookieName, "accepted", 365);
            banner.classList.add('hidden');
            overlay.classList.add('hidden');
        }
    });
});