# Copyright (c) 2025, Mosaab and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from datetime import datetime, timedelta
import requests


class InstagramInstance(Document):
	pass

@frappe.whitelist(methods=["POST"])
def create_instance(code, now):
	ig_settings = frappe.get_doc("Instagram Settings", "Instagram Settings")
	app_id = ig_settings.app_id
	app_secret = ig_settings.get_password("app_secret")
	redirect_uri = "https://whatsapp.wowdigital.sa/instagram-redirect/new"

	url = f"https://api.instagram.com/oauth/access_token"
	body = {
		"client_id": app_id,
		"client_secret": app_secret,
		"grant_type": "authorization_code",
		"redirect_uri": redirect_uri,
		"code": code
	}

	response = requests.post(url, data=body)
	if response.status_code == 200:
		data = response.json()
		ig_user_id = data.get("user_id")
		access_token = data.get("access_token")

		dt = datetime.strptime(now, "%Y-%m-%d %H:%M:%S")
		expiry_date = dt + timedelta(hours=1)

		instance = get_instance(ig_user_id, expiry_date, access_token)

		try:
			generate_live_token(instance.name, now)
		except:
			pass
		


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

	return {"success": success, "message": response.text}



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
		ig_user_id: str=None,
		expiry_date: datetime=None,
		token: str=None,
	):
	user = frappe.session.user

	ig_instances = frappe.get_list(
		"Instagram Instance",
		filters={"user": user},
		fields=["name", "instagram_user_id"],
	)

	if ig_instances and ig_instances[0].instagram_user_id:
		instance = frappe.get_list("Instagram Instance", ig_instances[0].name)

	else:
		instance = frappe.new_doc("Instagram Instance")
		instance.user = frappe.session.user
		instance.instagram_user_id = ig_user_id
		instance.expiry_date = expiry_date
		instance.token = token
		instance.insert(ignore_permissions=True)
		frappe.db.commit()

	return instance
