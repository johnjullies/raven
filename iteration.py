from twisted.internet import task
from twisted.internet import reactor
import requests

timeout = 150.0 # 150 seconds

def doWork():
    resp = requests.get('https://2363c32a.ngrok.io/sendmessage')

l = task.LoopingCall(doWork)
l.start(timeout) # call every sixty seconds

reactor.run()
