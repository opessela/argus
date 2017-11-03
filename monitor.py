from acitoolkit import Session, Credentials
from ucsmsdk.ucshandle import UcsHandle
import websocket
import thread
import time
import json

from ucs import do_cool_shit, undo_cool_shit
from aci import get_vlan_number_from_dn

import config


def on_message(ws, message):
    msg = json.loads(message)

    print "received message from websocket on subscription {}: {}".format(msg["subscriptionId"], msg['imdata'])
    for i in msg['imdata']:
        # handle create
        if i['l2RsPathDomAtt']['attributes']['status'] == 'created':
            if 'vlan-' in i['l2RsPathDomAtt']['attributes']['dn']:
                dn = i['l2RsPathDomAtt']['attributes']['dn']
                vlan_number = get_vlan_number_from_dn(dn)
                do_cool_shit(handle, vlan_number)

        # reverse
        elif i['l2RsPathDomAtt']['attributes']['status'] == 'deleted':
            if 'vlan-' in i['l2RsPathDomAtt']['attributes']['dn']:
                dn = i['l2RsPathDomAtt']['attributes']['dn']
                print('deleting {}'.format(dn))
                vlan_number = get_vlan_number_from_dn(dn)
                undo_cool_shit(handle, vlan_number)


def on_error(ws, error):
    print error


def on_close(ws):
    print "### closed ###"


def on_open(ws):
    print "### opening websocket ###"

    def run(*args):
        for i in range(30000):
            time.sleep(1)
            ws.send("Hello %d" % i)
        time.sleep(1)
        ws.close()
        print "thread terminating..."
    thread.start_new_thread(run, ())


if __name__ == "__main__":
    description = 'Argus'

    # Gather credentials for ACI toolkit
    creds = Credentials('apic', description)
    args = creds.get()

    # Establish an API session to the APIC
    session = Session(args.url, args.login, args.password)

    if session.login().ok:
        print("Connected to ACI")

    handle = UcsHandle(config.UCSM_IP, config.UCSM_LOGIN, config.UCSM_PASSWORD)
    handle.login()

    # Create a websocket
    ws = websocket.WebSocketApp("ws://{}/socket{}".format(session.ipaddr, session.token),
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)

    print("Creating subscription to ACI fabric")
    print("=" * 80)

    subscription = session.get('/api/class/l2RsPathDomAtt.json?subscription=yes')
    if subscription.ok:
        print subscription.text
        # blocking function to listen for messages on our websocket
        print("Waiting for events...")
        ws.run_forever()
