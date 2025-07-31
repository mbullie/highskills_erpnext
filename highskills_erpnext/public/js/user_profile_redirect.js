// Ensure Frappe's framework is fully loaded before executing your script
frappe.ready(function() {
    // Check if we are currently on the 'edit-profile' web form page
    // frappe.web_form.name holds the name of the current web form.
    // Ensure 'edit-profile' is the exact name of the web form.
    if (frappe.web_form && frappe.web_form.name === 'edit-profile') {
        // Log to the browser console to confirm this script is loaded for the correct form
        console.log("Custom 'user_profile_redirect.js' loaded for 'edit-profile' web form.");

        // Attach an event listener to the 'after_save' event of the web form.
        // This event fires once the form data has been successfully sent to the server and saved.
        frappe.web_form.on('after_save', function() {
            // Log to the browser console to confirm the save event triggered
            console.log("Web Form 'after_save' event triggered. Initiating redirect to /home.");

            // Perform the browser-side redirection
            window.location.href = "/home";
        });
    } else {
        // Optional: Log if the script loads but not on the target web form, for debugging purposes
        // console.log("Custom 'user_profile_redirect.js' loaded, but not on 'edit-profile' web form.");
        // if (frappe.web_form) {
        //     console.log("Current Web Form Name:", frappe.web_form.name);
        // }
    }
});