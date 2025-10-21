import frappe
from werkzeug.wrappers import Response
from datetime import datetime
from ai_intergration.ai_intergration.api import ai_chat, ai_comment, speech_to_text
import requests
import json
from io import BytesIO
import uuid
import os

# @frappe.whitelist()
# def send_message(
#     ig_id,
#     user_id,
#     type="text",
#     text=None,
# ):
#     wa_settings = frappe.get_doc("WhatsApp Settings", "WhatsApp Settings")

#     instance = frappe.get_all("WhatsApp Instance", filters={"phone_id": phone_id})
#     if not instance:
#         frappe.response["status"] == 404

#         return {"success": False, "message": "WhatsApp number id is not found"}
    
#     instance = frappe.get_doc("WhatsApp Instance", instance[0].name)
#     token = instance.get_password("token")
#     api_version = wa_settings.api_version

#     if type == "text":
#         response = send_whatsapp_response(
#             version=api_version,
#             phone_id=phone_id,
#             token=token,
#             to_number=client_number,
#             text=text,
#         )

@frappe.whitelist(allow_guest=True)
def instagram_webhook():
    if frappe.request.method == "GET":
        
        params = frappe.local.form_dict
        challenge = params.get("hub.challenge")
        verify_token = params.get("hub.verify_token")
        mode = params.get("hub.mode")

        ig_settings = frappe.get_doc("Instagram Settings", "Instagram Settings")
        api_version = ig_settings.api_version
        api_host = ig_settings.api_host
        
        if mode == "subscribe" and ig_settings.get_password("verify_token") == verify_token:
            return Response(str(challenge), mimetype='text/plain')
        
    else:
        ig_settings = frappe.get_doc("Instagram Settings", "Instagram Settings")
        api_version = ig_settings.api_version
        api_host = ig_settings.api_host

        try:
            raw_data = frappe.request.get_data(as_text=True)
            json_data = json.loads(raw_data)

            entry = json_data["entry"][0]
            ig_user_id = entry.get("id")
            changes = entry.get("changes", [])
            messages = entry.get("messaging", [])

            instance = get_instance(ig_user_id)
            if not instance:
                raise Exception("No Agent was found")
            
            token = instance.get_password("token")


            context = get_ai_context(instance.name)

            # client_subscription = get_sub(instance.business_account)
            # if client_subscription is None:
            #     error_message = str(instance.error_message).strip() if instance.error_message else ""
            #     if error_message:
            #         raise Exception(error_message)
            #     else:
            #         return
                
            # sub_id = client_subscription.name
            # enough_balance = has_enough_balance(sub_id)

            # if not enough_balance:
            #     return
            
            save_response_log(str(json_data), "4444444", "4444444444444", True)


            for msg in messages:
                timestamp = datetime.fromtimestamp(float(msg["timestamp"]) / 1000.0)
                message = msg.get("message")

                if not message:
                    return
                
                is_deleted = message.get("is_deleted")
                if is_deleted:
                    return
                
                is_echo = message.get("is_echo")
                if is_echo:
                    return
                
                text = message.get("text")
                attachments = msg.get("attachments")
                sender_id = msg["sender"]["id"]
                msg_body = ""
                image = None


                is_self_sent = sender_id == ig_user_id
                if is_self_sent:
                    return

                try:
                    
                    if text:
                        message_type = "text"
                        msg_body = text


                    elif attachments:
                        attachment = attachments[0]
                        message_type = attachment.get("type")
                        payload = attachment.get("payload")
                        media_url = payload.get("url")

                        if message_type == "audio":
                            stt_error = ig_settings.stt_error_message
                            stt_model = ig_settings.stt_model
                            
                            try:
                                if ig_settings.allow_stt == 0:
                                    raise Exception("1")
                                
                                file_resp = requests.get(media_url, headers={"Authorization": f"Bearer {token}"})
                                success = file_resp.status_code == 200

                                if not success:
                                    save_response_log(file_resp.text, "", "", True)

                                file_content = BytesIO(file_resp.content)
                                file_name = f"{uuid.uuid4()}.mp4"

                                if not file_content:
                                    raise Exception("2")
                                
                                if context.override_model == 0:
                                    raise Exception("3")
                                
                                stt_response = speech_to_text(
                                    stt_model,
                                    context.client_credentials,
                                    file_name,
                                    file_content,
                                )

                                if stt_response["success"]:
                                    msg_body = stt_response["text"]
                                    
                            except Exception as e:
                                ig_message = send_instagram_response(
                                    host=api_host,
                                    version=api_version,
                                    token=token,
                                    ig_id=ig_user_id,
                                    recipient_id=sender_id,
                                    text=f"{stt_error}: {e}",
                                )
                                return
                            
                        if message_type == "image":
                            pass
                        
                    chat = get_chat(
                        instance.name,
                        sender_id,
                        context,
                    )

                    model = get_model(context)

                    ai_response = ai_chat(
                        model=model,
                        chat_id=chat.name,
                        message_type="text",
                        new_message={
                            "role": "user",
                            "content": f"({sender_id}) says: {msg_body}",
                        },
                        plain_text=msg_body,
                        image=image,
                        to_account=ig_user_id,
                        stream=False,
                    )

                    if not ai_response:
                        error_msg = context.on_error if context.on_error else "عذرا لم أفهم، ممكن تكرر الطلب من فضلك."
                        raise Exception(error_msg)

                    is_live = ai_response.get("is_live")
                    response_text = ai_response.get("response")

                    if is_live:
                        frappe.publish_realtime(
                            f"instagram_chat_{chat.name}",
                            message={
                                "message": msg_body,
                                "sender": sender_id,
                                "role": "user",
                                "timestamp": datetime.now(),
                            }
                        )

                    elif response_text:
                        ig_message = send_instagram_response(
                            host=api_host,
                            version=api_version,
                            token=token,
                            ig_id=ig_user_id,
                            recipient_id=sender_id,
                            text=response_text,
                        )
                        if ig_message.status_code == 200:
                            pass
                            # spent = spend_balance(sub_id)
                            

                except Exception as e:
                    save_response_log(
                        f"ERROR: {e}",
                        sender_id,
                        ig_user_id,
                        True,
                    )


            for change in changes:

                field = change.get("field")
                value = change.get("value")
                from_user = value.get("from")
                user_id = from_user.get("id")
                username = from_user.get("username")
                image = None

                if ig_user_id == user_id:
                    return
                
                save_response_log(str(change), "------", "------")
                try:
                    if field == "comments":
                        msg_body = value.get("text", "")
                        comment_id = value.get("id")
                        media = value.get("media")
                        media_id = media.get("id")
                        media_type = media.get("media_product_type")

                        create_comment(
                            instance_id=instance.name,
                            user_id=user_id,
                            username=username,
                            media_id=media_id,
                            media_type=media_type,
                            comment_id=comment_id,
                            comment_text=msg_body,
                        )

                        model = get_model(context)

                        ai_response = ai_comment(
                            model=model,
                            context_id=context.name,
                            new_message={
                                "role": "user",
                                "content": f"({username}) says: {msg_body}",
                            },
                            to_account=ig_user_id,
                            stream=False,
                        )

                        if not ai_response:
                            error_msg = context.on_error if context.on_error else "عذرا لم أفهم، ممكن تكرر الطلب من فضلك."
                            raise Exception(error_msg)

                        response_text = ai_response.get("response")

                        if response_text:
                            ig_message = send_instagram_comment_response(
                                host=api_host,
                                version=api_version,
                                token=token,
                                comment_id=comment_id,
                                text=response_text,
                            )
                            if ig_message.status_code == 200:
                                pass
                                # spent = spend_balance(sub_id)

                except Exception as e:
                    save_response_log(
                        f"ERROR: {e}",
                        username,
                        ig_user_id,
                        True,
                    )


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
            filters={"user_id": ig_user_id, "enabled": 1, "live": 1}
        )
        if instances:
            instance = frappe.get_doc("Instagram Instance", instances[0].name)
            return instance

        return None
    except Exception as e:
        return None
    

def get_chat(instance_id, from_user, ai_context):
    chats = frappe.get_all(
        "Ai Chat",
        filters={
            "context": ai_context.name,
            "user_id": from_user,
        },
        fields=["name", "model"]
    )

    if chats:
        chat = chats[0]
    else:
        chat = frappe.new_doc("Ai Chat")
        chat.model = get_model(ai_context)

        chat.context = ai_context.name
        chat.instagram_instance = instance_id
        chat.channel_type = "Instagram"
        chat.user_id = from_user
        chat.save(ignore_permissions=True)

        frappe.db.commit()

    return chat


def get_model(ai_context):
    if ai_context.override_model == 1:
        model = ai_context.gpt_model
    elif ai_context.default_model == 1:
        model = "gpt-oss:120b"
    else:
        model = ai_context.llm
    return model


def has_enough_balance(sub_id):
    balance = frappe.db.get_value(
        "WhatsApp Subscription",
        sub_id,
        "balance"
    )
    if balance <= 0:
        return False
    return True


def spend_balance(sub_id):
    try:
        frappe.db.set_value(
            "Instagram Subscription",
            sub_id,
            "balance",
            (frappe.db.get_value(
                "Instagram Subscription",
                sub_id,
                "balance"
            ) - 1),
            update_modified=False,
        )
        return True
    except:
        return False
    

def get_sub(business_account):
    try:
        # today = datetime.now().date()
        # today_str = today.strftime("%Y-%m-%d")

        subs = frappe.get_all(
            "Instagram Subscription",
            filters={"business_account": business_account, "enabled": 1},
            fields=["name"],
            limit=1,
        )
        if subs:
            sub = frappe.get_doc("Instagram Subscription", subs[0].name)
            return sub
        
        return None
    except:
        return None


def get_ai_context(instance_id):
    ai_contexts = frappe.get_all(
        "AI Agent",
        filters={"instagram_instance": instance_id},
        fields=["name", "llm", "default_model", "gpt_model", "override_model", "client_credentials"],
        limit=1,
    )

    if not ai_contexts:
        return None

    ai_context = ai_contexts[0]
    return ai_context


def create_comment(
    instance_id,
    user_id,
    username,
    media_id,
    media_type,
    comment_id,
    comment_text,
):
    comment = frappe.new_doc("Instagram Comment")
    comment.instagram_instance = instance_id
    comment.user_id = user_id
    comment.username = username
    comment.media_id = media_id
    comment.media_product_type = media_type
    comment.comment_id = comment_id
    comment.text = comment_text
    comment.insert(ignore_permissions=True)
    frappe.db.commit()


def send_instagram_response(host, version, token, ig_id, recipient_id, text):
    try:
        url = f"https://{host}/{version}/{ig_id}/messages"
        body = {
            "recipient":{
                "id": recipient_id
            },
            "message":{
                "text": text
            }
        }
        headers = {
            "Authorization": f"Bearer {token}"
        }
        response = requests.post(url, json=body, headers=headers)

        return response
    except Exception as e:
        save_response_log(f"INSTAGRAM ERROR: {e}", "010101001", "01010101", True)



def send_instagram_comment_response(host, version, token, comment_id, text):
    url = f"https://{host}/{version}/{comment_id}/replies"
    body = {
        "message": text
    }
    headers = {
        "Authorization": f"Bearer {token}"
    }
    response = requests.post(url, json=body, headers=headers)

    return response


def save_response_log(body, sender, receiver, is_error=False):
    log = frappe.new_doc("Instagram Logs")
    log.sender = sender
    log.receiver = receiver
    log.method = "Received"
    log.timestamp = datetime.now()
    log.body = body
    log.is_error = is_error
    log.save(ignore_permissions=True)