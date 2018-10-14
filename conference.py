class munConference(object):
    def __init__(self, conference, admin):
        super(munConference, self).__init__()
        self.name = conference.values()[0]
        self.conference_id = conference.keys()[0]
        self.admin = admin
        self.secretariat = {}
        self.directorate = {}
        self.general_staff = {}
        self.all_staff = {"secretariat": self.secretariat, 
                          "directorate": self.directorate,
                          "general": self.general_staff}
        self.delegates = {}
        self.universes = {}
        self.all_users = {}
        self.advisors = {}
        self.schools = {}
        self.channels = {}

    def add_channels(self, new_channels):
        self.channels.update(new_channels)

    def add_secretariat_member(self, user):
        self.secretariat[user["id"]] = user["name"] 
        self.all_users[user["id"]] = user["name"]
        user["is_staff"] = True
        
    def add_directorate_member(self, user):
        self.directorate[user["id"]] = user["name"]
        self.all_user[user["id"]] = user["name"]
        user["is_staff"] = True

    def add_staff_member(self, user):
        self.general_staff[user["id"]] = user["name"]
        self.all_users[user["id"]] = user["name"]
        user["is_staff"] = True

    def assign_staff_universe(self, user, universe):
        if user["is_staff"]: 
            """
            if (    user_id in self.all_staff["general_staff"] or
                    user_id in self.all_staff["secretariat"] or
                    user_id in self.all_staff["directorate"]):
            """    
            if universe in self.universes.values():
                universe["staff"][user_id] = user
                for committee in universe["committees"].values():
                    committee["staff"][user_id] = user
        else:
            #not a staff member
            return 

    def create_universe(self, name, universe_id):
        """
        Ideally universe_id is the channel_id for the public main branch of the committee
        and committee_list is the channel_id for the private channels of the branch
        """
        new_universe = { 
                "name": name,
                "staff": {},
                "committees": committee_list
                }
        self.universes[universe_id] = new_universe
    
    def add_universe_committee(self, universe_id, committee_name, committee_id):
        new_committee = {
                "name":committee_name,
                "staff":{},
                "delegates":{}
                }
        self.universes[universe_id]["committees"][committee_id] = new_committee
    
    def add_delegate(self, universe_id, committee_id, position, delegate_id, 
            school_id, school_name, personal_name):
        unviverse = self.universe[universe_id]
        committee = unvierse["committees"][committee_id]
        delegate = {
                "user_id": delegate_id,
                "universe": universe["name"],
                "committee": committee["name"],
                "position": position,
                "school" : {school_id: school_name},
                "name": personal_name,
                "type": "delegate"
                }
        committee["delegates"][delegate_id] = delegate
        self.schools[school_id]["delegates"][delegate_id] = delegate 

    def add_advisor(self, advisor_id, advisor_name, school_id, school_name):
        advisor = {
                "user_id": advisor_id,
                "name": advisor_name,
                "school": {school_id: school_name},
                "type": "advisor"
                }
        self.advisors[advisor_id] = advisor_name
        self.schools[school_id]["advisors"][advisor_id] = advisor

    def add_school(self, school_id, school_name):
        school = {
                "id": school_id,
                "name": school_name,
                "advisors": {},
                "delegates": {} 
                }
        self.schools[school_id] = school
    
    def add_admin(self, user_id):
        self.admin.add(user_id)


    """
    committee Dictonary = {

        "chair": {user_id : user_name},
        "staff": { staff_id : staff_name,
                   staff_id : staff_name ,
                   ... }
        "delegates": { delegate_id : delegate_name,
                       delegate_id : delegate_name,
                       ... }

    }
    universe dictionary = {
        universe_id : { "staff" : {staff_id : staff_name,
                                    staff_id : staff_name
                                    ... }
                        "committees": {committee_id : committee_name,
                                        committee_id : committee_name
                                        ...}


                        }
        universe_id2 : {....}
    }

    """
