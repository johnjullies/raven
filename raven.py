import json
import requests
import tweepy
from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy


# WEBFORM APP
SENDER_ADDRESS = '0409'
APP_ID = 'zxRKC5eX4XH9dcMa4LTXAeH4ExXoCjqe'
APP_SECRET = '380441e6afb36361eb8b0f391aa00c503dba369ab0fcb401896bf614c7e440c9'
CONSUMER_KEY = 'M4xXlecXHdcqzOR81col45gIM'
CONSUMER_SECRET = '4sAWowIfpB3DE22qFr31hKDQ2JO0lD2pwod0JTIG4MRh4MH18C'
ACCESS_TOKEN_KEY = '756726101037035520-U9fXICkjaQDD4i6Z5JVTEBA3DgGWb7f'
ACCESS_TOKEN_SECRET = '5XWImOc46ga9YPPqVY3u1ykyeTePW2ZVd3P9BfbPTSPwL'


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:@localhost/raven'
db = SQLAlchemy(app)


class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    access_token = db.Column(db.String(50))
    subscriber_number = db.Column(db.String(50))

    def __init__(self, access_token, subscriber_number):
        self.access_token = access_token
        self.subscriber_number = subscriber_number

    def __repr__(self):
        return '{"access_token":%s, "subscriber_number":%s}' % (self.access_token, self.subscriber_number)

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


def unsubscription(access_token, subscriber_number):
    print('unsubscribe successfully')


def get_api(cfg):
    auth = tweepy.OAuthHandler(cfg['consumer_key'], cfg['consumer_secret'])
    auth.set_access_token(cfg['access_token'], cfg['access_token_secret'])
    return tweepy.API(auth)


@app.route('/')
def index():
    pagasa = '202890266'
    mmda = '171574926'
    raven = '756726101037035520'

    cfg = {
        'consumer_key': CONSUMER_KEY,
        'consumer_secret': CONSUMER_SECRET,
        'access_token': ACCESS_TOKEN_KEY,
        'access_token_secret': ACCESS_TOKEN_SECRET
    }
    api = get_api(cfg)

    for status in tweepy.Cursor(api.user_timeline, id=pagasa).items(1):
        advisory = Advisory.query.filter_by(twitter_id=pagasa).filter_by(advisory=status.text).first()

        if advisory:
            print('Stop: PAGASA Advisory already sent!')
        else:
            rows_changed = Advisory.query.filter_by(twitter_id=pagasa).update(dict(status=False))
            db.session.commit()

            advisory = Advisory(pagasa, status.text, True)
            db.session.add(advisory)
            db.session.commit()

            subscription = Subscription.query.all()
            for subscriber in subscription:
                access_token = subscriber.access_token
                subscriber_number = subscriber.subscriber_number
                data = {'address': '0'+subscriber_number, 'message': 'From PAGASA-DOST:\n\n' + status.text}
                resp = requests.post('https://devapi.globelabs.com.ph/smsmessaging/v1/outbound/%s/requests?access_token=%s' %(SENDER_ADDRESS, access_token), data=data)

    for status in tweepy.Cursor(api.user_timeline, id=mmda).items(1):
        advisory = Advisory.query.filter_by(twitter_id=mmda).filter_by(advisory=status.text).first()

        if advisory:
            print('Stop: MMDA Advisory already sent!')
        else:
            rows_changed = Advisory.query.filter_by(twitter_id=mmda).update(dict(status=False))
            db.session.commit()

            advisory = Advisory(mmda, status.text, True)
            db.session.add(advisory)
            db.session.commit()

            subscription = Subscription.query.all()
            for subscriber in subscription:
                access_token = subscriber.access_token
                subscriber_number = subscriber.subscriber_number
                data = {'address': '0'+subscriber_number, 'message': 'From Official MMDA:\n\n' + status.text}
                resp = requests.post('https://devapi.globelabs.com.ph/smsmessaging/v1/outbound/%s/requests?access_token=%s' %(SENDER_ADDRESS, access_token), data=data)

    for status in tweepy.Cursor(api.user_timeline, id=raven).items(1):
        advisory = Advisory.query.filter_by(twitter_id=mmda).filter_by(advisory=status.text).first()

        if advisory:
            print('Stop: Raven Advisory already sent!')
        else:
            rows_changed = Advisory.query.filter_by(twitter_id=raven).update(dict(status=False))
            db.session.commit()

            advisory = Advisory(raven, status.text, True)
            db.session.add(advisory)
            db.session.commit()

            subscription = Subscription.query.all()
            for subscriber in subscription:
                access_token = subscriber.access_token
                subscriber_number = subscriber.subscriber_number
                data = {'address': '0'+subscriber_number, 'message': status.text}
                resp = requests.post('https://devapi.globelabs.com.ph/smsmessaging/v1/outbound/%s/requests?access_token=%s' %(SENDER_ADDRESS, access_token), data=data)        


    return '<p>%s</p>' %('Complete')


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

        subscriber = Subscription(access_token, subscriber_number)
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

        subscriber = Subscription(access_token, subscriber_number)
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


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
