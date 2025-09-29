import frappe
from werkzeug.wrappers import Response
from datetime import datetime
from ai_intergration.ai_intergration.api import ai_chat, speech_to_text
import requests
import json
from io import BytesIO
import uuid
import os

@frappe.whitelist(allow_guest=True)
def instagram_webhook():
    if frappe.request.method == "GET":
        
        params = frappe.local.form_dict
        challenge = params.get("hub.challenge")
        verify_token = params.get("hub.verify_token")
        mode = params.get("hub.mode")

        ig_settings = frappe.get_doc("Instagram Settings", "Instagram Settings")
        
        if mode == "subscribe" and ig_settings.get_password("verify_token") == verify_token:
            return Response(str(challenge), mimetype='text/plain')
        
    else:
        try:
            raw_data = frappe.request.get_data(as_text=True)
            json_data = json.loads(raw_data)

            entry = json_data["entry"][0]
            ig_user_id = entry.get("id")
            changes = entry.get("changes")

            instance = get_instance(ig_user_id)

            for change in changes:
                field = change.get("field")
                value = change.get("value")
                
                save_response_log(str(change), "------", "------")
                pass


        except Exception as e:
            # return None
            save_response_log(
                str(e),
                "--------",
                "--------",
                True,
            )
            return None
        

def get_instance(ig_user_id: str):
    try:
        instances = frappe.get_all(
            "Instagram Instance",
            filters={"instagram_user_id": ig_user_id, "enable": 1, "live": 1}
        )
        if instances:
            instance = frappe.get_doc("Instagram Instance", instances[0].name)
            return instance

        return None
    except Exception as e:
        return None


def save_response_log(body, sender, receiver, is_error=False):
    log = frappe.new_doc("Instagram Logs")
    log.sender = sender
    log.receiver = receiver
    log.method = "Received"
    log.timestamp = datetime.now()
    log.body = body
    log.is_error = is_error
    log.save(ignore_permissions=True)