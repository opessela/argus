from acitoolkit import Session, Credentials, Subscriber, BaseACIObject, ConcreteBD
from ucsmsdk.ucshandle import UcsHandle
import websocket
import thread
import time
import json
from ucs import provision_ucs_pod, deprovision_ucs_pod
from aci import *

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


if __name__ == "__main__":
    description = 'Argus'

    # Gather credentials for ACI toolkit
    creds = Credentials('apic', description)
    args = creds.get()

    # Establish an API session to the APIC
    apic = Session(args.url, args.login, args.password)

    if apic.login().ok:
        print("Connected to ACI")

    # Discover topology
    lldp_adj = apic.get('/api/class/lldpAdjEp.json').json()['imdata']
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

    print("Creating subscription to ACI fabric")
    print("=" * 80)

    VlanBinding.subscribe(apic)

    while True:
        if VlanBinding.has_events(apic):
            binding = VlanBinding.get_event(apic)
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
                        deprovision_ucs_pod(handle, vlan_number)
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
                        provision_ucs_pod(handle, vlan_number)
                        handle.logout()

                    except UnboundLocalError as e:
                        print "could not derive mod/port from binding message"

                    except Exception as e:
                        print "Unhandled Exception {}".format(e)

            else:
                print "should only see this at bootup: {}".format(binding)
