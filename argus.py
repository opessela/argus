import os
import json
import requests
import datetime
from acitoolkit import Session, Credentials
from ucsmsdk.ucshandle import UcsHandle
from ucs import provision_ucs_pod, deprovision_ucs_pod, get_vlan_id_by_name
from aci import VlanBinding, ManagedTopology, PortGroup, fixup_epg_name
from utils import run_async

import config

HEADERS = {"Content-Type": "application/json"}


def perform_garbage_collection():
    """
    periodically ran to ensure that no unused vlans are provisioned on UCS domains
    Returns:

    """
    print("Starting Garbage Collection...")
    print("Gathering DVS information")
    port_groups = PortGroup.get(apic)
    port_groups_by_vlan = dict()
    port_groups_by_name = dict()
    for item in port_groups:
        port_groups_by_name[item.name.replace('|', config.DELIMTER)] = item.vlan
        port_groups_by_vlan[item.vlan] = item.name.replace('|', config.DELIMTER)

    print("Retrieving UCS configuration")
    provisioned_vlans = dict()
    for vip in config.UCS.keys():

        handle = UcsHandle(vip, config.UCSM_LOGIN, config.UCSM_PASSWORD)
        handle.login()
        members = handle.query_children(in_dn=config.VLAN_GROUP_DN, class_id='FabricPooledVlan')
        epgs = [vlan.name for vlan in members]
        provisioned_vlans[vip] = epgs

        fis = config.UCS[vip]
        vlans = epgs
        for fi_mgmt_ip in fis.values():
            bindings_for_fi = get_bindings_for_fi(apic, fi_mgmt_ip)
            print("Reconciling vlans {} with {}".format(vlans, bindings_for_fi))
            for vlan in vlans:
                print vlan
                vlan_dn = fixup_epg_name(vlan[-32:])

                if vlan_dn is not None:

                    is_valid = False
                    for b in bindings_for_fi:
                        if vlan_dn in b['fvDyPathAtt']['attributes']['dn']:
                            is_valid = True
                    if is_valid:
                        print "VLAN {} has active bindings, leaving it alone".format(vlan)
                    else:
                        vlan_id = get_vlan_id_by_name(handle, vlan)
                        print "We should probably delete vlan {} encap {}".format(vlan, vlan_id)
                        deprovision_ucs_pod(handle, vlan, vlan_id)


        handle.logout()
        print("Garbage Collection Completed")

def get_bindings_for_fi(session, fi):
    url = '/api/node/class/fvDyPathAtt.json?query-target-filter=' \
          'and(eq(fvDyPathAtt.targetDn,"topology/pod-1/node-102/sys/lsnode-{}"))'.format(fi)
    resp = session.get(url)
    return resp.json()['imdata']

@run_async
def binding_event_handler(session, epg, binding):
#    if binding.status:
    # create/delete events
    print "Got {} notification for {} using encap {}".format(binding.status, epg, binding.vlan)
    if 'vlan-' in binding.dn and binding.node and binding.port:
        print("Checking for UCS chassis on {} port {}: ".format(binding.node, binding.port)),
        try:
            ucsm_ip = config.UCSM_VIP_MAP[topology[binding.node][binding.port]]
        except KeyError:
            ucsm_ip = None

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
            else:
                print("Existing Binding - Verifying {} has {} provisoned".format(ucsm_ip, binding.vlan))
                provision_ucs_pod(handle, epg.name, binding.vlan)
            handle.logout()

        else:
            print("None Found")

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
    topology = ManagedTopology.get(apic, config.UCSM_VIP_MAP)

    existing_bindings = VlanBinding.get(apic)
    print("Validating existing ACI bindings are provisioned in UCS")

    print existing_bindings
    for b in existing_bindings:
        epg = PortGroup.get(apic, encap=b.vlan)
        binding_event_handler(apic, epg, b)

    perform_garbage_collection()
    last_garbage_collection = datetime.datetime.now()

    print("Creating subscription to ACI fabric")
    print("=" * 80)
    subscription = VlanBinding.subscribe(apic)


    while True:
        if VlanBinding.has_events(apic):
            binding = VlanBinding.get_event(apic)
            # Determine if it's already provisioned
            already_provsioned = False
            epg = PortGroup.get(apic, encap=binding.vlan)

            if not already_provsioned:
                binding_event_handler(apic, epg, binding)

        # Run garbage collection periodically
        if config.GARBAGE_COLLECTION_INTERVAL:
            if config.GARBAGE_COLLECTION_INTERVAL < 15:
                config.GARBAGE_COLLECTION_INTERVAL = 15
            delta = datetime.datetime.now() - last_garbage_collection
            if delta > datetime.timedelta(minutes=config.GARBAGE_COLLECTION_INTERVAL):
                perform_garbage_collection()
                last_garbage_collection = datetime.datetime.now()