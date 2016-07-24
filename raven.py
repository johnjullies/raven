import json
import requests
import tweepy
from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
from fuzzywuzzy import fuzz


# WEBFORM APP
SENDER_ADDRESS = '0409'
SMS_SENDER_ADDRESS = '9380'
LOCATION_SENDER_ADDRESS = '2708'
APP_ID = 'zxRKC5eX4XH9dcMa4LTXAeH4ExXoCjqe'
APP_SECRET = '380441e6afb36361eb8b0f391aa00c503dba369ab0fcb401896bf614c7e440c9'
CONSUMER_KEY = 'M4xXlecXHdcqzOR81col45gIM'
CONSUMER_SECRET = '4sAWowIfpB3DE22qFr31hKDQ2JO0lD2pwod0JTIG4MRh4MH18C'
ACCESS_TOKEN_KEY = '756726101037035520-U9fXICkjaQDD4i6Z5JVTEBA3DgGWb7f'
ACCESS_TOKEN_SECRET = '5XWImOc46ga9YPPqVY3u1ykyeTePW2ZVd3P9BfbPTSPwL'
GMAPS_API_KEY = 'AIzaSyCxOCkudbUXXUK3Fog9RTWAFNek8nES7c8'


app = Flask(__name__, static_url_path='/static')
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:@localhost/raven'
db = SQLAlchemy(app)


class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    access_token = db.Column(db.String(50))
    subscriber_number = db.Column(db.String(50))
    location_access_token = db.Column(db.String(50), default=None)
    location = db.Column(db.String(100), default=None)

    def __init__(self, access_token, subscriber_number, location_access_token, location):
        self.access_token = access_token
        self.subscriber_number = subscriber_number
        self.location_access_token = location_access_token
        self.location = location

    def __repr__(self):
        return '{"access_token":%s, "subscriber_number":%s, "location_access_token":%s, "location":%s}' % (self.access_token, self.subscriber_number, self.location_access_token, self.location)

class Advisory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    twitter_id = db.Column(db.String(30))
    advisory = db.Column(db.String(200))
    status = db.Column(db.Boolean)

    def __init__(self, twitter_id, advisory, status):
        self.twitter_id = twitter_id
        self.advisory = advisory
        self.status = status

    def __repr__(self):
        return '{"twitter_id":%s, "advisory":%s}' %(self.twitter_id, self.advisory)


def get_api(cfg):
    auth = tweepy.OAuthHandler(cfg['consumer_key'], cfg['consumer_secret'])
    auth.set_access_token(cfg['access_token'], cfg['access_token_secret'])
    return tweepy.API(auth)


def map_google_api(subscriber_number, latitude, longitude):
    resp = requests.get('https://maps.googleapis.com/maps/api/geocode/json?latlng=%s,%s&key=%s' %(latitude, longitude, GMAPS_API_KEY))
    lbs = resp.json()
    location = lbs['results'][0]['formatted_address']
    rows_changed = Subscription.query.filter_by(subscriber_number=subscriber_number).update(dict(location=location))
    db.session.commit()


def send_sms_from_twitter(twitter_id, warning_message, source):
    cfg = {
        'consumer_key': CONSUMER_KEY,
        'consumer_secret': CONSUMER_SECRET,
        'access_token': ACCESS_TOKEN_KEY,
        'access_token_secret': ACCESS_TOKEN_SECRET
    }
    api = get_api(cfg)

    for status in tweepy.Cursor(api.user_timeline, id=twitter_id).items(1):
        advisory = Advisory.query.filter_by(twitter_id=twitter_id).filter_by(advisory=status.text).first()

        if advisory:
            print(warning_message)
        else:
            rows_changed = Advisory.query.filter_by(twitter_id=twitter_id).update(dict(status=False))
            db.session.commit()

            advisory = Advisory(twitter_id, status.text, True)
            db.session.add(advisory)
            db.session.commit()

            subscription = Subscription.query.all()
            for subscriber in subscription:
                print('Sending message...')
                access_token = subscriber.access_token
                subscriber_number = subscriber.subscriber_number
                location = subscriber.location
                message = source + status.text
                data = {'address': '0'+subscriber_number, 'message': message}
                if fuzz.token_sort_ratio(location, status.text) > 20:
                    resp = requests.post('https://devapi.globelabs.com.ph/smsmessaging/v1/outbound/%s/requests?access_token=%s' %(SENDER_ADDRESS, access_token), data=data)
                    if resp.status_code == 400:
                        resp = requests.post('https://devapi.globelabs.com.ph/smsmessaging/v1/outbound/%s/requests?access_token=%s' %(SMS_SENDER_ADDRESS, access_token), data=data)
                    else:
                        print('Message not sent!')
                        break
                    print('Message sent!')


@app.route('/sendmessage')
def index():
    pagasa = '202890266'
    mmda = '171574926'
    raven = '756726101037035520'

    send_sms_from_twitter(pagasa, 'Stop: PAGASA Advisory already sent!', 'FROM PAGASA-DOST:\n\n')
    send_sms_from_twitter(raven, 'Stop: RAVEN Advisory already sent!', '')

    return '<p>SMS Service'


@app.route('/subscribe', methods=['GET', 'POST'])
def subscription():
    if request.args.get('code'):
        print('Webform Subscription')

        code = request.args.get('code')
        json = {'app_id': APP_ID, 'app_secret': APP_SECRET, 'code':code}
        resp = requests.post('http://developer.globelabs.com.ph/oauth/access_token', data=json)
        subscription_details = resp.json()
        print(subscription_details['access_token'])
        access_token = str(subscription_details['access_token'])
        subscriber_number = str(subscription_details['subscriber_number'])

        data = {'address': '0'+subscriber_number, 'message': 'If you want to subscribe to location based service of Raven. TEXT INFO TO 21582708.'}
        resp = requests.post('https://devapi.globelabs.com.ph/smsmessaging/v1/outbound/%s/requests?access_token=%s' %(SENDER_ADDRESS, access_token), data=data)

        subscriber = Subscription(access_token, subscriber_number, None, None)
        db.session.add(subscriber)
        db.session.commit()

    else:
        print('Webform Unsubscription')
        unsubscribed = request.json
        access_token = unsubscribed['unsubscribed']['access_token']
        unsubscription = Subscription.query.filter_by(access_token=access_token).first()
        db.session.delete(unsubscription)
        db.session.commit()

    return render_template('base.html'), 200


@app.route('/subscribesms', methods=['GET', 'POST'])
def sms_subscription():
    if request.args.get('access_token'):
        print('SMS Subscription')
        access_token = request.args.get('access_token')
        subscriber_number = request.args.get('subscriber_number')

        data = {'address': '0'+subscriber_number, 'message': 'If you want to subscribe to location based service of Raven. TEXT INFO TO 21582708.'}
        resp = requests.post('https://devapi.globelabs.com.ph/smsmessaging/v1/outbound/%s/requests?access_token=%s' %(SMS_SENDER_ADDRESS, access_token), data=data)

        subscriber = Subscription(access_token, subscriber_number, None, None)
        db.session.add(subscriber)
        db.session.commit()

    else:
        print('SMS Unsubscription')
        unsubscribed = request.json
        access_token = unsubscribed['unsubscribed']['access_token']
        unsubscription = Subscription.query.filter_by(access_token=access_token).first()
        db.session.delete(unsubscription)
        db.session.commit()

    return render_template('base.html'), 200


@app.route('/notification', methods=['GET', 'POST'])
def sms_notification():
    inbound_sms = request.json
    datetime = inbound_sms['inboundSMSMessageList']['inboundSMSMessage'][0]['dateTime']
    destination_address = inbound_sms['inboundSMSMessageList']['inboundSMSMessage'][0]['destinationAddress']
    message_id = inbound_sms['inboundSMSMessageList']['inboundSMSMessage'][0]['messageId']
    message = inbound_sms['inboundSMSMessageList']['inboundSMSMessage'][0]['message']
    resource_url = inbound_sms['inboundSMSMessageList']['inboundSMSMessage'][0]['resourceURL']
    sender_address = inbound_sms['inboundSMSMessageList']['inboundSMSMessage'][0]['senderAddress']

    return render_template('base.html'), 200

@app.route('/locate', methods=['GET', 'POST'])
def subscribe_location():
    access_token = request.args.get('access_token')
    subscriber_number = request.args.get('subscriber_number')
    rows_changed = Subscription.query.filter_by(subscriber_number=subscriber_number).update(dict(location_access_token=access_token))
    db.session.commit()
    return '<p>Location Based Function'

@app.route('/getlocation', methods=['GET', 'POST'])
def get_location():
    subscription = Subscription.query.all()
    for subscriber in subscription:
        access_token = subscriber.location_access_token
        subscriber_number = subscriber.subscriber_number
        resp = requests.get('https://devapi.globelabs.com.ph/location/v1/queries/location?access_token=%s&address=%s&requestedAccuracy=100' %(access_token, subscriber_number))
        lbs = resp.json()
        try:
            latitude = lbs['terminalLocationList']['terminalLocation']['currentLocation']['latitude']
            longitude = lbs['terminalLocationList']['terminalLocation']['currentLocation']['longitude']
            map_url = lbs['terminalLocationList']['terminalLocation']['currentLocation']['map_url']
            print(latitude)
            print(longitude)
            print(map_url)
            map_google_api(subscriber_number, latitude, longitude)
        except KeyError as e:
            print('%s is not subscribed to the Location-Based Service.' )

        '''terminalLocationList": {
            "terminalLocation": {
                  "address": "tel:9171234567",
                  "currentLocation": {
                    "accuracy": 100,
                    "latitude": "14.5609722",
                    "longitude": "121.0193394",
                    "map_url": "http://maps.google.com/maps?z=17&t=m&q=loc:14.5609722+121.0193394",
                    "timestamp": "Fri Jun 06 2014 09:25:15 GMT+0000 (UTC)"
                  },
            "locationRetrievalStatus": "Retrieved"
            }
          }
        }'''
    return '<p>Get Location'


@app.route('/', methods=['GET', 'POST'])
def landing():
    return render_template('index.html'), 200

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    return render_template('signup.html'), 200


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
