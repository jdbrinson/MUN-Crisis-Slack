# -*- coding: utf-8 -*-
"""
A routing layer for the onboarding bot tutorial built using
[Slack's Events API](https://api.slack.com/events-api) in Python
"""
import json
import bot
from flask import Flask, request, make_response, render_template
from threading import Thread 

pyBot = bot.Bot()
slack = pyBot.client

app = Flask(__name__)


def _event_handler(event_type, slack_event):
    """
    A helper function that routes events from Slack to our Bot
    by event type and subtype.

    Parameters
    ----------
    event_type : str
        type of event recieved from Slack
    slack_event : dict
        JSON response from a Slack reaction event

    Returns
    ----------
    obj
        Response object with 200 - ok or 500 - No Event Handler error

    """
    team_id = slack_event["team_id"]
    # ================ Team Join Events =============== #
    # When the user first joins a team, the type of event will be team_join
    if event_type == "team_join":
        user_id = slack_event["event"]["user"]["id"]
        # Send the onboarding message
        pyBot.onboarding_message(team_id, user_id)
        return make_response("Welcome Message Sent", 200,)

    # ============== Share Message Events ============= #
    # If the user has shared the onboarding message, the event type will be
    # message. We'll also need to check that this is a message that has been
    # shared by looking into the attachments for "is_shared".
    elif event_type == "message" and slack_event["event"].get("attachments"):
        user_id = slack_event["event"].get("user")
        if slack_event["event"]["attachments"][0].get("is_share"):
            # Update the onboarding message and check off "Share this Message"
            pyBot.update_share(team_id, user_id)
            return make_response("Welcome message updates with shared message",
                                 200,)

    # ============= Reaction Added Events ============= #
    # If the user has added an emoji reaction to the onboarding message
    elif event_type == "reaction_added":
        user_id = slack_event["event"]["user"]
        # Update the onboarding message
        pyBot.update_emoji(team_id, user_id)
        return make_response("Welcome message updates with reactji", 200,)

    # =============== Pin Added Events ================ #
    # If the user has added an emoji reaction to the onboarding message
    elif event_type == "pin_added":
        user_id = slack_event["event"]["user"]
        # Update the onboarding message
        pyBot.update_pin(team_id, user_id)
        return make_response("Welcome message updates with pin", 200,)
    # ================ potty mouth detector ============ #
    # scans deleted messages for  
    elif event_type == "message.im":
        if "message_deleted" in slack_event["event"]["subtype"]:
            message = slack_event["event"]["text"]
            message_set = set(message.split(' ')) 
            if not message_set.isdisjoint(bad_words):
                bad_message = {}
                bad_message["user"] = slack_event["event"]["user"]
                bad_message["message"] = message
                bad_message["channel"] = slack_event["channel"]
                bad_message["time"] = slack_event["ts"]
                #alert committee staff
                #alert Secretariat
                #alert advisor(s)
                return make_response("bad message", 200,)
        return make_response("good message", 200,)

    # ============= Event Type Not Found! ============= #
    # If the event_type does not have a handler
    message = "You have not added an event handler for the %s" % event_type
    # Return a helpful error message
    return make_response(message, 200, {"X-Slack-No-Retry": 1})


@app.route("/install", methods=["GET"])
def pre_install():
    """This route renders the installation page with 'Add to Slack' button."""
    # Since we've set the client ID and scope on our Bot object, we can change
    # them more easily while we're developing our app.
    client_id = pyBot.oauth["client_id"]
    scope = pyBot.oauth["scope"]
    # Our template is using the Jinja templating language to dynamically pass
    # our client id and scope
    return render_template("install.html", client_id=client_id, scope=scope)


@app.route("/thanks", methods=["GET", "POST"])
def thanks():
    """
    This route is called by Slack after the user installs our app. It will
    exchange the temporary authorization code Slack sends for an OAuth token
    which we'll save on the bot object to use later.
    To let the user know what's happened it will also render a thank you page.
    """
    # Let's grab that temporary authorization code Slack's sent us from
    # the request's parameters.
    code_arg = request.args.get('code')
    # The bot's auth method to handles exchanging the code for an OAuth token
    pyBot.auth(code_arg)
    return render_template("thanks.html")

@app.route("/update", methods=["GET", "POST"]) 
def update():
    """
    This route is called by Postman to initialize the Slack client with
    our access token. Otherwise in development the token never gets updated
    """
    token = request.args.get('token')
    team_id = request.args.get('team_id')
    pyBot.update_token(team_id, token)
    return make_response("Token updated", 200, {"content_type":
                                                "application/json"
                                                })
@app.route("/init_conference", methods=["GET", "POST"])
def start_conference():
    """
    This route is called by the slash command /init_conference for creating 
    an integrated conference object with multiple committees that may or may 
    not interact. This way there will be one slack team for the entire conference
    """
    def make_conference(conference_info):
             
        admin = {conference_info["user_id"]:conference_info["user_name"]}
            
        conference = {conference_info["team_id"]:conference_info["text"]} 
        pyBot.create_conference(conference, admin, conference_info["response_url"] )
        
    thread = Thread(target=make_conference, kwargs={'conference_info':request.form})

     
    
    if len(request.form["text"]) > 3: # for minamum MUN 
        message = "conference " + request.form["text"] + " initializing" 
        thread.start()
    else:
        message = "please supply conference name[/init_conference [name]]"
    return make_response(message, 200, {"content_type":"application/json"})

@app.route("/init_universe", methods=["GET", "POST"])
def start_universe():
    """
    This route is called by the slash command /init_universe for creating
    a 'universe' in the conference (a stand-alone committee has is one committee
    in one universe, an X-number-JCC is X committees in one universe).
    Must be called after a call to/init_conference
   
    Slash commands send data as url-form-encoded which gets put into 
    request.form NOT request.data

    """
    if not pyBot.conference:
        #Conference has not been set 
        return make_response("conference not initialized", 200, {"content_type":
                                                                 "plain text"})
    universe_jcc = True
    universe_info = request.form
    
    print(universe_info)
    payload = universe_info["text"]
    if "jcc" in payload: universe_jcc = True 
    payload = payload.split(" ")
    committee_list = set()
    for word in payload:
        if '<#' not in word and '#' in word:
            word = word[1:21].lower()
            ok ="_0123456789-abcdefghijklmnopqrstuvwxyz"
            if all(c in ok for c in word):
                committee_list.add(word)
    
    if not universe_jcc:
        committee_list.add({"name": universe_info["channel_name"],
                            "id": universe_info["channel_id"]})


    pybot.create_universe(universe_info["channel_name"],
                          universe_info["channel_id"],
                          committee_list,
                          universe_jcc)


@app.route("/add_jcc", methods=["GET", "POST"])
def add_jcc():
    """ have to include the #channel that is the 
    base of the jcc"""
    if not pybot.conference:
        #conference hasn't been initialized    
        return make_response("conference not initialized", 200, {"content_type":
                                                                 "plain text"})
    
    universe_id  = None
    committee_info = request.form
    payload = committee_info["text"]
    if "<#" in payload:
        payload = payload.split("<#") 
        universe_id = payload[1].split(">")
    else:
        #channel not specified! 
        return make_response("channel not specified", 200, {"content_type":
                                                                 "plain text"})
    
    if universe_id:
        pybot.add_universe_committee(universe_id, 
                                     committee_info["channel_name"], 
                                     committee_info["channel_id"])
    else:
        #could not parse universe_id 
        
        return make_response("could not find universe channel", 200, {"content_type":
                                                                 "plain text"})


@app.route("/listening", methods=["GET", "POST"])
def hears():
    """
    This route listens for incoming events from Slack and uses the event
    handler helper function to route events to our Bot.
    """
    slack_event = json.loads(request.data)

    # ============= Slack URL Verification ============ #
    # In order to verify the url of our endpoint, Slack will send a challenge
    # token in a request and check for this token in the response our endpoint
    # sends ba/ck.
    #       For more info: https://api.slack.com/events/url_verification
    if "challenge" in slack_event:
        return make_response(slack_event["challenge"], 200, {"content_type":
                                                             "application/json"
                                                             })

    # ============ Slack Token Verification =========== #
    # We can verify the request is coming from Slack by checking that the
    # verification token in the request matches our app's settings
    if pyBot.verification != slack_event.get("token"):
        message = "Invalid Slack verification token: %s \npyBot has: \
                   %s\n\n" % (slack_event["token"], pyBot.verification)
        # By adding "X-Slack-No-Retry" : 1 to our response headers, we turn off
        # Slack's automatic retries during development.
        make_response(message, 403, {"X-Slack-No-Retry": 1})

    # ====== Process Incoming Events from Slack ======= #
    # If the incoming request is an Event we've subcribed to
    if "event" in slack_event:
        event_type = slack_event["event"]["type"]
        # Then handle the event by event_type and have your bot respond
        return _event_handler(event_type, slack_event)
    # If our bot hears things that are not events we've subscribed to,
    # send a quirky but helpful error response
    return make_response("[NO EVENT IN SLACK REQUEST] These are not the droids\
                         you're looking for.", 404, {"X-Slack-No-Retry": 1})


if __name__ == '__main__':
    app.run(debug=True, threaded=True)
