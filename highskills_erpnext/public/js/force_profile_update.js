frappe.ready(function() {
    if (window.location.pathname === "/update-password") {
        // Observe DOM changes for a success message
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.addedNodes.length) {
                    mutation.addedNodes.forEach(function(node) {
                        if (
                            node.nodeType === 1 &&
                            node.innerText &&
                            node.innerText.includes("Password updated")
                        ) {
                            // Redirect after success message appears
                            setTimeout(function() {
                                window.location.href = "/update-profile/" + frappe.session.user + "/edit";
                            }, 500);
                        }
                    });
                }
            });
        });

        observer.observe(document.body, { childList: true, subtree: true });
    }
});