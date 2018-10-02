import string
import os
from flask import Flask, request, jsonify
import random
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import json
import base64
from requests import post

from send_mail import send_mail

registrations_closed = False

eventTypes = {'Technical': 1, 'Cultural': 2, 'Lectures': 3, 'Workshops': 4, 'Shows': 5}
level = {
    'ADMIN': '0',
    'COORD': '1',
    'EDITOR': '2',
    'USERMANAGER': '3',
    'USER': '4'
}

f = open('categories.json', encoding='utf8')
cats = json.load(f)
f.close()

categories = dict()
for cat in cats:
    for subcat in cat['sub_categories']:
        categories[subcat['name']] = subcat['id']

################################################################

app = Flask(__name__)

CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://mayank:Pec_160012@localhost:3306/pecfest_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

################################################################

from models.model import pass_param

pass_param(db)

from models.event import Event
from models.user import User
from models.pecfestIds import PecfestIds
from models.otps import OTPs
from models.event_registration import EventRegistration
from models.sent_sms import SentSMS
from models.session import Session
from models.coordinator import Coordinator


################################################################

def genPecfestId(name, length=6):
    done = False
    proposedId = ''
    while not done:
        proposedId = name + ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(length))
        alreadyId = PecfestIds.query.filter_by(pecfestId=proposedId).first()
        if alreadyId == None:
            break
    return proposedId


db.create_all()


################################################################
#####################EVENT MANAGEMENT###########################

# return categories
@app.route('/v1/categories', methods=['GET'])
def getCategories():
    return jsonify(cats)


# Create event
@app.route('/v1/event/create', methods=['POST'])
def createEvent():
    session, user = authenticateUser(request)

    if not session:
        return jsonify({'ACK': 'FAILED', 'message': user})

    coordinator = Coordinator.query.filter_by(userId=user.pecfestId).first()

    if not coordinator or coordinator.level > level['COORD']:
        return jsonify({'ACK': 'FAILED', 'message': 'You are not allowed to do this operation'})

    data = request.get_json()

    try:
        name = data["name"]
        coordinators = data["coordinators"]
        location = data["location"] if "location" in data else ''
        day = data["day"] if "day" in data else 0
        time = data["time"] if "time" in data else "0"
        prize = data["prize"] if "prize" in data else "0"
        minSize = data["minSize"] if "minSize" in data else 1
        maxSize = data["maxSize"] if "maxSize" in data else 1
        eventType = eventTypes[data["eventType"]]
        category = categories[data["category"]]
        clubId = data["clubId"] if "clubId" in data else "PEC"
        details = data["details"] if "details" in data else ""
        shortDescription = data["shortDescription"] if "shortDescription" in data else ""
        imageUrl = data["imageUrl"] if "imageUrl" in data else ""
        rulesList = data["rulesList"] if "rulesList" in data else ""
        pdfUrl = data["pdfUrl"] if "pdfUrl" in data else ""
    except KeyError as e:
        return jsonify({'ACK': 'FAILED', 'message': 'Missing ' + e.args[0]})

    event = Event(name=name,
                  coordinators=coordinators,
                  location=location,
                  day=day,
                  time=time,
                  prize=prize,
                  minSize=minSize,
                  maxSize=maxSize,
                  eventType=eventType,
                  category=category,
                  clubId=clubId,
                  details=details,
                  shortDescription=shortDescription,
                  imageUrl=imageUrl,
                  rulesList=rulesList,
                  pdfUrl=pdfUrl)

    curr_session = db.session
    success = False
    try:
        curr_session.add(event)
        curr_session.commit()
        success = True
    except Exception as err:
        print(err);
        curr_session.rollback()
        curr_session.flush()

    if success:
        return jsonify({'ACK': 'SUCCESS'})
    return jsonify({'ACK': 'FAILED'})


# Get event details
@app.route('/v1/event/<int:eventId>', methods=['GET'])
def getEventDetails(eventId):
    eventInfo = {}
    event = Event.query.filter_by(eventId=eventId).first()

    if event == None:
        eventInfo["ACK"] = "FAILED"
        return jsonify(eventInfo)

    eventInfo["ACK"] = "SUCCESS"
    eventInfo["id"] = event.eventId
    eventInfo["name"] = event.name
    eventInfo["coordinators"] = event.coordinators
    eventInfo["location"] = event.location
    eventInfo["day"] = event.day
    eventInfo["time"] = event.time
    eventInfo["prize"] = event.prize
    eventInfo["minSize"] = event.minSize
    eventInfo["maxSize"] = event.maxSize
    eventInfo["eventType"] = event.eventType
    eventInfo["category"] = event.category
    eventInfo["clubId"] = event.clubId
    eventInfo["details"] = event.details
    eventInfo["shortDescription"] = event.shortDescription
    eventInfo["imageUrl"] = event.imageUrl
    eventInfo["rulesList"] = event.rulesList
    eventInfo["pdfUrl"] = event.pdfUrl

    return jsonify(eventInfo)


# edit events
@app.route('/v1/event/update', methods=['POST'])
def updateEvent():
    session, user = authenticateUser(request)

    if not session:
        return jsonify({'ACK': 'FAILED', 'message': user})

    coordinator = Coordinator.query.filter_by(userId=user.pecfestId).first()

    if not coordinator or coordinator.level > level['EDITOR']:
        return jsonify({'ACK': 'FAILED', 'message': 'You are not allowed to do this operation'})

    '''
        Update event information.
    '''
    data = request.get_json()

    eventId = data["id"]
    event = Event.query.filter_by(eventId=eventId).first()

    event.name = data["name"] if "name" in data else event.name
    event.coordinators = data["coordinators"] if "coordinators" in data else event.coordinators
    event.location = data["location"] if "location" in data else event.location
    event.day = data["day"] if "day" in data else event.day
    event.time = data["time"] if "time" in data else event.time
    event.prize = data["prize"] if "prize" in data else event.prize
    event.minSize = data["minSize"] if "minSize" in data else event.minSize
    event.maxSize = data["maxSize"] if "maxSize" in data else event.maxSize
    event.eventType = data["eventType"] if "eventType" in data else event.eventType
    event.category = data["category"] if "category" in data else event.category
    event.clubId = data["clubId"] if "clubId" in data else event.clubId
    event.details = data["details"] if "details" in data else event.details
    event.shortDescription = data["shortDescription"] if "shortDescription" in data else event.shortDescription
    event.imageUrl = data["imageUrl"] if "imageUrl" in data else event.imageUrl
    event.rulesList = data["rulesList"] if "rulesList" in data else event.rulesList
    event.pdfUrl = data["pdfUrl"] if "pdfUrl" in data else event.pdfUrl

    db.session.commit()
    return jsonify({"ACK": "SUCCESS"})


# Get event details
@app.route('/v1/event/category/<int:eventCategory>', methods=['GET'])
def getEventFromCategory(eventCategory):
    eventsInfo = {}
    events = Event.query.filter_by(category=eventCategory)

    if events == None:
        eventsInfo["ACK"] = "FAILED"
        return jsonify(eventsInfo)

    eventsInfo["ACK"] = "SUCCESS"

    for event in events:
        eventInfo = {}

        eventInfo["id"] = event.eventId
        eventInfo["name"] = event.name
        eventInfo["coordinators"] = event.coordinators
        eventInfo["location"] = event.location
        eventInfo["day"] = event.day
        eventInfo["time"] = event.time
        eventInfo["prize"] = event.prize
        eventInfo["minSize"] = event.minSize
        eventInfo["maxSize"] = event.maxSize
        eventInfo["eventType"] = event.eventType
        eventInfo["category"] = event.category
        eventInfo["clubId"] = event.clubId
        eventInfo["details"] = event.details
        eventInfo["shortDescription"] = event.shortDescription
        eventInfo["imageUrl"] = event.imageUrl
        eventInfo["rulesList"] = event.rulesList
        eventInfo["pdfUrl"] = event.pdfUrl

        eventsInfo[event.name] = eventInfo

    return jsonify(eventsInfo)


@app.route('/v1/events', methods=["GET"])
def getAllEvents():
    eventsInfo = []
    events = Event.query.all()

    for event in events:
        eventInfo = {}

        eventInfo["id"] = event.eventId
        eventInfo["name"] = event.name
        eventInfo["coordinators"] = event.coordinators
        eventInfo["location"] = event.location
        eventInfo["day"] = event.day
        eventInfo["time"] = event.time
        eventInfo["prize"] = event.prize
        eventInfo["minSize"] = event.minSize
        eventInfo["maxSize"] = event.maxSize
        eventInfo["eventType"] = event.eventType
        eventInfo["category"] = event.category
        eventInfo["clubId"] = event.clubId
        eventInfo["details"] = event.details
        eventInfo["shortDescription"] = event.shortDescription
        eventInfo["imageUrl"] = event.imageUrl
        eventInfo["rulesList"] = event.rulesList
        eventInfo["pdfUrl"] = event.pdfUrl

        eventsInfo.append(eventInfo)

    return jsonify(eventsInfo)


################################################################
#####################USER INFO##################################

def sendOTP(name, mobile, email, otp, pecfestId):
    data = dict()
    data['user'] = 'onlineteam.pecfest'
    data['password'] = 'onlinesms'
    data['sid'] = 'PECCHD'
    data['msisdn'] = '91' + mobile
    name = name.split(' ')[0]
    data['msg'] = "Hi " + name + ", your PECFEST ID is " + pecfestId + ". Happy participating!"
    data['gwid'] = 2
    data['fl'] = 0
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}

    res = post('http://www.smslane.com//vendorsms/pushsms.aspx', data=data, headers=headers)
    success = send_mail(email, data['msg'])
    if res.status_code is not 200:
        return False
    else:
        text = res.text
        if 'Message Id' in text:
            messageId = text.split(' : ')
            print(text)
            sms = SentSMS(smsId=messageId, mobile=mobile, smsType=1, status=1)

            session = db.session
            success = False
            try:
                session.add(sms)
                session.commit()
                success = True
            except:
                session.rollback()
                session.flush()
            return True
        else:
            print(text)
            return False


# Create User
@app.route('/v1/user/create', methods=['POST'])
def createUser():
    print(registrations_closed)
    if registrations_closed:
        return jsonify({'ACK': 'FAILED', 'message': 'Registrations are closed.'})

    data = request.get_json()

    try:
        name = data['name']
        pecfestId = genPecfestId(''.join(name.split(' '))[:3].strip().upper())
        college = data['college']
        email = data['email']
        mobile = data['mobile']
        gender = data['gender']
        accomodation = data['accomodation'] if "accomodation" in data else ""
        verified = 1
        smsCounter = 0
    except KeyError as e:
        return jsonify({'ACK': 'FAILED', 'message': 'Missing ' + e.args[0]})

    alreadyUser = User.query.filter_by(mobile=mobile).first()
    if alreadyUser:
        return jsonify({'ACK': 'ALREADY', 'message': 'Phone number already registered.'})

    user = User(pecfestId=pecfestId,
                name=name,
                college=college,
                email=email,
                mobile=mobile,
                gender=gender,
                accomodation=accomodation,
                verified=verified,
                smsCounter=smsCounter)

    newPecfestId = PecfestIds(pecfestId=pecfestId)

    OTP = ''.join(random.choice(string.digits) for _ in range(6))
    otp = OTPs(mobile=mobile,
               otp=OTP)

    # send otp to the user's mobile number
    status = sendOTP(name, mobile, email, OTP, pecfestId)
    if not status:
        return jsonify({'ACK': 'FAILED', 'message': 'Unable to send OTP.'})

    curr_session = db.session
    success = False
    try:
        curr_session.add(user)
        curr_session.add(newPecfestId)
        curr_session.add(otp)
        curr_session.commit()
        success = True
    except Exception as err:
        print(err)
        curr_session.rollback()
        curr_session.flush()

    if success:
        return jsonify({'ACK': 'SUCCESS', 'pecfestId': pecfestId})
    return jsonify({'ACK': 'FAILED'})


@app.route('/v1/user/forgot_pecfestid', methods=['POST'])
def forgotPecfestId():
    data = request.get_json()
    try:
        email = data['email']
    except KeyError as e:
        return jsonify({'ACK': 'FAILED', 'message': 'Missing ' + e.args[0]})

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'ACK': 'FAILED', 'message': 'User not found'})

    success = send_mail(user.email, 'Your PECFEST ID is ' + user.pecfestId)
    if success:
        return jsonify({'ACK': 'SUCCESS', 'message': 'Successfully sent mail!'})
    return jsonify({'ACK': 'FAILED', 'message': 'Unable to send email!'})


# login service that works only for the admins/coordinators of the website,
# it returns key that stores the session in the session database
# 3 access levels:
#		0: ADMIN, me
#		1: COORDINATOR
#		2: RESERVED
@app.route('/v1/portal/user/coordinator', methods=['POST'])
def loginUser():
    if 'Authorization' not in request.headers:
        return jsonify({'ACK': 'FAILED', 'message': 'Permission denied.'})

    auth = request.headers['Authorization']
    encoded_info = auth.replace('Basic ', '', 1)

    user = ''
    password = ''
    try:
        userpasswd = base64.b64decode(encoded_info).decode('utf-8')
        user = userpasswd.split(':')[0]
        password = userpasswd.split(':')[1]
    except:
        return jsonify({'ACK': 'FAILED', 'message': 'Wrong session.'})

    result = db.session.query(Coordinator, User).join(User, User.pecfestId == Coordinator.userId).filter(
        db.and_(Coordinator.userId == user, Coordinator.password == password)).first()

    if not result:
        return jsonify({'ACK': 'FAILED', 'message': 'Wrong username/password'})

    print(result)
    coordinator, userInfo = result

    user_ = userInfo.__dict__
    user_.pop('_sa_instance_state')
    print(user_)
    user_ = {**user_}

    # create a token and save it to the database
    sessionKey = ''.join(random.choice(string.digits) for _ in range(6))
    session = Session(userId=userInfo.pecfestId, sessionKey=sessionKey)

    sessionKey = base64.b64encode(sessionKey.encode('ascii')).decode('utf-8')
    try:
        db.session.add(session)
        db.session.commit()
    except Exception as err:
        print(err)
        db.session.rollback()
        db.session.flush()
        return jsonify({'ACK': 'FAILED'})

    return jsonify({'user': user_, 'ACK': 'SUCCESS', 'sessionKey': sessionKey})


@app.route("/v1/portal/user/logout", methods=['POST'])
def logoutCoordinator():
    if 'Authorization' not in request.headers:
        return jsonify({'ACK': 'FAILED', 'message': 'Permission denied.'})

    auth = request.headers['Authorization']
    session = auth.replace('Basic ', '', 1)

    sessionKey = ''
    try:
        sessionKey = base64.b64decode(session).decode('utf-8')
    except:
        return jsonify({'ACK': 'FAILED', 'message': 'Wrong session.'})

    result = Session.query.filter_by(sessionKey=sessionKey).first()

    print(result)
    if result:
        try:
            db.session.delete(result)
            db.session.commit()
        except Exception as err:
            print(err)
            db.session.rollback()
            db.session.flush()

    return jsonify({'ACK': 'SUCCESS'})


# get the user information from the
@app.route("/v1/portal/user", methods=['POST'])
def getCoordinator():
    if 'Authorization' not in request.headers:
        return jsonify({'ACK': 'FAILED', 'message': 'Permission denied.'})

    auth = request.headers['Authorization']
    session = auth.replace('Basic ', '', 1)

    sessionKey = ''
    try:
        sessionKey = base64.b64decode(session).decode('utf-8')
    except Exception as err:
        print(err)
        return jsonify({'ACK': 'FAILED', 'message': 'Wrong session.'})

    result = db.session.query(Session, User).join(User, User.pecfestId == Session.userId).filter(
        Session.sessionKey == sessionKey).first()

    if not result:
        return jsonify({'ACK': 'FAILED', 'message': 'Session expired.'})

    session, user = result

    user = user.__dict__
    user.pop('_sa_instance_state')
    return jsonify({'ACK': 'SUCCESS', 'user': user})


def authenticateUser(request):
    if 'Authorization' not in request.headers:
        return (None, "Permission denied")

    auth = request.headers['Authorization']
    session = auth.replace('Basic ', '', 1)

    sessionKey = ''
    try:
        sessionKey = base64.b64decode(session).decode('utf-8')
    except Exception as err:
        print(err)
        return (None, "Unknown session.")

    result = db.session.query(Session, User).join(User, User.pecfestId == Session.userId).filter(
        Session.sessionKey == sessionKey).first()
    if not result:
        return (None, "Session expired.")

    return result


## allow coordinator to create new user
@app.route("/v1/portal/user/create", methods=["POST"])
def createUserFromPortal():
    session, user = authenticateUser(request)

    if not session:
        return jsonify({'ACK': 'FAILED', 'message': user})

    print(registrations_closed)
    if registrations_closed:
        return jsonify({'ACK': 'FAILED', 'message': 'Registrations are closed.'})

    data = request.get_json()

    try:
        name = data['name']
        pecfestId = genPecfestId(name[:3].strip().upper())
        college = data['college']
        email = data['email']
        mobile = data['mobile']
        gender = data['gender']
        accomodation = data['accomodation'] if "accomodation" in data else ""
        verified = 1
        smsCounter = 0
    except KeyError as e:
        return jsonify({'ACK': 'FAILED', 'message': 'Missing ' + e.args[0]})

    alreadyUser = User.query.filter_by(mobile=mobile).first()
    if alreadyUser:
        return jsonify({'ACK': 'ALREADY', 'message': 'Phone number already registered.'})

    user = User(pecfestId=pecfestId,
                name=name,
                college=college,
                email=email,
                mobile=mobile,
                gender=gender,
                accomodation=accomodation,
                verified=verified,
                smsCounter=smsCounter)

    newPecfestId = PecfestIds(pecfestId=pecfestId)
    curr_session = db.session
    success = False
    try:
        curr_session.add(user)
        curr_session.add(newPecfestId)
        curr_session.commit()
        success = True
    except Exception as err:
        print(err)
        curr_session.rollback()
        curr_session.flush()

    if success:
        return jsonify({'ACK': 'SUCCESS', 'pecfestId': pecfestId})
    return jsonify({'ACK': 'FAILED'})


# Get user's details
@app.route('/v1/user/<string:pecfestId>', methods=['GET'])
def getUserDetails(pecfestId):
    userInfo = {}
    user = User.query.filter_by(pecfestId=pecfestId).first()

    if user == None:
        userInfo["ACK"] = "FAILED"
        return jsonify(userInfo)

    userInfo["ACK"] = "SUCCESS"
    userInfo["pecfestId"] = user.pecfestId
    userInfo["name"] = user.name
    userInfo["college"] = user.college
    userInfo["gender"] = user.gender
    userInfo['verified'] = user.verified
    return jsonify(userInfo)


@app.route('/v1/users', methods=['GET'])
def getAllUsers():
    session, user = authenticateUser(request)

    if not session:
        return jsonify({'ACK': 'FAILED', 'message': user})

    coordinator = Coordinator.query.filter_by(userId=user.pecfestId).first()

    if not coordinator or coordinator.level > level['COORD']:
        return jsonify({'ACK': 'FAILED', 'message': 'You are not allowed to do this operation'})

    userInfos = []
    users = User.query.all()

    if users == None:
        userInfos["ACK"] = "FAILED"
        return jsonify(userInfos)

    for user in users:
        userInfo = {}
        userInfo["ACK"] = "SUCCESS"
        userInfo["pecfestId"] = user.pecfestId
        userInfo["name"] = user.name
        userInfo["college"] = user.college
        userInfo["gender"] = user.gender
        userInfo['verified'] = user.verified
        userInfo['email'] = user.email
        userInfo['mobile'] = user.mobile
        userInfo['accomodation'] = user.accomodation
        userInfos.append(userInfo)

    return jsonify(userInfos)


@app.route('/v1/user/update', methods=['POST'])
def updateUser():
    session, user = authenticateUser(request)

    if not session:
        return jsonify({'ACK': 'FAILED', 'message': user})

    coordinator = Coordinator.query.filter_by(userId=user.pecfestId).first()

    print(coordinator)
    if not coordinator or coordinator.level != level['ADMIN']:
        return jsonify({'ACK': 'FAILED', 'message': 'You are not allowed to do this operation'})

    data = request.get_json()

    email = data['email']

    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({'ACK': 'FAILED '})

    name = data['name'] if 'name' in data else user.name
    pecfestId = data['pecfestId'] if 'pecfestId' in data else user.pecfestId
    college = data['college'] if 'college' in data else user.college
    mobile = data['mobile'] if 'mobile' in data else user.mobile
    gender = data['gender'] if 'gender' in data else user.gender
    accomodation = data['accomodation'] if "accomodation" in data else user.accomodation
    db.session.commit()

    return jsonify({'ACK': 'SUCCESS'})


# verify user
@app.route('/v1/user/verify', methods=['POST'])
def verifyUser():
    userInfo = {}
    json = request.get_json()
    o = json['otp']
    mobile = json['mobile']

    otp = OTPs.query.filter_by(mobile=mobile,
                               otp=o).first()

    if otp:
        curr_session = db.session
        user = User.query.filter_by(mobile=mobile).update(dict(verified=1))
        user = User.query.filter_by(mobile=mobile).first()

        if user:
            success = False
            try:
                curr_session.delete(otp)
                curr_session.commit()
                success = True
            except:
                curr_session.rollback()
                curr_session.flush()

            if success:
                userInfo['ACK'] = 'SUCCESS'
                userInfo["pecfestId"] = user.pecfestId
                userInfo["name"] = user.name
                userInfo["college"] = user.college
                userInfo["gender"] = user.gender

                return jsonify(userInfo)
            else:
                return jsonify({'ACK': 'FAILED', message: 'Unknown error occurred'})
        else:
            return jsonify({'ACK': 'FAILED', message: 'User doesn\'t exist'})
    else:
        return jsonify({'ACK': 'FAILED', 'message': 'Wrong OTP'})


# returns the events that user has registered
@app.route('/v1/user/<string:pecfestId>/registered_events')
def getUsersEvents(pecfestId):
    result = db.session.execute("""
			select
				r.eventId,
			    e.name as eventName,
			    r.memberId,
			    u.name as memberName,
			    r.leaderId,
			    l.name as leaderName
			from Registration r
			join Event e on e.eventId = r.eventId
			join User u on u.pecfestId = r.memberId
			join User l on l.pecfestId = r.leaderId
			where leaderId in (select leaderId from Registration where memberId = :memberId)
		""", {'memberId': pecfestId}).fetchall();

    l = []
    j = dict()
    previous = -1
    count = 0
    for row in result:
        if row[0] != previous:
            if (count != 0):
                l.append(j)
            j = dict()
            j['event'] = {'id': row[0], 'name': row[1]}
            j['leader'] = {'pecfestId': row[4], 'name': row[5]}
            j['members'] = [{'pecfestId': row[2], 'name': row[3]}]
            count = count + 1
            previous = row[0]
        else:
            j['members'].append({'pecfestId': row[2], 'name': row[3]})

    l.append(j)
    return jsonify({'ACK': 'SUCCESS', 'result': l})


# check whether user is verified or not
@app.route('/v1/user/is_verified/<string:mobile>', methods=['GET'])
def getUserVerification(mobile):
    userInfo = {}
    user = User.query.filter_by(mobile=mobile).first()

    if user == None:
        userInfo["ACK"] = "FAILED"
        return jsonify(userInfo)

    if user.verified == 0:
        # delete previous sent otp from the database
        otp = OTPs.query.filter_by(mobile=mobile)

        session = db.session
        if otp:
            try:
                session.delete(otp)
                session.commit()
            except:
                session.rollback()
                session.flush()

        OTP = ''.join(random.choice(string.digits) for _ in range(6))
        otp = OTPs(mobile=mobile,
                   otp=OTP)

        # send otp again to the user's mobile number
        status = sendOTP(user.name, user.mobile, OTP, user.pecfestId)
        if not status:
            return jsonify({'ACK': 'FAILED', 'message': 'Unable to send OTP.'})

    userInfo["ACK"] = "SUCCESS"
    userInfo['verified'] = user.verified
    return jsonify(userInfo)


################################################################
#####################REGISTRATION###############################

@app.route('/v1/event/register', methods=['POST'])
def registerEvent():
    if registrations_closed:
        return jsonify({'ACK': 'FAILED', 'message': 'Registrations are closed.'})
    try:
        json = request.get_json()

        eventId = json['eventId']
        event = Event.query.filter_by(eventId=eventId).first()

        team = [member for member in json['team']]
        teamLeaderId = json['leader']

        if len(team) != len(set(team)):
            return jsonify({'ACK': 'FAILED', 'message': 'Duplicate entry in the team.'})

        if teamLeaderId not in team:
            return jsonify({'ACK': 'FAILED', 'message': 'Leader not from team'})

        for pecfestId in team:
            user = User.query.filter_by(pecfestId=pecfestId).first()
            if not user:
                return jsonify({'ACK': 'FAILED', 'message': 'Invalid members'})
            else:
                if user.verified == 0:
                    return jsonify({'ACK': 'FAILED', 'message': 'Some members are not verified.'})

        ## check whether users are already registered or not
        for pecfestId in team:
            reg = EventRegistration.query.filter_by(memberId=pecfestId, eventId=eventId).first()
            if reg:
                return jsonify({'ACK': 'FAILED', 'message': pecfestId + ' is already registered to this event.'})

        ## register this team in the database
        regs = []
        for pecfestId in team:
            reg = EventRegistration(
                eventId=eventId,
                memberId=pecfestId,
                leaderId=teamLeaderId)
            regs.append(reg)

        session = db.session
        success = False
        try:
            for reg in regs:
                session.add(reg)

            session.commit()
            success = True
        except Exception as err:
            session.rollback()
            session.flush()

        if success:
            return jsonify({'ACK': 'SUCCESS'})
        else:
            return jsonify({'ACK': 'FAILED'})
    except Exception as err:
        return jsonify({'ACK': 'FAILED', 'message': 'Some unknown error occurred.'})


################################################################

@app.route("/v1/start", methods=['POST'])
def start_regsitrations():
    global registrations_closed
    json = request.get_json()

    if 'pass' in json:
        if json['pass'] == 'pecfest':
            registrations_closed = False
            return jsonify({'ACK': 'SUCCESS'})

    return jsonify({'ACK': 'FAILED'})


@app.route("/v1/close", methods=['POST'])
def start_registrations():
    global registrations_closed
    json = request.get_json()

    if 'pass' in json:
        if json['pass'] == 'pecfest':
            registrations_closed = True
            return jsonify({'ACK': 'SUCCESS'})

    return jsonify({'ACK': 'FAILED'})


################################################################

if __name__ == '__main__':
    # For Digital Ocean
    app.run(host='0.0.0.0')

    # For Heroku
    # port = int(os.environ.get('PORT', 5000))
    # app.run(host='0.0.0.0', port=port)

    # For Local Host ( Over LAN )
    # app.run(debug=True, host="127.0.0.1", port=8080)
