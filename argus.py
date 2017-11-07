import os
import json
import requests

from acitoolkit import Session, Credentials, Subscriber, BaseACIObject, ConcreteBD
from ucsmsdk.ucshandle import UcsHandle
from ucs import provision_ucs_pod, deprovision_ucs_pod
from aci import VlanBinding, Topology, PortGroup
from utils import run_async
import config

HEADERS = {"Content-Type": "application/json"}

@run_async
def binding_event_handler(session, binding):
    if binding.status:
        # create/delete events
        epg = PortGroup.get(session, encap=binding.vlan)
        print "Got {} notification for {} using encap {}".format(binding.status, epg, binding.vlan)
        if 'vlan-' in binding.dn and binding.node and binding.port:
            print("Checking for UCS chassis on {} port {}: ".format(binding.node, binding.port)),
            ucsm_ip = config.UCSM_VIP_MAP[topology[binding.node][binding.port]]
            if ucsm_ip:
                print("Found UCSM on {}".format(ucsm_ip))
                send_event(binding.status, epg.name, binding.node, binding.port, binding.vlan, ucsm_ip)
                handle = UcsHandle(ucsm_ip, config.UCSM_LOGIN, config.UCSM_PASSWORD)
                handle.login()

                if binding.status == 'created':
                    print("Adding {} to {}".format(epg.name, ucsm_ip))
                    provision_ucs_pod(handle, epg.name, binding.vlan)
                elif binding.status == 'deleted':
                    print("Removing {} from {}".format(epg.name, ucsm_ip))
                    deprovision_ucs_pod(handle, epg.name, binding.vlan)
                handle.logout()
            else:
                print("None Found")

    else:
        print "should only see this at startup: {}".format(binding.dn)


@run_async
def send_event(action, epg, node, port, vlan, ucsm):
    argus_api = os.getenv("ARGUS_BASE_API") + '/events'
    data = {
        "action": action,
        "epg": epg,
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

    topology = Topology.get(apic)

    print("Creating subscription to ACI fabric")
    print("=" * 80)

    VlanBinding.subscribe(apic, only_new=True)

    while True:
        if VlanBinding.has_events(apic):
            binding = VlanBinding.get_event(apic)
            binding_event_handler(apic, binding)

