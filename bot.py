# -*- coding: utf-8 -*-
"""
Python Slack Bot class for use with the pythOnBoarding app
"""
import os
import message
import requests 
import json, codecs, io 

from conference import munConference

from slackclient import SlackClient


# To remember which teams have authorized your app and what tokens are
# associated with each team, we can store this information in memory on
# as a global object. When your bot is out of development, it's best to
# save this in a more persistant memory store.
authed_teams = {}
authed_users = {}

class Bot(object):
    """ Instanciates a Bot object to handle Slack onboarding interactions."""
    def __init__(self):
        super(Bot, self).__init__()
        self.name = "pythonboardingbot"
        self.emoji = ":robot_face:"
        # When we instantiate a new bot object, we can access the app
        # credentials we set earlier in our local development environment.
        self.oauth = {"client_id": os.environ.get("CLIENT_ID"),
                      "client_secret": os.environ.get("CLIENT_SECRET"),
                      # Scopes provide and limit permissions to what our app
                      # can access. It's important to use the most restricted
                      # scope that your app will need.
                      "scope": "bot"}
        self.verification = os.environ.get("VERIFICATION_TOKEN")
		
        # We'll use this dictionary to store the state of each message object.
        # In a production envrionment you'll likely want to store this more
        # persistantly in  a database.
        self.messages = {} 
        self.conference = {}
        try:
            with open('data.txt', 'r') as json_file:
                data = json.load(json_file) 
                self.bot_id = data["bot"]["bot_user_id"]
                self.bot_token = data["bot"]["bot_access_token"]
                self.token = data["access_token"]
                self.client = SlackClient(self.token) 
                self.user_id = data["user_id"]
                authed_users[self.user_id] = {"access_token":self.token}
                print("data successfully loaded!\n"+ json.dumps(data, indent=4))
        except:
            # NOTE: Python-slack requires a client connection to generate
            # an oauth token. We can connect to the client without authenticating
            # by passing an empty string as a token and then reinstantiating the
            # client with a valid OAuth token once we have one.
            self.client = SlackClient("")
	    self.user_id = None
            self.bot_id = None
            self.bot_token = None
            self.token = None

    def auth(self, code):
        """
        Authenticate with OAuth and assign correct scopes.
        Save a dictionary of authed team information in memory on the bot
        object.

        Parameters
        ----------
        code : str
            temporary authorization code sent by Slack to be exchanged for an
            OAuth token

        """
        # After the user has authorized this app for use in their Slack team,
        # Slack returns a temporary authorization code that we'll exchange for
        # an OAuth token using the oauth.access endpoint
        auth_response = self.client.api_call(
                                "oauth.access",
                                client_id=self.oauth["client_id"],
                                client_secret=self.oauth["client_secret"],
                                code=code
                                )
        try: 
            with open('data.txt', 'w') as outfile:
                                                    
                self.user_id = auth_response["user_id"]
                # To keep track of authorized teams and their associated OAuth tokens,
                # we will save the team ID and bot tokens to the global
                # authed_teams object
                team_id = auth_response["team_id"]
                self.bot_id = auth_response["bot"]["bot_user_id"]
                authed_teams[team_id] = {"bot_token":
                                         auth_response["bot"]["bot_access_token"]}

                authed_users[self.user_id] = { "access_token" : auth_response["access_token"],}
                authorized = {"users": authed_users, "teams":authed_teams} 
                # Then we'll reconnect to the Slack Client with the correct team's
                # bot token
                self.client = SlackClient(authed_users[self.user_id]["access_token"])
                auth_response.update(authorized) 
                pretty = json.dumps(auth_response, indent=4)
                print(pretty) 
                outfile.write(pretty) 
        except:
            pass

    def update_token(self, team_id, token):
        authed_teams[team_id] = {"bot_token":token} 
        self.client = SlackClient(token=token)
    
    def open_dm(self, user_id):
        """
        Open a DM to send a welcome message when a 'team_join' event is
        recieved from Slack.

        Parameters
        ----------
        user_id : str
            id of the Slack user associated with the 'team_join' event

        Returns
        ----------
        dm_id : str
            id of the DM channel opened by this method
        """
        new_dm = self.client.api_call("im.open",
                                      user=user_id)
        dm_id = new_dm["channel"]["id"]
        return dm_id

    def onboarding_message(self, team_id, user_id):
        """
        Create and send an onboarding welcome message to new users. Save the
        time stamp of this message on the message object for updating in the
        future.

        Parameters
        ----------
        team_id : str
            id of the Slack team associated with the incoming event
        user_id : str
            id of the Slack user associated with the incoming event

        """
        # We've imported a Message class from `message.py` that we can use
        # to create message objects for each onboarding message we send to a
        # user. We can use these objects to keep track of the progress each
        # user on each team has made getting through our onboarding tutorial.

        # First, we'll check to see if there's already messages our bot knows
        # of for the team id we've got.
        if self.messages.get(team_id):
            # Then we'll update the message dictionary with a key for the
            # user id we've recieved and a value of a new message object
            self.messages[team_id].update({user_id: message.Message()})
        else:
            # If there aren't any message for that team, we'll add a dictionary
            # of messages for that team id on our Bot's messages attribute
            # and we'll add the first message object to the dictionary with
            # the user's id as a key for easy access later.
            self.messages[team_id] = {user_id: message.Message()}
        message_obj = self.messages[team_id][user_id]
        # Then we'll set that message object's channel attribute to the DM
        # of the user we'll communicate with
        message_obj.channel = self.open_dm(user_id)
        # We'll use the message object's method to create the attachments that
        # we'll want to add to our Slack message. This method will also save
        # the attachments on the message object which we're accessing in the
        # API call below through the message object's `attachments` attribute.
        message_obj.create_attachments()
        post_message = self.client.api_call("chat.postMessage",
                                            channel=message_obj.channel,
                                            username=self.name,
                                            icon_emoji=self.emoji,
                                            text=message_obj.text,
                                            attachments=message_obj.attachments
                                            )
        timestamp = post_message["ts"]
        # We'll save the timestamp of the message we've just posted on the
        # message object which we'll use to update the message after a user
        # has completed an onboarding task.
        message_obj.timestamp = timestamp

    def update_emoji(self, team_id, user_id):
        """
        Update onboarding welcome message after recieving a "reaction_added"
        event from Slack. Update timestamp for welcome message.

        Parameters
        ----------
        team_id : str
            id of the Slack team associated with the incoming event
        user_id : str
            id of the Slack user associated with the incoming event

        """
        # These updated attachments use markdown and emoji to mark the
        # onboarding task as complete
        completed_attachments = {"text": ":white_check_mark: "
                                         "~*Add an emoji reaction to this "
                                         "message*~ :thinking_face:",
                                 "color": "#439FE0"}
        # Grab the message object we want to update by team id and user id
        message_obj = self.messages[team_id].get(user_id)
        # Update the message's attachments by switching in incomplete
        # attachment with the completed one above.
        message_obj.emoji_attachment.update(completed_attachments)
        # Update the message in Slack
        post_message = self.client.api_call("chat.update",
                                            channel=message_obj.channel,
                                            ts=message_obj.timestamp,
                                            text=message_obj.text,
                                            attachments=message_obj.attachments
                                            )
        # Update the timestamp saved on the message object
        message_obj.timestamp = post_message["ts"]

    def update_pin(self, team_id, user_id):
        """
        Update onboarding welcome message after recieving a "pin_added"
        event from Slack. Update timestamp for welcome message.

        Parameters
        ----------
        team_id : str
            id of the Slack team associated with the incoming event
        user_id : str
            id of the Slack user associated with the incoming event

        """
        # These updated attachments use markdown and emoji to mark the
        # onboarding task as complete
        completed_attachments = {"text": ":white_check_mark: "
                                         "~*Pin this message*~ "
                                         ":round_pushpin:",
                                 "color": "#439FE0"}
        # Grab the message object we want to update by team id and user id
        message_obj = self.messages[team_id].get(user_id)
        # Update the message's attachments by switching in incomplete
        # attachment with the completed one above.
        message_obj.pin_attachment.update(completed_attachments)
        # Update the message in Slack
        post_message = self.client.api_call("chat.update",
                                            channel=message_obj.channel,
                                            ts=message_obj.timestamp,
                                            text=message_obj.text,
                                            attachments=message_obj.attachments
                                            )
        # Update the timestamp saved on the message object
        message_obj.timestamp = post_message["ts"]

    def update_share(self, team_id, user_id):
        """
        Update onboarding welcome message after recieving a "message" event
        with an "is_share" attachment from Slack. Update timestamp for
        welcome message.

        Parameters
        ----------
        team_id : str
            id of the Slack team associated with the incoming event
        user_id : str
            id of the Slack user associated with the incoming event

        """
        # These updated attachments use markdown and emoji to mark the
        # onboarding task as complete
        completed_attachments = {"text": ":white_check_mark: "
                                         "~*Share this Message*~ "
                                         ":mailbox_with_mail:",
                                 "color": "#439FE0"}
        # Grab the message object we want to update by team id and user id
        message_obj = self.messages[team_id].get(user_id)
        # Update the message's attachments by switching in incomplete
        # attachment with the completed one above.
        message_obj.share_attachment.update(completed_attachments)
        # Update the message in Slack
        post_message = self.client.api_call("chat.update",
                                            channel=message_obj.channel,
                                            ts=message_obj.timestamp,
                                            text=message_obj.text,
                                            attachments=message_obj.attachments
                                            )
        # Update the timestamp saved on the message object
        message_obj.timestamp = post_message["ts"]

    def check_existing_channels(self, channel_set, head_honchos):
        
        conf_channels = {}
        next_cursor = None 
        while next_cursor is None or next_cursor:
            args= {"excluded_archived":True, "types":"public_channel,private_channel",}
            if next_cursor: args["cursor"] = next_cursor
            channel_batch = self.client.api_call(
                        "conversations.list", 
                         **args
                         )
            if channel_batch["ok"]:

                for channel in channel_batch["channels"]:
                    if channel["name"] in channel_set:
                        conf_channels[channel["id"]] = channel["name"]
                        self.invite_missing_members(channel["id"], head_honchos, True) 
                        message = """This channel has been co-opted 
                                    into the MUN conference: %s 
                                    started by """ % (self.conference.name)
                        for user_id in head_honchos:
                            message = " ". join((message,"<@%s>"% user_id))
                        self.send_message(channel["id"], message)
                next_cursor = channel_batch["response_metadata"].get("next_cursor")
            else: next_cursor = ""
        return conf_channels  
    
    def send_message(self, channel_id, message):
        
       message_response = self.client.api_call(
                "chat.postMessage",
                 channel=channel_id,
                 text=message,
                 as_user=False,
                 username="MUN Conference",
                 link_names=True,
                 )
       if not message_response["ok"]:
           print(message_response)

    def invite_missing_members(self, channel_id, head_honchos, existed):
        head_honchos.add(self.bot_id)
        if existed:
            next_cursor = None
            while next_cursor is None or next_cursor:
                member_args= {"channel":channel_id,}
                if next_cursor: member_args["cursor"] = next_cursor 
                response = self.client.api_call(
                        "conversations.members",
                        **member_args
                        )
                if response["ok"]:
                    channel_members = set(response["members"]) 
                    self.invite_members(channel_id, head_honchos.difference(channel_members)) 
                    next_cursor = response["response_metadata"].get("next_cursor")
                else: 
                    next_cursor = "" 
                    print(response)
        else:
            self.invite_members(channel_id, head_honchos.difference({self.user_id})) 
    
    
    def invite_members(self, channel_id, members):
        if members:
            response = self.client.api_call(
                            "conversations.invite", 
                            channel=channel_id, 
                            users=",".join(members) #limited to 30 members
                            )
            if not response["ok"]:
                print(response)



    def make_remaining_channels(self, channel_set, private_channels, head_honchos):
        new_channels = {} 
        for channel in channel_set:
            response = self.client.api_call("conversations.create", 
                                            name=channel,
                                            is_private=channel in private_channels,
                                            )
            if response["ok"]:
                new_channels[response["channel"]["id"]] = response["channel"]["name"]
                self.invite_missing_members(response["channel"]["id"], head_honchos, False) 
                message = """This channel has been created 
                            for the MUN conference: %s 
                            started by """ % self.conference.name, 
                for user_id in head_honchos:
                    message = " ". join((message,"<@%s>"% user_id))
                self.send_message(channel["id"], message) 
            else:
                print(response)
        return new_channels
    
    def create_conference(self, conference, admin, response_url):
         
        self.conference = munConference(conference, admin,) 
        head_honchos = set(admin) #guaranteed to exist
        try:
            head_honchos = head_honchos.union(self.conference.secretariat)
            head_honchos = head_honchos.union(self.conference.directorate)
        except:
            pass
        #setup default channels 
        public_channels = {"announcements", "advisors",}
        private_channels = {"secretariat", "directorate", "all_staff"} 
        channel_set = public_channels.union(private_channels) 
        #check if these channels already exist
        conf_channels = self.check_existing_channels(channel_set, head_honchos)
        #create missing channels for 
        new_channels = self.make_remaining_channels(channel_set.difference(conf_channels.values()), private_channels, head_honchos)
        conf_channels.update(new_channels) 
        self.conference.add_channels(conf_channels)
        #send reply that it's finished. 
        headers = {"Content-type": "application/json"}
        r = requests.post(response_url,  
                          headers=headers, 
                          data={"response_type": "in_channel",
                                "text":"Conference: " + self.conference.name + " has been initialized",
                                "attachments":[],
                                }
                          )
        print("request sent.\nresponse" + r.text) 
    
    def create_universe(self, name, universe_id, committee_list, universe_jcc):
        self.conference.create_universe(name, universe_id)
        if universe_jcc:
            for committee_name in committee_list:
                private_channel = self.client.api_call("groups.create",
                                                        name=committee_name)
                self.conference.add_universe_committee(universe_id, 
                                                       private_channel["group"]["name"],
                                                       private_channel["group"]["id"])
        else:
            #committee is standalone
            self.conference.add_universe_committee(universe_id,
                                                   committee_list["name"],
                                                   committee_list["id"])

    def add_universe_committee(self, universe_id, committee_name, committee_id):
        self.conference.add_universe_committee(universe_id, committee_name, committee_id)

