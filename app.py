
import re
import os
import openai
import datetime
import time
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk import WebClient
from slack_bolt import App, Ack, Respond
from slack_sdk.errors import SlackApiError

app = App(token=SLACK_BOT_TOKEN) 
client = WebClient(SLACK_BOT_TOKEN)
openai.api_key = OPENAI_API_KEY


commitment_infos=[]
users_list = {}
CompleteTs = '12094920394.394'
CommitId = 0

users = client.conversations_list(types="im")
for x in users["channels"]:
    if x["user"] == "USLACKBOT":
        continue
    tmp = {x["user"]:{
        "name":"<@"+x["user"]+">",
        "userId": x["user"],
        "channel": x["id"]
    }}
    response = client.users_info(user=x["user"])
    user = response["user"]
    user_name = user["real_name"]
    print(user_name)
    users_list.update(tmp)



def handle_openAi(prompt, maxtoken, tempearature):
    response = openai.Completion.create(
    engine="text-davinci-003",
    prompt=prompt,
    max_tokens=maxtoken,
    n=1,
    stop=None,
    temperature=tempearature).choices[0].text
    return response

def searchCommitId_info(C_id):
    iterator = len(commitment_infos) - 1
    while iterator > -1:
        if commitment_infos[iterator]['id'] == C_id:
            return iterator
        iterator = iterator - 1
    return -1

user_id_pattern = re.compile(r'<@(\w+)>')
def convert_user_ids_to_names(message_text):
    # Find all user IDs in the message text
    user_ids = user_id_pattern.findall(message_text)
    # If no user IDs are found, return the original message text
    if not user_ids:
        return message_text
    # Iterate through each user ID and retrieve the corresponding user's real name
    for user_id in user_ids:
        try:
            response = client.users_info(user=user_id)
            real_name = response['user']['real_name']
            # Replace the user ID in the message text with the user's real name
            message_text = message_text.replace(f'<@{user_id}>', real_name)
        except SlackApiError:
            pass
    return message_text


currentchannelState = False
passchannelState = False
public_channels = client.conversations_list()

for ch in public_channels['channels']:
    if ch['name'] == 'reliablyme-current_commitments':
        currentchannelState = True
    if ch['name'] == 'reliablyme-past_commitments':
        passchannelState = True
if currentchannelState == False:
    client.conversations_create(name="reliablyme-current_commitments")

if passchannelState == False:
    client.conversations_create(name="reliablyme-past_commitments")

for channelss in public_channels['channels']:
    if channelss['name'] == "reliablyme-current_commitments":
        currentchannel_Historyid = channelss['id']
    elif channelss['name'] == "reliablyme-past_commitments":
        passchannel_Historyid = channelss['id']


@app.event("message")
def handle_message_events(body, logger):

    CompleteDetected = True
    global current_msg, current_user, direct_channel
    if(body["event"].get('subtype') == None):
        current_msg = body["event"]["text"]
        current_user = body["event"]["user"]
    else:
        current_msg = body["event"]["message"]["text"]
        current_user = body["event"]["message"]["user"]
    if users_list[current_user].get('DM') != None and body['event']['channel_type'] == 'im':
        prompt = f"""I would like to inform someone who is I offered commitment that I have complete the commitment.
        So I said as like "{current_msg}".
        Did I say to inform that I have done the commitment, even implicit? """
        response = handle_openAi(prompt=prompt, tempearature=0.6, maxtoken=1024)
        CompleteDetected = False
        if "No" in response:
            client.chat_postMessage(channel = users_list[current_user]['DM'],
                                    text = f"<@{current_user}>'s message: {current_msg}")
            client.chat_postMessage(channel = current_user,
                                    text = f"Sent to <@{users_list[current_user]['DM']}>") 
        elif "Yes" in response:
            res = client.chat_postMessage(channel=users_list[current_user]["channel"],
                    text=f":mag_right: Would you like to inform someone that you have complete a commitment?",
                    blocks=[
                                {
                                    "type":"section",
                                    "text": {
                                        "type": "mrkdwn",
                                        "text": ":mag_right: Would you like to inform someone that you have complete a commitment? If yes please click here."
                                    },
                                },
                                {
                                    "type": "actions",
                                    "elements" : [
                                        {
                                            "type": "button",
                                            "text": {
                                                "type": "plain_text",
                                                "text": "Yes",
                                            },
                                            "action_id" : "Select_task"
                                        }
                                    ]
                                },
                                # {
                                #     "type": "section",
                                #     "text": {
                                #         "type": "mrkdwn",
                                #         "text": "Please select a user:"
                                #     },
                                #     "accessory": {
                                #         "type": "users_select",
                                #         "placeholder": {
                                #             "type": "plain_text",
                                #             "text": "Select a user"
                                #         },
                                #         "initial_user": current_user
                                #     }
                                # }

                            ]
                        )
            users_list[current_user]['SearchComplete'] = res['ts']
    if body['event']['channel_type'] == 'channel' and CompleteDetected == True:
        print("detection -->Step!!")
        prompt= f"""
        You need to identify offering, suggesting, inviting and requesting, even implicit.

        Here's a detailed explanation of each type of commitment and how to identify them: 
        
        1. Offering commitment: This is when you proactively offer to take on a task or responsibility. You might say, "I can handle that for you" or "I'll take care of that." You can identify this type of commitment by listening for phrases that indicate willingness to take action, such as "I'll do it" or "Let me handle that." 
        
        2. Suggesting commitment: This is when you propose an idea or solution that requires some level of commitment from others. You might say, "What if we tried this approach?" or "Have you considered doing it this way?" You can identify this type of commitment by listening for phrases that suggest ideas or solutions, such as "Maybe we could" or "What if we." 
        
        3. Inviting commitment: This is when you encourage or invite others to participate in a shared goal or vision. You might say, "We need your help with this" or "We would love for you to be a part of this team." You can identify this type of commitment by listening for phrases that suggest inclusion or participation, such as "Join us" or "Be a part of this." 
        
        4. Requesting commitment: This is when you ask someone to do something specific and commit to a certain task or responsibility. You might say, "Can you help me with this?" or "Could you take care of that for me?" You can identify this type of commitment by listening for phrases that ask for specific tasks or responsibilities, such as "Can you" or "Could you." 
        
        In general, it's important to pay attention to the language being used in a conversation to identify the type of commitment being offered, suggested, invited, or requested. Look for phrases that indicate willingness, ideas, inclusion, or specific tasks or responsibilities. It can also be helpful to clarify any commitments that are unclear to make sure everyone is on the same page.

        So I said "{current_msg}".
        If my answer is closer offering or suggesting commitment, please answer "OfferAA."
        Else if my answer is closer inviting or requesting commitment, please answer "RequestRR".
        Else please answer "Nothing."

        """
        response = handle_openAi(prompt=prompt, tempearature=0.5, maxtoken=1024)
        if "RequestRR" in response:
            print("step Request----")
            message_converted = convert_user_ids_to_names(current_msg)
            prompt = f"""You need to recognize my explain below to identify full requesting commitment, not offering commitment.
                A request for commitment is a clear and direct statement where someone is asking for help, support, or action from another person. It typically includes specific instructions and a timeframe for completion. Example of a request for commitment are: 
                
                - Can you please review this report and provide me with feedback by Tuesday at 3:00 PM? 
                - I need you to complete this project by Friday at noon. Can you please confirm that you can do so? 
                - Will you be able to attend the meeting next Wednesday at 10:00 AM? We really need your input. 
                
                On the other hand, an offer of commitment is a statement where someone is offering to provide help or support to another person. They may be making themselves available for assistance, but are not making a specific commitment to complete a task. Examples of an offer of commitment are: 
                
                - If you need any help with the project, just let me know. 
                - I'm happy to offer any support that you need to get the job done. 
                - If there's anything that I can do to help, please don't hesitate to ask. 
                
                In summary, a request for commitment is a specific and direct statement where someone is asking for help, support, or action from another person, while an offer of commitment is a statement where someone is offering to provide help or support to another person without making a specific commitment to complete a task.

                When requesting a commitment from someone, it is important to be clear and specific in your communication. One way to differentiate between a request and an offer is to focus on the outcome that you desire. If you are asking someone to commit to a specific action or result, then you are making a request. On the other hand, if you are offering something and letting the other party decide whether or not to accept it, then you are making an offer. Here are some tips to help you know if you have fully requested a commitment from someone, rather than making an offer: 
                
                1. Be clear about what you want 
                The first step in making a request is to be clear about what you want. Make sure that you are asking for something specific, rather than making a general statement. For example, instead of saying "Can you help me with this project?", say "Can you provide me with feedback on this project by the end of the week?" 
                
                2. Explain why you need it 
                When making a request, it is important to provide context about why you need the other person's help. This will help them understand the importance of the request and may encourage them to commit to it. For example, you might say "I really need your help on this project because it is a high-priority task for our department." 
                
                3. Set clear expectations 
                It is important to set clear expectations when making a request. This includes specifying the deadline and any other relevant details. For example, you might say "Can you provide me with feedback on this project by the end of the week? I need it in order to finalize the report for the executive team." 
                
                4. Ask for a commitment 
                To make sure that the other person fully understands the request, make sure to ask for a commitment. This can be as simple as asking "Can you commit to providing me with feedback on this project by the end of the week?" If they say yes, then you have successfully requested a commitment. 
                
                5. Follow up 
                Once the other person has committed to your request, it is important to follow up to ensure that they have completed the task. This will help you build trust with the other person and may make them more likely to commit to future requests. For example, you might say "I just wanted to follow up and see if you had any feedback on the project. I really appreciate your help on this." 
                
                In conclusion, making a request and getting a commitment requires clear communication, setting expectations and following up. By being clear about what you want, explaining why you need it, setting clear expectations, asking for a commitment, and following up, you can ensure that you have fully requested a commitment from someone, rather than making an offer.

                So I said to someone as like "{message_converted}".
                Please provide only a correct example that is requesting for full commitment. """
            res = handle_openAi(prompt=prompt, tempearature=0.5, maxtoken=1024)
            users_list[current_user]['Request_hint'] = res
            prompt = f"""You need to recognize my explain below to identify full requesting commitment, not offering commitment.
            A request for commitment is a clear and direct statement where someone is asking for help, support, or action from another person. It typically includes specific instructions and a timeframe for completion. Example of a request for commitment are: 
            
            - Can you please review this report and provide me with feedback by Tuesday at 3:00 PM? 
            - I need you to complete this project by Friday at noon. Can you please confirm that you can do so? 
            - Will you be able to attend the meeting next Wednesday at 10:00 AM? We really need your input. 
            
            On the other hand, an offer of commitment is a statement where someone is offering to provide help or support to another person. They may be making themselves available for assistance, but are not making a specific commitment to complete a task. Examples of an offer of commitment are: 
            
            - If you need any help with the project, just let me know. 
            - I'm happy to offer any support that you need to get the job done. 
            - If there's anything that I can do to help, please don't hesitate to ask. 
            
            In summary, a request for commitment is a specific and direct statement where someone is asking for help, support, or action from another person, while an offer of commitment is a statement where someone is offering to provide help or support to another person without making a specific commitment to complete a task.

            When requesting a commitment from someone, it is important to be clear and specific in your communication. One way to differentiate between a request and an offer is to focus on the outcome that you desire. If you are asking someone to commit to a specific action or result, then you are making a request. On the other hand, if you are offering something and letting the other party decide whether or not to accept it, then you are making an offer. Here are some tips to help you know if you have fully requested a commitment from someone, rather than making an offer: 
            
            1. Be clear about what you want 
            The first step in making a request is to be clear about what you want. Make sure that you are asking for something specific, rather than making a general statement. For example, instead of saying "Can you help me with this project?", say "Can you provide me with feedback on this project by the end of the week?" 
            
            2. Explain why you need it 
            When making a request, it is important to provide context about why you need the other person's help. This will help them understand the importance of the request and may encourage them to commit to it. For example, you might say "I really need your help on this project because it is a high-priority task for our department." 
            
            3. Set clear expectations 
            It is important to set clear expectations when making a request. This includes specifying the deadline and any other relevant details. For example, you might say "Can you provide me with feedback on this project by the end of the week? I need it in order to finalize the report for the executive team." 
            
            4. Ask for a commitment 
            To make sure that the other person fully understands the request, make sure to ask for a commitment. This can be as simple as asking "Can you commit to providing me with feedback on this project by the end of the week?" If they say yes, then you have successfully requested a commitment. 
            
            5. Follow up 
            Once the other person has committed to your request, it is important to follow up to ensure that they have completed the task. This will help you build trust with the other person and may make them more likely to commit to future requests. For example, you might say "I just wanted to follow up and see if you had any feedback on the project. I really appreciate your help on this." 
            
            In conclusion, making a request and getting a commitment requires clear communication, setting expectations and following up. By being clear about what you want, explaining why you need it, setting clear expectations, asking for a commitment, and following up, you can ensure that you have fully requested a commitment from someone, rather than making an offer.


            So I said "{current_msg}".
            In above conversation who is approver? Output only Slack ID.  If you don't get slack ID only above conversation, output "Someone". """

            Userdetected = handle_openAi(prompt=prompt, tempearature=0.5, maxtoken=1024)
            users_list[current_user]['Request_Userhint'] = Userdetected
            print("Request user hint detected --->>>>>>>>>", users_list[current_user]['Request_Userhint'])
            res = client.chat_postEphemeral(channel=body['event']['channel'],
                text=f":mag_right: {current_msg}",
                user= current_user,
                blocks=[
                            {
                                "type":"section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": f":mag_right: {current_msg}"
                                },
                            },                
                            {
                                "type": "actions",
                                "elements" : [
                                    {
                                        "type": "button",
                                        "text": {
                                            "type": "plain_text",
                                            "text": "Formalize Request",
                                        },
                                        "action_id" : "startRequest_commitment"
                                    },                                    
                                ]
                            }
                        ]
                    )
            users_list[current_user]['Search_requestTs'] = res['message_ts']
            users_list[current_user]['Request_Public_channel'] = body['event']['channel']
            print("block Offer Request Ts>>>>>>>>>>>>", res['message_ts'])
        elif "OfferAA." in response:
            print("Offer-->")
            message_converted = convert_user_ids_to_names(current_msg)
            prompt = f"""
                You need to recognize my guide below to identify full offering commitment, not requesting commitment. 
                An offer of commitment is a statement in which someone is offering to provide help, support or action to another person without being directly asked for it. It's important to recognize offers of commitment as they can be a valuable source of support and assistance. Here are a few key things to look out for when identifying full offers of commitment: 
                
                1. The language used: Look out for phrases like "I'm happy to," "I can help with," or "I'm available to." These sorts of phrases typically indicate an offer of support. 
                
                2. The tone of voice: People offering commitments often sound sincere and genuine. They may use a tone of voice that is friendly, helpful, and supportive. 
                
                3. The context: Consider the context of the conversation or situation. If someone offers to help or support you, consider whether their offer is relevant to the task or challenge you are facing. 
                
                4. The follow-through: A true offer of commitment is consistently followed up by action. If someone offers to assist you with something, they will usually follow through with their offer. 
                
                Keep in mind that offers of commitment can sometimes be less direct, such as when someone says "Let me know if there is anything I can do to help." These offers indicate that the person is willing to help, but you may need to follow up with them to clarify what support you need. 
                
                In summary, look out for language, tone of voice, context, and follow-through when identifying offers of commitment.

                When making an offer, it is important to take ownership of your actions and stand behind your commitments. Unlike a request, which requires the other party to take action, an offer is a proactive statement of what you are willing to do or provide. Here are some tips to help you know if you are offering full commitment rather than making a request: 
                1. Take ownership of your actions 
                When making an offer, it is important to take full ownership of your actions. This means that you are committing to taking action or providing a service, rather than relying on someone else to do it. For example, instead of saying "Can you help me with this project?", you might say "I am willing to take on this project and complete it by the end of the month." 
                2. Be specific 
                It is important to be specific when making an offer. This means providing details about what you are willing to offer and what the other party can expect. For example, you might say "I am willing to provide you with a detailed report on the project by the end of the week, including recommendations for next steps." 
                3. Be clear about your availability 
                When making an offer, it is important to be clear about your availability. This means specifying when you will be able to deliver the service or take the action. For example, you might say "I am available to work on this project every Monday and Wednesday for the next two weeks." 
                4. Set clear expectations 
                It is important to set clear expectations when making an offer. This includes specifying the deadline and any other relevant details. For example, you might say "I am willing to provide you with a detailed report on the project by the end of the week. In order to do this, I will need the necessary data from you by Wednesday." 
                5. Follow through on your commitment 
                When making an offer, it is important to follow through on your commitment. This means completing the action or providing the service that you promised. By following through, you build trust with the other party and demonstrate your commitment to your word.  
                
                For example, let's say that you are a graphic designer and a potential client has contacted you about designing a brochure. Rather than making a request for the client to provide you with more information, you might make an offer like this: "I am willing to design a brochure for your company that showcases your products and services. I can create a custom design that reflects your brand and deliver the final product to you within two weeks. I will also provide two rounds of revisions to ensure that you are completely satisfied with the design. Does this sound like a commitment you would be interested in?" In this scenario, you are taking ownership of the design process, providing specific details about what the client can expect, and setting clear expectations about the timeline and revisions. By making a full commitment, you are demonstrating your willingness to provide high-quality service and to stand behind your work. 
                
                In conclusion, making an offer requires taking ownership of your actions, being specific, being clear about your availability and expectations, and following through on your commitment. By making a full commitment, you can build trust with the other party and demonstrate your dedication to providing high-quality service.

                So I said to someone as like "{message_converted}".
                Please output only a correct example that is offering for full commitment.  """
            res = handle_openAi(prompt=prompt, tempearature=0.5, maxtoken=1024)
            users_list[current_user]['Offer_hint'] = res

            prompt = f"""
            You need to recognize my guide below to identify full offering commitment, not requesting commitment. 
            An offer of commitment is a statement in which someone is offering to provide help, support or action to another person without being directly asked for it. It's important to recognize offers of commitment as they can be a valuable source of support and assistance. Here are a few key things to look out for when identifying full offers of commitment: 
            
            1. The language used: Look out for phrases like "I'm happy to," "I can help with," or "I'm available to." These sorts of phrases typically indicate an offer of support. 
            
            2. The tone of voice: People offering commitments often sound sincere and genuine. They may use a tone of voice that is friendly, helpful, and supportive. 
            
            3. The context: Consider the context of the conversation or situation. If someone offers to help or support you, consider whether their offer is relevant to the task or challenge you are facing. 
            
            4. The follow-through: A true offer of commitment is consistently followed up by action. If someone offers to assist you with something, they will usually follow through with their offer. 
            
            Keep in mind that offers of commitment can sometimes be less direct, such as when someone says "Let me know if there is anything I can do to help." These offers indicate that the person is willing to help, but you may need to follow up with them to clarify what support you need. 
            
            In summary, look out for language, tone of voice, context, and follow-through when identifying offers of commitment.

            When making an offer, it is important to take ownership of your actions and stand behind your commitments. Unlike a request, which requires the other party to take action, an offer is a proactive statement of what you are willing to do or provide. Here are some tips to help you know if you are offering full commitment rather than making a request: 
            1. Take ownership of your actions 
            When making an offer, it is important to take full ownership of your actions. This means that you are committing to taking action or providing a service, rather than relying on someone else to do it. For example, instead of saying "Can you help me with this project?", you might say "I am willing to take on this project and complete it by the end of the month." 
            2. Be specific 
            It is important to be specific when making an offer. This means providing details about what you are willing to offer and what the other party can expect. For example, you might say "I am willing to provide you with a detailed report on the project by the end of the week, including recommendations for next steps." 
            3. Be clear about your availability 
            When making an offer, it is important to be clear about your availability. This means specifying when you will be able to deliver the service or take the action. For example, you might say "I am available to work on this project every Monday and Wednesday for the next two weeks." 
            4. Set clear expectations 
            It is important to set clear expectations when making an offer. This includes specifying the deadline and any other relevant details. For example, you might say "I am willing to provide you with a detailed report on the project by the end of the week. In order to do this, I will need the necessary data from you by Wednesday." 
            5. Follow through on your commitment 
            When making an offer, it is important to follow through on your commitment. This means completing the action or providing the service that you promised. By following through, you build trust with the other party and demonstrate your commitment to your word.  
            
            For example, let's say that you are a graphic designer and a potential client has contacted you about designing a brochure. Rather than making a request for the client to provide you with more information, you might make an offer like this: "I am willing to design a brochure for your company that showcases your products and services. I can create a custom design that reflects your brand and deliver the final product to you within two weeks. I will also provide two rounds of revisions to ensure that you are completely satisfied with the design. Does this sound like a commitment you would be interested in?" In this scenario, you are taking ownership of the design process, providing specific details about what the client can expect, and setting clear expectations about the timeline and revisions. By making a full commitment, you are demonstrating your willingness to provide high-quality service and to stand behind your work. 
            
            In conclusion, making an offer requires taking ownership of your actions, being specific, being clear about your availability and expectations, and following through on your commitment. By making a full commitment, you can build trust with the other party and demonstrate your dedication to providing high-quality service.
 
            So I said "{current_msg}"
            In above conversation who is am I offering to? Output only Slack ID. If you don't get slack ID, output "Someone". """
            Userdetected = handle_openAi(prompt=prompt, tempearature=0.5, maxtoken=1024)
            users_list[current_user]['Offer_Userhint'] = Userdetected
            print("Offer user detected->>>>>>>>>", users_list[current_user]['Offer_Userhint'])
            res = client.chat_postEphemeral(channel=body['event']['channel'],
                text=f":mag_right: {current_msg}",
                user= current_user,
                blocks=[
                            {
                                "type":"section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": f":mag_right: {current_msg}"
                                },
                            },
                            {
                                "type": "actions",
                                "elements" : [
                                    {
                                        "type": "button",
                                        "text": {
                                            "type": "plain_text",
                                            "text": "Formalize Offer",
                                        },
                                        "action_id" : "startOffer_commitment"
                                    },
                                ]
                            }
                        ]
                    )
            print("Ephemeral message-->>>")
            print(res)
            users_list[current_user]['Search_OfferTs'] = res['message_ts']
            users_list[current_user]['Offer_Public_channel'] = body['event']['channel']
            print("block Offer message Ts>>>>>>>>>>>>", res['message_ts'])
        elif "Nothing" in response:
            print("Nothing!-----")
            print(response)
@app.action({"action_id": "startOffer_commitment"})
def handle_startOffer_commitment(ack, body, logger):
    ack()
    print(body["trigger_id"])
    print("Action Ts>>>>>>>>>>>>>>")
    print(">>>>>>>>><<<<<<<<<<<<<<")
    print("usersOfferhint----->",users_list[body['user']['id']]['Offer_Userhint'])
    if "Someone" in users_list[body['user']['id']]['Offer_Userhint']:
        open_dialog = client.dialog_open(
            trigger_id= body["trigger_id"],
            dialog={
                "title": "Offering a commitment",
                "submit_label": "Submit",
                "callback_id": "offer_commit",
                "elements": [
                    {
                        "label": "Post this message on",
                        "name": "channel_notify",
                        "type": "select",
                        "data_source": "users",
                        "placeholder": "Select user"
                    },
                    {
                        "label": "commitment content",
                        "name": "commit_content",
                        "type": "textarea",
                        "hint": "Please provide offering commitment.",
                        "value": users_list[body['user']['id']]['Offer_hint']
                    }
                ]
            }
        )
    else :
        print("initial_user ->>>>", users_list[body['user']['id']]['Offer_Userhint'])
        open_dialog = client.dialog_open(
            trigger_id= body["trigger_id"],
            dialog={
                "title": "Offering a commitment",
                "submit_label": "Submit",
                "callback_id": "offer_commit",
                "state": "QQQQQQQQQQQQQQQQTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT",
                "elements": [
                    {
                        "label": "Post this message on",
                        "name": "channel_notify",
                        "type": "select",
                        "data_source": "users",
                        "value" : users_list[body['user']['id']]['Offer_Userhint']
                    },
                    {
                        "label": "commitment content",
                        "name": "commit_content",
                        "type": "textarea",
                        "hint": "Please provide offering commitment.",
                        "value": users_list[body['user']['id']]['Offer_hint']
                    }
                ]
            }
        )
@app.action({'type': 'dialog_submission', 'callback_id': 'offer_commit'})
def handle_submit_offer(ack, body, logger):
    ack()
    user = body['user']['id']
    print("submission>>>>>>>>>>>>> Data <<<<<<<<<<<<<<<<<<<<<<<<<")
    print(body['state'])
    print(">>>>>>>>>>>>>>>>submission<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
    # prompt = f"""
    # You need to recognize my guide below to identify full offering commitment, not requesting commitment. 
    # An offer of commitment is a statement in which someone is offering to provide help, support or action to another person without being directly asked for it. It's important to recognize offers of commitment as they can be a valuable source of support and assistance. Here are a few key things to look out for when identifying full offers of commitment: 
    
    # 1. The language used: Look out for phrases like "I'm happy to," "I can help with," or "I'm available to." These sorts of phrases typically indicate an offer of support. 
    
    # 2. The tone of voice: People offering commitments often sound sincere and genuine. They may use a tone of voice that is friendly, helpful, and supportive. 
    
    # 3. The context: Consider the context of the conversation or situation. If someone offers to help or support you, consider whether their offer is relevant to the task or challenge you are facing. 
    
    # 4. The follow-through: A true offer of commitment is consistently followed up by action. If someone offers to assist you with something, they will usually follow through with their offer. 
    
    # Keep in mind that offers of commitment can sometimes be less direct, such as when someone says "Let me know if there is anything I can do to help." These offers indicate that the person is willing to help, but you may need to follow up with them to clarify what support you need. 
    
    # In summary, look out for language, tone of voice, context, and follow-through when identifying offers of commitment.

    # When making an offer, it is important to take ownership of your actions and stand behind your commitments. Unlike a request, which requires the other party to take action, an offer is a proactive statement of what you are willing to do or provide. Here are some tips to help you know if you are offering full commitment rather than making a request: 
    # 1. Take ownership of your actions 
    # When making an offer, it is important to take full ownership of your actions. This means that you are committing to taking action or providing a service, rather than relying on someone else to do it. For example, instead of saying "Can you help me with this project?", you might say "I am willing to take on this project and complete it by the end of the month." 
    # 2. Be specific 
    # It is important to be specific when making an offer. This means providing details about what you are willing to offer and what the other party can expect. For example, you might say "I am willing to provide you with a detailed report on the project by the end of the week, including recommendations for next steps." 
    # 3. Be clear about your availability 
    # When making an offer, it is important to be clear about your availability. This means specifying when you will be able to deliver the service or take the action. For example, you might say "I am available to work on this project every Monday and Wednesday for the next two weeks." 
    # 4. Set clear expectations 
    # It is important to set clear expectations when making an offer. This includes specifying the deadline and any other relevant details. For example, you might say "I am willing to provide you with a detailed report on the project by the end of the week. In order to do this, I will need the necessary data from you by Wednesday." 
    # 5. Follow through on your commitment 
    # When making an offer, it is important to follow through on your commitment. This means completing the action or providing the service that you promised. By following through, you build trust with the other party and demonstrate your commitment to your word.  
    
    # For example, let's say that you are a graphic designer and a potential client has contacted you about designing a brochure. Rather than making a request for the client to provide you with more information, you might make an offer like this: "I am willing to design a brochure for your company that showcases your products and services. I can create a custom design that reflects your brand and deliver the final product to you within two weeks. I will also provide two rounds of revisions to ensure that you are completely satisfied with the design. Does this sound like a commitment you would be interested in?" In this scenario, you are taking ownership of the design process, providing specific details about what the client can expect, and setting clear expectations about the timeline and revisions. By making a full commitment, you are demonstrating your willingness to provide high-quality service and to stand behind your work. 
    
    # In conclusion, making an offer requires taking ownership of your actions, being specific, being clear about your availability and expectations, and following through on your commitment. By making a full commitment, you can build trust with the other party and demonstrate your dedication to providing high-quality service.
    # So I said to someone as like "{body['submission']['commit_content']}".
    # Am I offering fully commitment to someone? If your answer is "No" please explain to me kindly so that how should I tell. You answer include at least 150 words, and also should include correct examples that is requesting for full commitment too. """

    # response = handle_openAi(maxtoken=1024, tempearature=0.75, prompt=prompt)
    # if "Yes" in response:
    client.chat_postMessage(channel = user,
                    text="Successfully submited to " + '<@' + body['submission']['channel_notify'] + '>')
    global CommitId
    CommitId = CommitId + 1
    response = client.chat_postMessage(channel = body['submission']['channel_notify'],
                        text = f"Commitment is offered",
                        blocks=[
                                {
                                    "type":"section",
                                    "text": {
                                        "type": "mrkdwn",
                                        "text": '<@'+ user + '>'+" is offering to make this commitment to you: " + body['submission']['commit_content']
                                    },
                                },
                                {
                                    "type": "actions",
                                    "elements" : [
                                        {
                                            "type": "button",
                                            "text": {
                                                "type": "plain_text",
                                                "text": "Accept Offer",
                                            },
                                            "style": "primary",
                                            "action_id" : "Accept_commitment",
                                            "value": body['submission']['commit_content']
                                        },
                                        {
                                            "type": "button",
                                            "text": {
                                                "type": "plain_text",
                                                "text": "Decline Offer",
                                            },
                                            "style": "danger",
                                            "action_id" : "Decline_commitment",
                                            "value": body['submission']['commit_content']
                                        },
                                    ]
                                }
                            ],
                        metadata={
                            "event_type": "Offer_created",
                            "event_payload": {
                                "id": CommitId,
                                "title": "Offer Created"
                            }
                        }    
            )
    t_user = {
        "id" : CommitId,
        "OffertDate": response['ts'],
        "type": "Offer",
        "offer_man": user,
        "offer_content": body['submission']['commit_content'],
        "accepter_man" : body['submission']['channel_notify'],
        "status" : "pending"
    }
    users_list[user]['DM'] = body['submission']['channel_notify']
    commitment_infos.append(t_user)
    print("Epheral message update >>>>> channel", users_list[body['user']['id']]['Offer_Public_channel'])
    print("Epheral message update >>>>> timestamp", users_list[body['user']['id']]['Search_OfferTs'])
    # scheduled_time = time.time() + 5
    # response = client.chat_scheduleMessage(
    #     channel=users_list[body['user']['id']]['Offer_Public_channel'],
    #     text="This is an updated ephemeral message",
    #     post_at=scheduled_time
    # )   
    # delete_response = client.chat_deleteScheduledMessage(
    #     channel=users_list[body['user']['id']]['Offer_Public_channel'],
    #     scheduled_message_id=response["scheduled_message_id"]
    # )     
    response = client.chat_postEphemeral(channel = users_list[body['user']['id']]['Offer_Public_channel'],
                    user= user,
                    text=":grinning: Offered!",
                    blocks = [])        
    # else:
    #     client.chat_postMessage(channel = user,
    #                             text = f":wink:\n{response}")
@app.action({"action_id": "Decline_commitment"})
def handle_OfferDecline(ack, body, logger):
    ack()
    print("meta_Data>>>>>>>>>>>>>>>>>>>")
    print(body['message'])
    print(body['message']['metadata'])
    print("meta_Data Attachments <<<<<<<<<<<<<<<<<<")
    message_ts = body["message"]["ts"]
    channel_id = body["channel"]["id"]
    c_Id = body['message']['metadata']['event_payload']['id']
    C_index = searchCommitId_info(C_id=int(c_Id))
    response = client.chat_update(channel = channel_id,
                       ts=message_ts,
                       text="Decline! :face_with_rolling_eyes:",
                       blocks = [])
    response = client.chat_postMessage(channel = commitment_infos[C_index]['offer_man'],
                       text="Decline! :face_with_rolling_eyes:")
    response = client.chat_postMessage(channel = currentchannel_Historyid,
                       text=f"<@{commitment_infos[C_index]['offer_man']}> has made a declined commitment to <@{body['user']['id']}>: {commitment_infos[C_index]['offer_content']}")   
    commitment_infos[C_index]['status'] = "Decline"
    commitment_infos[C_index]['DeclineDate'] = response['ts']
@app.action({"action_id": "Accept_commitment"}) #Offer
def handle_acceptRequest(ack, body, logger):
    ack()
    print("meta_Data>>>>>>>>>>>>>>>>>>>")
    print(body['message'])
    print(body['message']['metadata'])
    print("meta_Data Attachments <<<<<<<<<<<<<<<<<<")
    message_ts = body["message"]["ts"]
    channel_id = body["channel"]["id"]
    accept_user = body['user']['id']
    c_Id = body['message']['metadata']['event_payload']['id']
    C_index = searchCommitId_info(C_id=int(c_Id))
    offerman = commitment_infos[C_index]['offer_man']
    offercontent = commitment_infos[C_index]['offer_content']
    response = client.chat_update(channel = channel_id,
                       ts=message_ts,
                       text=f"Accepted! <@{offerman}> :handshake: <@{accept_user}>",
                       blocks = [])
    client.pins_add(channel=channel_id, timestamp=message_ts)
    client.chat_postMessage(channel = offerman,
                       text=f"Accepted! <@{offerman}> :handshake: <@{accept_user}>")
    # client.chat_postMessage(channel = accept_user,
    #                    text=f"Accepted! <@{offerman}> :handshake: <@{accept_user}>")         
    response = client.chat_postMessage(channel = currentchannel_Historyid,
                       text=f"<@{offerman}> has made a commitment to <@{accept_user}>: {offercontent}")   
    commitment_infos[C_index]['status'] = "Accepted"
    commitment_infos[C_index]['AcceptDate'] = response['ts']
#######Request#######
@app.action({"action_id": "startRequest_commitment"})
def handle_RequestStart_commitment(ack, body, logger):
    ack()
    print("Request user hint -->>>>", users_list[current_user]['Request_Userhint'])
    if "Someone" in users_list[current_user]['Request_Userhint']:            
        open_dialog = client.dialog_open(
        trigger_id= body["trigger_id"],
        dialog={
            "title": "Requesting a commitment",
            "submit_label": "Submit",
            "callback_id": "Request_commit",
            "elements": [
                {
                    "label": "Post this message on",
                    "name": "request_channel_notify",
                    "type": "select",
                    "data_source": "users",
                },
                {
                    "label": "commitment content",
                    "name": "request_commit_content",
                    "type": "textarea",
                    "hint": "Please provide offering commitment.",
                    "value": users_list[body['user']['id']]['Request_hint']
                }
            ]
        }
    )
    else :
        open_dialog = client.dialog_open(
        trigger_id= body["trigger_id"],
        dialog={
            "title": "Requesting a commitment",
            "submit_label": "Submit",
            "callback_id": "Request_commit",
            "elements": [
                {
                    "label": "Post this message on",
                    "name": "request_channel_notify",
                    "type": "select",
                    "data_source": "users",
                    "value" : users_list[body['user']['id']]['Request_Userhint']
                },
                {
                    "label": "commitment content",
                    "name": "request_commit_content",
                    "type": "textarea",
                    "hint": "Please provide offering commitment.",
                    "value": users_list[body['user']['id']]['Request_hint']
                }
            ]
        }
    )            

@app.action({'type': 'dialog_submission', 'callback_id': 'Request_commit'})
def handle_RequestStart_Submission(ack, body, logger):
    ack()
    user = body['user']['id']
    # prompt = f"""You need to recognize my explain below to identify full requesting commitment, not offering commitment.
    # A request for commitment is a clear and direct statement where someone is asking for help, support, or action from another person. It typically includes specific instructions and a timeframe for completion. Example of a request for commitment are: 
    
    # - Can you please review this report and provide me with feedback by Tuesday at 3:00 PM? 
    # - I need you to complete this project by Friday at noon. Can you please confirm that you can do so? 
    # - Will you be able to attend the meeting next Wednesday at 10:00 AM? We really need your input. 
    
    # On the other hand, an offer of commitment is a statement where someone is offering to provide help or support to another person. They may be making themselves available for assistance, but are not making a specific commitment to complete a task. Examples of an offer of commitment are: 
    
    # - If you need any help with the project, just let me know. 
    # - I'm happy to offer any support that you need to get the job done. 
    # - If there's anything that I can do to help, please don't hesitate to ask. 
    
    # In summary, a request for commitment is a specific and direct statement where someone is asking for help, support, or action from another person, while an offer of commitment is a statement where someone is offering to provide help or support to another person without making a specific commitment to complete a task.

    # When requesting a commitment from someone, it is important to be clear and specific in your communication. One way to differentiate between a request and an offer is to focus on the outcome that you desire. If you are asking someone to commit to a specific action or result, then you are making a request. On the other hand, if you are offering something and letting the other party decide whether or not to accept it, then you are making an offer. Here are some tips to help you know if you have fully requested a commitment from someone, rather than making an offer: 
    
    # 1. Be clear about what you want 
    # The first step in making a request is to be clear about what you want. Make sure that you are asking for something specific, rather than making a general statement. For example, instead of saying "Can you help me with this project?", say "Can you provide me with feedback on this project by the end of the week?" 
    
    # 2. Explain why you need it 
    # When making a request, it is important to provide context about why you need the other person's help. This will help them understand the importance of the request and may encourage them to commit to it. For example, you might say "I really need your help on this project because it is a high-priority task for our department." 
    
    # 3. Set clear expectations 
    # It is important to set clear expectations when making a request. This includes specifying the deadline and any other relevant details. For example, you might say "Can you provide me with feedback on this project by the end of the week? I need it in order to finalize the report for the executive team." 
    
    # 4. Ask for a commitment 
    # To make sure that the other person fully understands the request, make sure to ask for a commitment. This can be as simple as asking "Can you commit to providing me with feedback on this project by the end of the week?" If they say yes, then you have successfully requested a commitment. 
    
    # 5. Follow up 
    # Once the other person has committed to your request, it is important to follow up to ensure that they have completed the task. This will help you build trust with the other person and may make them more likely to commit to future requests. For example, you might say "I just wanted to follow up and see if you had any feedback on the project. I really appreciate your help on this." 
    
    # In conclusion, making a request and getting a commitment requires clear communication, setting expectations and following up. By being clear about what you want, explaining why you need it, setting clear expectations, asking for a commitment, and following up, you can ensure that you have fully requested a commitment from someone, rather than making an offer.

    # So I said to someone as like "{body['submission']['request_commit_content']}".
    # Am I requesting fully commitment to someone? If your answer is "No" please explain to me kindly so that how should I tell. You answer include at least 150 words, and also should include correct examples that is requesting for full commitment too. """

    # response = handle_openAi(prompt=prompt, tempearature=0.5, maxtoken=1024)
    # if "Yes" in response:
    prompt = f"""Someone request commitment to me. I should to offer commitment on his reqeusting commitment.
        So you need to recognize my explain below to handle above.
        When someone requests a commitment from you, it's important to take the time to fully understand what is being asked and to think carefully before making a commitment. Here are some tips to help you offer full commitment to someone who has requested it from you: 
        1. Clarify the request 
        Before offering a commitment, it's important to clarify what is being asked. This means asking questions to ensure that you fully understand the scope of the request and what is expected of you. For example, if someone asks you to lead a project, you might ask for more information about the timeline, budget, and deliverables. 
        2. Consider your resources and limitations 
        When considering the request, it's important to think about your own resources and limitations. This means considering factors such as your time, expertise, and support network. For example, if someone asks you to volunteer at an event, you might need to consider whether you have the time and energy to commit to the event and whether you have the necessary skills to fulfill your responsibilities. 
        3. Provide a clear response 
        When offering a commitment, it's important to provide a clear response that outlines what you are willing to do and when you will do it. This means using specific language and setting clear expectations. For example, if someone asks you to help organize a fundraiser, you might say "I will commit to working with you on this fundraiser and will provide regular updates on my progress. I can commit to attending all meetings and will dedicate 10 hours per week to the project." 
        4. Follow through on your commitment 
        Once you have made a commitment, it is important to follow through on it. This means completing the tasks that you agreed to and staying in communication with the person who requested the commitment. For example, if you committed to helping organize a fundraiser, you might need to attend meetings, make phone calls, and help with event planning. By following through, you demonstrate your reliability and commitment to the project or task. 
        5. Communicate challenges or setbacks 
        If you encounter challenges or setbacks that prevent you from fulfilling your commitment, it's important to communicate this to the person who requested your commitment. This means being transparent about any issues that arise and working together to find a solution. For example, if you are unable to attend a meeting due to a family emergency, you might need to communicate this to the project lead and work together to reschedule the meeting. 
        In conclusion, offering full commitment requires careful consideration, clear communication, and follow-through. By taking the time to understand the request, considering your own resources and limitations, providing a clear response, and following through on your commitment, you can build strong relationships and demonstrate your reliability and dedication.

        Someone request to me as like "{body['submission']['request_commit_content']}" 
        Please output a correct example how I should offer commitment.
        """
    res = handle_openAi(prompt=prompt,tempearature=0.5, maxtoken=1024)
    users_list[body['submission']['request_channel_notify']]['OfferRequestHint'] = res
    client.chat_postMessage(channel = user,
                    text="Successfully submited to " + '<@' + body['submission']['request_channel_notify'] + '>')
    global CommitId
    CommitId = CommitId + 1
    response = client.chat_postMessage(channel = body['submission']['request_channel_notify'],
                        text = f"Commitment is offered",
                        blocks=[
                                {
                                    "type":"section",
                                    "text": {
                                        "type": "mrkdwn",
                                        "text": '<@'+ user + '>'+" is requesting to make this commitment to you: " + body['submission']['request_commit_content']
                                    },
                                },
                                {
                                    "type": "actions",
                                    "elements" : [
                                        {
                                            "type": "button",
                                            "text": {
                                                "type": "plain_text",
                                                "text": "Accept Request",
                                            },
                                            "style": "primary",
                                            "action_id" : "Accept_Request",
                                            "value": body['submission']['request_commit_content']
                                        },
                                        {
                                            "type": "button",
                                            "text": {
                                                "type": "plain_text",
                                                "text": "Decline Request",
                                            },
                                            "style": "danger",
                                            "action_id" : "Decline_Request",
                                            "value": body['submission']['request_commit_content']
                                        }

                                    ]
                                }
                            ],
                        metadata={
                            "event_type": "Request_created",
                            "event_payload": {
                                "id": CommitId,
                                "title": "Request Created"
                            }
                        }    

    )
    t_user = {
        "id": CommitId,
        "RequestDate": response['ts'],
        "type": "Request",
        "offer_man": body['submission']['request_channel_notify'],
        "request_content": body['submission']['request_commit_content'],
        "accepter_man" : user,
        "status" : "pending"
    }
    users_list[user]['DM'] = body['submission']['request_channel_notify']
    print(response['ts'], '<<<<<<<<<<<<<<<<<<<< id >>>>>>>>>>>>>>>>>')
    commitment_infos.append(t_user)
    # response = client.chat_update(channel = users_list[body['user']['id']]['Request_Public_channel'],
    #                 ts = users_list[body['user']['id']]['Search_requestTs'],
    #                 text=":grinning: Requested!",
    #                 blocks = [])

    response = client.chat_postEphemeral(channel = users_list[body['user']['id']]['Request_Public_channel'],
                    user= user,
                    text=":grinning: Requested!",
                    blocks = [])            

    # else:
    #     client.chat_postMessage(channel = user,
    #                             text = f":wink:\n{response}")

@app.action({"action_id": "Decline_Request"})
def handle_DeclineRequest(ack, body, logger):
    ack()
    user = body['user']['id']
    message_ts = body["message"]["ts"]
    channel_id = body["channel"]["id"]
    c_Id = body['message']['metadata']['event_payload']['id']
    print("Decline Request>>>>>>>>>>>>>>>>>>>>>>", c_Id)
    C_index = searchCommitId_info(C_id=int(c_Id))
    offerman = commitment_infos[C_index]['offer_man']
    requestcontent = commitment_infos[C_index]['request_content']
    response = client.chat_update(channel = channel_id,
                       ts=message_ts,
                       text="Decline! :face_with_rolling_eyes:",
                       blocks = [])
    client.chat_postMessage(channel = offerman,
                       text="Decline! :face_with_rolling_eyes:")
    # client.chat_postMessage(channel = user,
    #                    text="Decline! :face_with_rolling_eyes:")   
    response = client.chat_postMessage(channel = currentchannel_Historyid,
                       text=f"<@{offerman}> has made a declined request to <@{user}>: {requestcontent}")   
    commitment_infos[C_index]['status'] = "Request_Declined"
    commitment_infos[C_index]['RequestDeclineDate'] = response['ts']

@app.action({"action_id": "Accept_Request"})
def handle_Accpet_Request(ack, body, logger):
    ack()
    c_Id = body['message']['metadata']['event_payload']['id']
    print("Accept Request>>>>>>>>>>>>>>>>>>>>>> ", c_Id)
    open_dialog = client.dialog_open(
    trigger_id= body["trigger_id"],
    dialog={
        "title": "Offering a commitment",
        "submit_label": "Submit",
        "callback_id": "RequestOffer_commit",
        "state" : c_Id,
        "elements": [
            # {
            #     "label": "Post this message on",
            #     "name": "requestOffer_channel_notify",
            #     "type": "select",
            #     "data_source": "users",
            #     "placeholder": "Select user"
            # },
            {
                "label": "commitment content",
                "name": "requestoffer_commit_content",
                "type": "textarea",
                "hint": "Please provide offering commitment.",
                "value": users_list[body['user']['id']]['OfferRequestHint']
            }
        ]
        }
    )
@app.action({'type': 'dialog_submission', 'callback_id': 'RequestOffer_commit'})
def handle_RequestOffer(ack, body, logger):
    ack()
    user = body['user']['id']
    C_Id = int(body['state'])
    print("Accept Request state >>>>>>>>>>>>>>>>>>>>>>>>>>>>>> ", C_Id)
    # prompt = f"""Someone request commitment to me. I should to offer commitment on his reqeusting commitment.
    # So you need to recognize my explain below to handle above.
    # When someone requests a commitment from you, it's important to take the time to fully understand what is being asked and to think carefully before making a commitment. Here are some tips to help you offer full commitment to someone who has requested it from you: 
    # 1. Clarify the request 
    # Before offering a commitment, it's important to clarify what is being asked. This means asking questions to ensure that you fully understand the scope of the request and what is expected of you. For example, if someone asks you to lead a project, you might ask for more information about the timeline, budget, and deliverables. 
    # 2. Consider your resources and limitations 
    # When considering the request, it's important to think about your own resources and limitations. This means considering factors such as your time, expertise, and support network. For example, if someone asks you to volunteer at an event, you might need to consider whether you have the time and energy to commit to the event and whether you have the necessary skills to fulfill your responsibilities. 
    # 3. Provide a clear response 
    # When offering a commitment, it's important to provide a clear response that outlines what you are willing to do and when you will do it. This means using specific language and setting clear expectations. For example, if someone asks you to help organize a fundraiser, you might say "I will commit to working with you on this fundraiser and will provide regular updates on my progress. I can commit to attending all meetings and will dedicate 10 hours per week to the project." 
    # 4. Follow through on your commitment 
    # Once you have made a commitment, it is important to follow through on it. This means completing the tasks that you agreed to and staying in communication with the person who requested the commitment. For example, if you committed to helping organize a fundraiser, you might need to attend meetings, make phone calls, and help with event planning. By following through, you demonstrate your reliability and commitment to the project or task. 
    # 5. Communicate challenges or setbacks 
    # If you encounter challenges or setbacks that prevent you from fulfilling your commitment, it's important to communicate this to the person who requested your commitment. This means being transparent about any issues that arise and working together to find a solution. For example, if you are unable to attend a meeting due to a family emergency, you might need to communicate this to the project lead and work together to reschedule the meeting. 
    # In conclusion, offering full commitment requires careful consideration, clear communication, and follow-through. By taking the time to understand the request, considering your own resources and limitations, providing a clear response, and following through on your commitment, you can build strong relationships and demonstrate your reliability and dedication.

    # Someone request to me as like "{Offerman['request_content']}".
    # So I offered to him as like "{body['submission']['requestoffer_commit_content']}"
    # Did I fully offer commitment on his requesting commitment? If my answer is "No", please explain kindly how should I do. """
    # response = handle_openAi(tempearature=0.6, prompt=prompt, maxtoken=1024)
    # if "Yes" in response:
    print("Number type >>>>>>>>>>",C_Id, type(C_Id))
    print("data-------------->>>>>>", commitment_infos)
    index = searchCommitId_info(C_Id)
    print("index??????????", index)
    print("offer request commitment", commitment_infos[index])
    response = client.chat_update(channel = body['channel']['id'],
                ts=commitment_infos[index]['RequestDate'],
                text="Offered! :wave:",
                blocks = [])
    commitment_infos[index]['status'] = "offered"
    commitment_infos[index]['offer_content'] = body['submission']['requestoffer_commit_content']
    users_list[user]['DM'] = commitment_infos[index]['accepter_man']
    response = client.chat_postMessage(channel = commitment_infos[index]['accepter_man'],
                        text = f"Commitment is offered",
                        blocks=[
                                {
                                    "type":"section",
                                    "text": {
                                        "type": "mrkdwn",
                                        "text": '<@'+ user + '>'+"'s offering commitment: " + body['submission']['requestoffer_commit_content']
                                    },
                                },
                                {
                                    "type": "actions",
                                    "elements" : [
                                        {
                                            "type": "button",
                                            "text": {
                                                "type": "plain_text",
                                                "text": "Accept",
                                            },
                                            "style": "primary",
                                            "action_id" : "Accept_requestoffer",
                                        },
                                        {
                                            "type": "button",
                                            "text": {
                                                "type": "plain_text",
                                                "text": "Decline",
                                            },
                                            "style": "danger",
                                            "action_id" : "Decline_requestoffer",
                                        }
                                    ]
                                }
                            ],
                        metadata={
                            "event_type": "RequestOffer_created",
                            "event_payload": {
                                "id": body["state"],
                                "title": "Requesting Offer Created"
                            }
                        }    
    )
    client.chat_postMessage(channel = user,
            text="Successfully submited to " + '<@' + commitment_infos[index]['accepter_man'] + '>')
    response = client.chat_postMessage(channel = currentchannel_Historyid,
                       text=f"Accepted request of <@{commitment_infos[index]['accepter_man']}> by <@{user}>: {commitment_infos[index]['request_content']}")   
    commitment_infos[index]['status'] = "Request_Accepted"
    commitment_infos[index]['RequestAcceptDate'] = response['ts']

    # else:
    #     client.chat_postMessage(channel = user,
    #             text=f":wink: \n {response}")


@app.action({"action_id": "Decline_requestoffer"})
def handle_DeclineReqeustOffer(ack ,body, logger):
    ack()
    message_ts = body["message"]["ts"]
    channel_id = body["channel"]["id"]
    c_Id = body['message']['metadata']['event_payload']['id']
    C_index = searchCommitId_info(C_id=int(c_Id))
    offerman = commitment_infos[C_index]['offer_man']
    print("Decline RequestOffer >>>>>>>>>>>>>>>>>>>>>>>>>>>>>> ", c_Id)
    response = client.chat_update(channel = channel_id,
                       ts=message_ts,
                       text="Decline! :face_with_rolling_eyes:",
                       blocks = [])
    client.chat_postMessage(channel = offerman,
                       text="Decline! :face_with_rolling_eyes:")
    # client.chat_postMessage(channel = accept_user,
    #                    text="Decline! :face_with_rolling_eyes:")
    response = client.chat_postMessage(channel = currentchannel_Historyid,
                    text=f"Declined offer of <@{offerman}> by <@{user}>: {commitment_infos[C_index]['offer_content']}")   
    commitment_infos[C_index]['status'] = "RequestOffering_Decline"

@app.action({"action_id": "Accept_requestoffer"})
def handle_AcceptRequestOffer(ack, body, logger):
    ack()
    message_ts = body["message"]["ts"]
    channel_id = body["channel"]["id"]
    accept_user = body['user']['id']
    accept_user = body['user']['id']
    c_Id = body['message']['metadata']['event_payload']['id']
    print("handleReuqestAcceptOffer >>>>>>>>>", type(c_Id))
    C_index = searchCommitId_info(C_id=int(c_Id))
    offerman = commitment_infos[C_index]['offer_man']
    offercontent = commitment_infos[C_index]['offer_content']
    print("Accept RequestOffer >>>>>>>>>>>>>>>>>>>>>>>>>>>>>> ", c_Id)
    response = client.chat_update(channel = channel_id,
                       ts=message_ts,
                       text=f"Accepted! <@{offerman}> :handshake: <@{accept_user}>",
                       blocks = [])
    client.pins_add(channel=channel_id, timestamp=message_ts)
    client.chat_postMessage(channel = accept_user,
                       text=f"Accepted! <@{offerman}> :handshake: <@{accept_user}>")     
    client.chat_postMessage(channel = offerman,
                       text=f"Accepted! <@{offerman}> :handshake: <@{accept_user}>")     
    response = client.chat_postMessage(channel = currentchannel_Historyid,
                       text=f"<@{offerman}> has made a commitment to <@{accept_user}>: {offercontent}")   
    commitment_infos[C_index]['status'] = "Accepted"
    commitment_infos[C_index]['AcceptDate'] = response['ts']


@app.action({"action_id" : "Select_task"})
def Select_task(ack, body, logger):
    ack()
    user = body['user']['id']    
    tasks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Please select task*",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"Approver: <@{users_list[user]['DM']}>   |  Assignee: <@{user}>",
            },
        },        
    ]
    for tmp in commitment_infos:
        if tmp['offer_man'] == user and tmp["accepter_man"] == users_list[user]['DM'] and tmp['status'] == 'Accepted':
            content = {
                "type": "section",
                "text":{
                    "type": "mrkdwn",
                    "text": f"{tmp['offer_content']}",
                }
            }
            actions = {
                    "type" : "actions",
                    "elements" : [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Request",
                            },
                            "value": str(tmp["id"]),
                            "action_id" : "Commit_completed_Request"
                        }
                    ]            
                }
            tasks.append(content)
            tasks.append(actions)
    print("task------->>>>>")
    print(tasks)
    print("<<<<-----------task")
    res = client.chat_postMessage(
        channel = user,
        text="Please select task.",
        blocks = tasks,
    )
    print(">>>>>>>>>>>>>>>>>>>>>Select task data")
    print("<<<<<<<<<<<<<<<<<<<<<<< end data")

@app.action({"action_id": "Commit_completed_Request"})
def Commit_completed_Request(ack, body, logger):
    ack()
    # response = client.chat_update(channel = users_list[body['user']['id']]['channel'],
    #                    ts=users_list[body['user']['id']]['SearchComplete'],
    #                    text=":grinning:",
    #                    blocks = [])
    print(">>>>>>>>>>>>>>>>>action value", body["actions"][0]['value'])
    open_dialog = client.dialog_open(
    trigger_id= body["trigger_id"],
    dialog={
        "title":  "Commitment",
        "submit_label": "Submit",
        "callback_id": "RequestCompleted_commit",
        "state": body["actions"][0]['value'],
        "elements": [
            {
                "label": "commitment content",
                "name": "requestcomplete_commit_content",
                "type": "textarea",
                "hint": "Please provide detail content.",
            }
        ]
        }
    )
@app.action({'type': 'dialog_submission', 'callback_id': 'RequestCompleted_commit'})
def handle_RequestCompleted_commit(ack, body, logger):
    ack()
    C_id = int(body['state'])
    print(">>>>>>>>>>>>>>>>>  ", C_id)
    response = client.chat_postMessage(channel = users_list[body['user']['id']]['DM'],
                        text = f"Request to complete commitment",
                        blocks=[
                                {
                                    "type":"section",
                                    "text": {
                                        "type": "mrkdwn",
                                        "text": '<@'+ body['user']['id'] + '>'+ " is informing you that they has fulfilled their commitment and has provided this explanation: " 
                                            + body['submission']['requestcomplete_commit_content'] + ' Do you accept their completion request?'
                                    },
                                },
                                {
                                    "type": "actions",
                                    "elements" : [
                                        {
                                            "type": "button",
                                            "text": {
                                                "type": "plain_text",
                                                "text": "Accept",
                                            },
                                            "style": "primary",
                                            "action_id" : "Complete_Commitment",
                                        },
                                        {
                                            "type": "button",
                                            "text": {
                                                "type": "plain_text",
                                                "text": "Clarify expectations",
                                            },
                                            "style": "primary",
                                            "action_id" : "Clarify_expectations",                                            
                                        },                                                                                  
                                        {
                                            "type": "button",
                                            "text": {
                                                "type": "plain_text",
                                                "text": "Reject",
                                            },
                                            "style": "danger",
                                            "action_id" : "Reject_Commitment",
                                        },
                                    ]
                                }
                            ],
                        metadata={
                            "event_type": "Complete_created",
                            "event_payload": {
                                "id": C_id,
                                "title": "Complete Created"
                            }
                        }    

    )
    approver = users_list[body['user']['id']]['DM']
    users_list[approver]['CompleteTs'] = response['ts']
    global CompleteTs 
    CompleteTs = response['ts']
    print("Complete Ts Init>>>", CompleteTs)
    client.chat_postMessage(channel = body['user']['id'],
        text="Successfully submited to " + '<@' + users_list[body['user']['id']]['DM'] + '>')


@app.action({"action_id": "Complete_Commitment"})
def handle_Complete_Commitment(ack, body, logger):
    ack()
    c_Id = body['message']['metadata']['event_payload']['id']    
    print("complete dialogue Id ))0))))", c_Id)
    open_dialog = client.dialog_open(
    trigger_id= body["trigger_id"],
    dialog={
        "title":  "Commitment",
        "submit_label": "Submit",
        "callback_id": "Complete_select",
        "state" : c_Id,
        "elements": [
            {
                "label": "Post this message on",
                "name": "complete_channel_notify",
                "type": "select",              
                "options": [
                    {
                        "label": "Complete",
                        "value": "complete",
                    },
                    {
                        "label": "Incomplete",
                        "value": "incomplete"
                    },
                ]                
            },
            {
                "label": "Feedback",
                "name": "requestcomplete_commit_content",
                "type": "textarea",
                "hint": "Please provide detail content.",
                "optional" : "true"
            }
        ]
        }
    )

@app.action({"action_id": "Reject_Commitment"})
def handle_Reject_Commitment_Commitment(ack, body, logger):
    ack()
    channel_id = body["channel"]["id"]
    accept_user = body['user']['id']
    c_Id = body['message']['metadata']['event_payload']['id']
    C_index = searchCommitId_info(C_id=int(c_Id))
    C_info = commitment_infos[C_index]        
    response = client.chat_update(channel = channel_id,
                       ts=users_list[accept_user]['CompleteTs'],
                       text="Rejected! :x: ",
                       blocks = [])
    # client.pins_add(channel=channel_id, timestamp=message_ts)
    response = client.chat_postMessage(channel = currentchannel_Historyid,
                       text=f":x: Rejected by <@{accept_user}> to <@{C_info['offer_man']}>")   

    client.chat_postMessage(channel = C_info['offer_man'],
                       text="Rejected! :x: ")     


@app.action({'type': 'dialog_submission', 'callback_id': 'Complete_select'})
def handle_Complete_Selet(ack, body, logger):
    ack()
    print("-----------complete select---------")
    print(body)
    channel_id = body["channel"]["id"]
    accept_user = body['user']['id']
    C_id = int(body['state'])
    C_index = searchCommitId_info(C_id=C_id)
    C_info = commitment_infos[C_index]
    if 'complete' == body['submission']['complete_channel_notify']:
        response = client.chat_update(channel = channel_id,
                        ts=users_list[accept_user]['CompleteTs'],
                        text=f":heavy_check_mark:  Complete! <@{C_info['offer_man']}> :handshake: <@{accept_user}>",
                        blocks = [])
        client.pins_add(channel=channel_id, timestamp=users_list[accept_user]['CompleteTs'])
        client.chat_postMessage(channel = C_info['offer_man'],
                text=f":heavy_check_mark:  Complete! <@{C_info['offer_man']}> :handshake: <@{accept_user}>\n{body['submission']['requestcomplete_commit_content']}"
        )  
        # client.chat_postMessage(channel = accept_user,
        #         text=f":heavy_check_mark:  Complete! <@{Offerman['offer_man']}> :handshake: <@{accept_user}>"
        # )
        client.chat_postMessage(channel = passchannel_Historyid,
                text=f":heavy_check_mark:  Complete! <@{C_info['offer_man']}> :handshake: <@{accept_user}>"
        )
        commitment_infos[C_index]['feedback_content'] = body['submission']['requestcomplete_commit_content']
        commitment_infos[C_index]['status'] = "complete"
    elif 'incomplete' == body['submission']['complete_channel_notify']:            
        response = client.chat_update(channel = channel_id,
                        ts=users_list[accept_user]['CompleteTs'],
                        text=f":x:  Incomplete! <@{C_info['offer_man']}> :handshake: <@{accept_user}>",
                        blocks = [])
        client.pins_add(channel=channel_id, timestamp=users_list[accept_user]['CompleteTs'])
        client.chat_postMessage(channel = C_info['offer_man'],
                        text=f":x:  Incomplete! <@{C_info['offer_man']}> :handshake: <@{accept_user}>\n{body['submission']['requestcomplete_commit_content']}")  
        # client.chat_postMessage(channel = accept_user,
        #                 text=f":x:  Incomplete! <@{Offerman['offer_man']}> :handshake: <@{accept_user}>")
        client.chat_postMessage(channel = passchannel_Historyid,
            text=f":x:  Incomplete! <@{C_info['offer_man']}> :handshake: <@{accept_user}>")

        commitment_infos[C_index]['status'] = "incomplete"
        commitment_infos[C_index]['feedback_content'] = body['submission']['requestcomplete_commit_content']

@app.action({"action_id": "Clarify_expectations"})
def handle_Clarify_expectations(ack, body, logger):
    ack()
    c_Id = body['message']['metadata']['event_payload']['id']
    open_dialog = client.dialog_open(
    trigger_id= body["trigger_id"],
    dialog={
        "title":  "Clarify expectation",
        "submit_label": "Submit",
        "callback_id": "Clarify_dialogue",
        "state": c_Id,
        "elements": [
            {
                "label": "ClarifyExpectation_Feedback",
                "name": "ClarifyExpectation_content",
                "type": "textarea",
                "hint": "Please edit detail content.",
                "optional" : "true"
            }
        ]
        }
    )
@app.action({'type': 'dialog_submission', 'callback_id': 'Clarify_dialogue'})
def handle_ClarifySubmission(ack, body, logger):
    ack()
    C_id = body["state"]
    C_index = searchCommitId_info(C_id=int(C_id))
    C_info = commitment_infos[C_index]
    channel_id = body["channel"]["id"]
    accept_user = body['user']['id']    
    print("Clarify channel __ id", channel_id)
    print("Complete TimeStamp:", CompleteTs)
    response = client.chat_update(channel = channel_id,
                        ts=users_list[accept_user]['CompleteTs'],
                        text=f"Submited to <@{C_info['offer_man']}>",
                        blocks = [])    
    commitment_infos[C_index]['clarify_feedback'] = body['submission']['ClarifyExpectation_content']
    client.chat_postMessage(channel = C_info['offer_man'],
            text=f"<@{accept_user}>'s message : Clarify expectation\n{body['submission']['ClarifyExpectation_content']}"
    )
    client.chat_postMessage(channel = passchannel_Historyid,
    text=f"Clarify expectation\n <@{accept_user}>'s message : Clarify expectation\n{body['submission']['ClarifyExpectation_content']}")
  
    # client.chat_postMessage(channel = accept_user,
    #         text=f"Submited to <@{Offerman['offer_man']}>"
    # )


if __name__ == "__main__":
    SocketModeHandler(app, SLACK_APP_TOKEN).start()

