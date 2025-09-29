// Copyright (c) 2025, Mosaab and contributors
// For license information, please see license.txt

frappe.ui.form.on('Instagram Instance', {
	// refresh: function(frm) {

	// }
	request_live_token: function(frm) {
		request_live_token(frm)
	}
});


function request_live_token(frm) {
	frappe.call({
    method: "instagram_integration.instagram.doctype.instagram_instance.instagram_instance.generate_live_token",
    args: {
        instance_id: frm.doc.name,
        now: frappe.datetime.now_datetime()
    },
    callback: function(r) {
        if (!r.exc) {
            console.log("New datetime:", r.message);
        }
    }
});
}