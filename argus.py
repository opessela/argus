import os
import json
import requests

from acitoolkit import Session, Credentials, Subscriber, BaseACIObject, ConcreteBD
from ucsmsdk.ucshandle import UcsHandle
from ucs import provision_ucs_pod, deprovision_ucs_pod
from aci import *
from utils import run_async
import config

HEADERS = {"Content-Type": "application/json"}

@run_async
def send_event(action, node, port, vlan, ucsm):
    argus_api = os.getenv("ARGUS_BASE_API") + '/events'
    data = {
        "action": action,
        "vlan": vlan,
        "node": node,
        "port": port,
        "ucsm": ucsm
        }
    resp = requests.post(argus_api, headers=HEADERS, data=json.dumps(data))
    if not resp.ok:
        print "Error contacting API: {}".format(resp.status_code)


if __name__ == "__main__":
    description = 'Argus'

    # Gather credentials for ACI toolkit
    creds = Credentials('apic', description)
    args = creds.get()

    # Establish an API session to the APIC
    apic = Session(args.url, args.login, args.password)

    if apic.login().ok:
        print("Connected to ACI")



    topology = get_topology(apic)

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

                        send_event(binding['status'], node, port, vlan_number, ucsm_ip)
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
                        send_event(binding['status'], node, port, vlan_number, ucsm_ip)

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
