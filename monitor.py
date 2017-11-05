from acitoolkit import Session, Credentials, Subscriber, BaseACIObject, ConcreteBD


from ucsmsdk.ucshandle import UcsHandle
import websocket
import thread
import time
import json

from ucs import do_cool_shit, undo_cool_shit
from aci import (get_vlan_number_from_dn,
                 get_port_from_lldp_dn,
                 get_port_from_pathdn,
                 get_node_id_from_dn)

import config


class VlanBinding(BaseACIObject):

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by this acitoolkit class.
        :returns: list of strings containing APIC class names
        """
        return ['l2RsPathDomAtt']

    @classmethod
    def get_event(cls, session):
        """
        Gets the event that is pending for this class.  Events are
        returned in the form of objects.  Objects that have been deleted
        are marked as such.

        :param session:  the instance of Session used for APIC communication
        """
        urls = cls._get_subscription_urls()
        for url in urls:
            if not session.has_events(url):
                continue
            event = session.get_event(url)
            for class_name in cls._get_apic_classes():
                if class_name in event['imdata'][0]:
                    break
            attributes = event['imdata'][0][class_name]['attributes']
            return attributes
            # dn = str(attributes['dn'])
            # parent = cls._get_parent_from_dn(cls._get_parent_dn(dn))
            # if status == 'created':
            #     name = str(attributes['name'])
            # else:
            #     name = cls._get_name_from_dn(dn)
            # obj = cls(name, parent=parent)
            # obj._populate_from_attributes(attributes)
            # if status == 'deleted':
            #     obj.mark_as_deleted()
            # return obj

    # @staticmethod
    # def _get_name_dn_delimiters():
    #     return ['/node-', '/']


    # @staticmethod
    # def _get_parent_class():
    #     """
    #     Gets the acitoolkit class of the parent object
    #     Meant to be overridden by inheriting classes.
    #     Raises exception if not overridden.
    #     :returns: class of parent object
    #     """
    #     return ConcreteBD

# def on_message(ws, message):
#     msg = json.loads(message)
#
#     print "received message from websocket on subscription {}: {}".format(msg["subscriptionId"], msg['imdata'])
#     for i in msg['imdata']:
#         # handle create
#         if i['l2RsPathDomAtt']['attributes']['status'] == 'created':
#             if 'vlan-' in i['l2RsPathDomAtt']['attributes']['dn']:
#                 dn = i['l2RsPathDomAtt']['attributes']['dn']
#                 vlan_number = get_vlan_number_from_dn(dn)
#                 node = get_node_id_from_dn(dn)
#                 port = get_port_from_pathdn(dn)
#                 ucsm_ip = topology[node][port]
#                 ucsm_ip = config.UCSM_VIP_MAP[ucsm_ip]
#                 print("We will provision on {}".format(ucsm_ip))
#                 handle = UcsHandle(ucsm_ip, config.UCSM_LOGIN, config.UCSM_PASSWORD)
#                 handle.login()
#                 do_cool_shit(handle, vlan_number)
#                 handle.logout()
#
#         # reverse
#         elif i['l2RsPathDomAtt']['attributes']['status'] == 'deleted':
#             if 'vlan-' in i['l2RsPathDomAtt']['attributes']['dn']:
#                 dn = i['l2RsPathDomAtt']['attributes']['dn']
#                 print('deleting {}'.format(dn))
#                 vlan_number = get_vlan_number_from_dn(dn)
#                 node = get_node_id_from_dn(dn)
#                 port = get_port_from_pathdn(dn)
#                 ucsm_ip = topology[node][port]
#                 ucsm_ip = config.UCSM_VIP_MAP[ucsm_ip]
#
#                 print("We will de-provision on {}".format(ucsm_ip))
#                 handle = UcsHandle(ucsm_ip, config.UCSM_LOGIN, config.UCSM_PASSWORD)
#                 handle.login()
#                 undo_cool_shit(handle, vlan_number)
#                 handle.logout()
#
# def on_error(ws, error):
#     print error
#
#
# def on_close(ws):
#     print "### closed ###"
#
#
# def on_open(ws):
#     print "### opening websocket ###"
#
#     def run(*args):
#         for i in range(30000):
#             time.sleep(1)
#             ws.send("Hello %d" % i)
#         time.sleep(1)
#         ws.close()
#         print "thread terminating..."
#     thread.start_new_thread(run, ())
#

if __name__ == "__main__":
    description = 'Argus'

    # Gather credentials for ACI toolkit
    creds = Credentials('apic', description)
    args = creds.get()

    # Establish an API session to the APIC
    session = Session(args.url, args.login, args.password)

    if session.login().ok:
        print("Connected to ACI")


    # Discover topology
    lldp_adj = session.get('/api/class/lldpAdjEp.json').json()['imdata']
    topology = dict()
    for adj in lldp_adj:
        node = get_node_id_from_dn(adj['lldpAdjEp']['attributes']['dn'])
        if node not in topology.keys():
            topology[node] = dict()

        port = get_port_from_lldp_dn(adj['lldpAdjEp']['attributes']['dn'])
        mgmt_ip = adj['lldpAdjEp']['attributes']['mgmtIp']
        topology[node][port] = mgmt_ip

    for adj in lldp_adj:
        node = get_node_id_from_dn(adj['lldpAdjEp']['attributes']['dn'])
        port = get_port_from_lldp_dn(adj['lldpAdjEp']['attributes']['dn'])
        mgmt_ip = adj['lldpAdjEp']['attributes']['mgmtIp']
        topology[(node, port)] = mgmt_ip

    # Create a websocket
    # ws = websocket.WebSocketApp("ws://{}/socket{}".format(session.ipaddr, session.token),
    #                             on_message=on_message,
    #                             on_error=on_error,
    #                             on_close=on_close)
    # subscription = session.get('/api/class/l2RsPathDomAtt.json?subscription=yes')
    # if subscription.ok:
    #     print subscription.text
    #     # blocking function to listen for messages on our websocket
    #     print("Waiting for events...")
    #     ws.run_forever()

    print("Creating subscription to ACI fabric")
    print("=" * 80)

    VlanBinding.subscribe(session)

    while True:
        if VlanBinding.has_events(session):
            binding = VlanBinding.get_event(session)
            if binding['status'] == 'deleted':
                if 'vlan-' in binding['dn']:
                    dn = binding['dn']
                    try:
                        print('deleting {}'.format(dn))
                        vlan_number = get_vlan_number_from_dn(dn)
                        node = get_node_id_from_dn(dn)
                        port = get_port_from_pathdn(dn)
                        ucsm_ip = topology[node][port]
                        ucsm_ip = config.UCSM_VIP_MAP[ucsm_ip]

                        print("We will de-provision on {}".format(ucsm_ip))
                        handle = UcsHandle(ucsm_ip, config.UCSM_LOGIN, config.UCSM_PASSWORD)
                        handle.login()
                        undo_cool_shit(handle, vlan_number)
                        handle.logout()
                    except UnboundLocalError as e:
                        print "could not derive mod/port from binding message"

                    except Exception as e:
                        print "Unhandled Exception {}".format(e)


            elif binding['status'] == 'created':
                print 'created'
                if 'vlan-' in binding['dn']:
                    dn = binding['dn']
                    try:
                        print('deleting {}'.format(dn))
                        vlan_number = get_vlan_number_from_dn(dn)
                        node = get_node_id_from_dn(dn)
                        port = get_port_from_pathdn(dn)
                        ucsm_ip = topology[node][port]
                        ucsm_ip = config.UCSM_VIP_MAP[ucsm_ip]

                        print("We will de-provision on {}".format(ucsm_ip))
                        handle = UcsHandle(ucsm_ip, config.UCSM_LOGIN, config.UCSM_PASSWORD)
                        handle.login()
                        do_cool_shit(handle, vlan_number)
                        handle.logout()

                    except UnboundLocalError as e:
                        print "could not derive mod/port from binding message"

                    except Exception as e:
                        print "Unhandled Exception {}".format(e)

            else:
                print "should only see this at bootup: {}".format(binding)

