frappe.ui.form.on('Quotation', {
    after_save: function(frm) {
        frappe.call({
            method: 'highskills_erpnext.highskills_erpnext.api.quotation_notify_support',
            args: {
                doc: frm.doc
            },
            callback: function(r) {
                if (r.message && r.message.show_modal) {
                    frappe.msgprint({
                        title: __('Notification'),
                        message: r.message.message,
                        indicator: 'green'
                    });
                } else if (r.message && r.message.message) {
                    frappe.msgprint({
                        title: __('Notification'),
                        message: r.message.message,
                        indicator: 'red'
                    });
                }
            }
        });
    }
});
