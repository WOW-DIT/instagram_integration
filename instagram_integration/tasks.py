import frappe
from instagram_integration.instagram.doctype.instagram_instance.instagram_instance import refresh_live_token

def refresh_instagram_instances():
    instances = frappe.get_all("Instagram Instance", filters={"auto_refresh": 1}, fields=["name", "expiry_date"])
    
    for instance in instances:
        refresh_live_token(instance.name, instance.expiry_date)