from twisted.internet import task
from twisted.internet import reactor
import requests

timeout = 3600 # 1 hour

def doWork():
    resp = requests.get('https://2363c32a.ngrok.io/getlocation')

l = task.LoopingCall(doWork)
l.start(timeout) # call every sixty seconds

reactor.run()
