# Copyright (c) 2025, Mosaab and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from datetime import datetime, timedelta
import requests


class InstagramInstance(Document):
	pass

@frappe.whitelist(allow_guest=True)
def create_instance(code, now):
	user = frappe.get_doc("User", frappe.session.user)
	customer_id = user.customer_id if user.customer_id else "WOW Digital Information Technology"
	
	ig_settings = frappe.get_doc("Instagram Settings", "Instagram Settings")
	app_id = ig_settings.app_id
	app_secret = ig_settings.get_password("app_secret")
	redirect_uri = "https://connectly.wowdigital.sa/instagram-redirect/new"

	url = f"https://api.instagram.com/oauth/access_token"
	body = {
		"client_id": app_id,
		"client_secret": app_secret,
		"grant_type": "authorization_code",
		"redirect_uri": redirect_uri,
		"code": code
	}

	response = requests.post(url, data=body)

	success = response.status_code == 200
	if success:
		data = response.json()
		ig_user_id = data.get("user_id")
		access_token = data.get("access_token")

		dt = datetime.strptime(now, "%Y-%m-%d %H:%M:%S")
		expiry_date = dt + timedelta(hours=1)

		instance = get_instance(customer_id, ig_user_id, expiry_date, access_token)

		user = frappe.get_doc("User", frappe.session.user)
		has_role = frappe.db.exists(
			"Has Role",
			{"parenttype": "User", "parent": user.name, "role": "Instagram Manager"}
		)
		if not has_role:
			user.append("roles", {"role": "Instagram Manager"})
			user.save(ignore_permissions=True)

		try:
			return generate_live_token(instance.name, now)
			
		except Exception as e:
			return {"success": False, "error": str(e)}

	return {"success": False, "error": response.text}

		


@frappe.whitelist(methods=["POST"])
def generate_live_token(instance_id: str, now: str):
	ig_settings = frappe.get_doc("Instagram Settings", "Instagram Settings")
	api_host = ig_settings.api_host
	app_secret = ig_settings.get_password("app_secret")
	
	instance = frappe.get_doc("Instagram Instance", instance_id)
	token = instance.get_password("token")

	url = f"https://{api_host}/access_token"
	params = {
		"grant_type": "ig_exchange_token",
		"client_secret": app_secret,
		"access_token": token,
	}

	response = requests.get(url, params=params)
	success = response.status_code == 200

	if success:
		data = response.json()
		new_token = data.get("access_token")
		expires_in_seconds = int(data.get("expires_in"))

		dt = datetime.strptime(now, "%Y-%m-%d %H:%M:%S")
    
    	# new_dt = dt + timedelta(hours=1)
		expiry_date = dt + timedelta(seconds=expires_in_seconds)

		instance.expiry_date = expiry_date
		instance.token = new_token
		instance.live = 1
		instance.enabled = 1
		instance.save(ignore_permissions=True)
		frappe.db.commit()

	return {"success": success, "message": response.text, "instance_id": instance_id}



@frappe.whitelist(methods=["POST"])
def refresh_live_token(instance_id: str, now: str):
	ig_settings = frappe.get_doc("Instagram Settings", "Instagram Settings")
	api_host = ig_settings.api_host
	
	instance = frappe.get_doc("Instagram Instance", instance_id)
	token = instance.get_password("token")

	url = f"https://{api_host}/refresh_access_token"
	params = {
		"grant_type": "ig_refresh_token",
		"access_token": token,
	}

	response = requests.get(url, params=params)
	success = response.status_code == 200

	if success:
		data = response.json()
		new_token = data.get("access_token")
		expires_in_seconds = int(data.get("expires_in"))

		dt = datetime.strptime(now, "%Y-%m-%d %H:%M:%S")
    
    	# new_dt = dt + timedelta(hours=1)
		expiry_date = dt + timedelta(seconds=expires_in_seconds)

		instance.expiry_date = expiry_date
		instance.token = new_token
		instance.live = 1
		instance.enabled = 1
		instance.save(ignore_permissions=True)
		frappe.db.commit()

	return {"success": success, "message": response.text}


def get_instance(
		customer_id: str,
		ig_user_id: str=None,
		expiry_date: datetime=None,
		token: str=None,
	):
	user = frappe.session.user

	ig_instances = frappe.get_all(
		"Instagram Instance",
		filters={"user": user, "customer_id": customer_id},
		fields=["name", "instagram_user_id"],
		limit=1,
	)

	if ig_instances and ig_instances[0].instagram_user_id:
		instance = frappe.get_doc("Instagram Instance", ig_instances[0].name)

	else:
		instance = frappe.new_doc("Instagram Instance")
		instance.user = user
		instance.customer_id = customer_id
		instance.instagram_user_id = ig_user_id
		instance.expiry_date = expiry_date
		instance.token = token
		instance.insert(ignore_permissions=True)

		create_permission(user, instance.doctype, instance.name)
		
		frappe.db.commit()

	return instance

@frappe.whitelist(methods=["POST"])
def get_instagram_info(instance_id, sync_profile=False):
	try:
		ig_settings = frappe.get_doc("Instagram Settings", "Instagram Settings")
		api_host = ig_settings.api_host
		api_version = ig_settings.api_version

		instance = frappe.get_doc("Instagram Instance", instance_id)
		token = instance.get_password("token")

		fields = "user_id,username,name,account_type,profile_picture_url,followers_count,media_count"
		url = f"https://{api_host}/{api_version}/me?fields={fields}&access_token={token}"

		response = requests.get(url)

		success = response.status_code == 200
		if success:
			if sync_profile:
				info = response.json()
				instance.username = info.get("username")
				instance.user_id = info.get("user_id")
				instance.profile_picture = info.get("profile_picture_url")
				instance.followers_count = info.get("followers_count")
				instance.media_count = info.get("media_count")
				instance.save(ignore_permissions=True)

			return {"success": success, "info": info}
		
		return {"success": False, "error": response.text}
	
	except Exception as e:
		return {"success": False, "error": str(e)}
	

def create_permission(user, doctype, value):
	if user != "Administrator" and user != "Guest":
		user_perm = frappe.new_doc("User Permission")
		user_perm.user = user
		user_perm.allow = doctype
		user_perm.for_value = value
		user_perm.insert(ignore_permissions=True)

@frappe.whitelist(methods=["POST"])
def delete_user_data():
	pass