// Copyright (c) 2025, Mosaab and contributors
// For license information, please see license.txt

frappe.ui.form.on('Instagram Instance', {
	refresh: function(frm) {
        if(frm.doc.live && frm.doc.expiry_date > frappe.datetime.now_datetime()) {
            frm.add_custom_button("Sync Profile", () => {
                get_profile(frm, true);
            }).addClass("btn-primary");
        }

        if(frm.doc.live && frm.doc.expiry_date > frappe.datetime.now_datetime()
            && frm.doc.user_id && frm.doc.is_subscribed == 0
        ) {
            frm.add_custom_button("Subscribe", () => {
                subscribe(frm);
            }).addClass("btn-primary");
        }
	},
	request_live_token: function(frm) {
		request_live_token(frm)
	},
    refresh_token: function(frm) {
		refresh_token(frm)
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

function refresh_token(frm) {
	frappe.call({
        method: "instagram_integration.instagram.doctype.instagram_instance.instagram_instance.refresh_live_token",
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

function get_profile(frm, sync_profile=false) {
	frappe.call({
        method: "instagram_integration.instagram.doctype.instagram_instance.instagram_instance.get_instagram_info",
        args: {
            instance_id: frm.doc.name,
            sync_profile: sync_profile, 
        },
        callback: function(r) {            
            if (r.message.success) {
                console.log("New datetime:", r.message);

                const info = r.message.info;
                
                if(sync_profile) {
                    location.reload();
                }
            }
        }
    });
}

function subscribe(frm) {
	frappe.call({
        method: "instagram_integration.instagram.doctype.instagram_instance.instagram_instance.subscribe_ig_account",
        args: {
            instance_id: frm.doc.name,
        },
        callback: function(r) { 
            console.log(r.message)           
            if (r.message.success) {
                location.reload();
            }
        }
    });
}