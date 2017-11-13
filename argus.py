import os
import json
import requests
import datetime
from acitoolkit import Session, Credentials
from ucsmsdk.ucshandle import UcsHandle
from ucs import ManagedUCS # provision_ucs_pod, deprovision_ucs_pod, get_vlan_id_by_name
from aci import VlanBinding, ManagedTopology, PortGroup, fixup_epg_name, get_bindings_for_lsnode
from utils import run_async
import yaml

import config

HEADERS = {"Content-Type": "application/json"}

def full_sync():

    print("Validating existing ACI bindings are provisioned in UCS")

    existing_bindings = VlanBinding.get(apic, topology=topology, vip_map=config.UCSM_VIP_MAP)
    for ucs in config.UCS.keys():
        print "Synchronizing Existing bindings for UCS pod {}".format(ucs)
        ucsm = ManagedUCS(ucs, config.UCSM_LOGIN, config.UCSM_PASSWORD)
        ucsm.login()
        bindings = [b for b in existing_bindings if b.ucsm == ucs]

        # all ACI vlans which are provisioned
        aci_vlans = set([b.vlan for b in bindings])

        # all vlans provisioned on this UCS pod
        ucs_vlans = set([v.id for v in ucsm.get_vlans()])

        # we are only concerned about ucs_vlans which are part of the dvs
        ucs_vlans = ucs_vlans.intersection(dvs_vlans)

        # vlans that exist in ACI but not in UCS and must be provisioned
        missing_vlans = aci_vlans.difference(ucs_vlans)
        print "Need to provision {}".format(missing_vlans)
        for v in missing_vlans:
            try:
                epg = port_groups_by_vlan[v]
                print("Adding {}".format(epg))
                ucsm.provision_portgroup(epg, v)
            except KeyError:
                print("Skipping {} as we were unable to determine port-group".format(v))

        # verify that all aci_vlans exist in the vlan group
        vlan_group_members = ucsm.get_vlan_group_members()
        vlan_group_members = set([v.name for v in vlan_group_members])

        print("VLAN group members {}".format(vlan_group_members))
        expected_group_members = set(map(lambda x : ucsm.ucs_name_from_portgroup(x),
                                     [port_groups_by_vlan[v] for v in aci_vlans]))
        print("Expected Group members {}".format(expected_group_members))
        print port_groups_by_name.keys()
        if not expected_group_members == vlan_group_members:
            print("Group Membership is out of sync")
            missing_group_members = expected_group_members.difference(vlan_group_members)
            print("Missing Group Members {}".format(missing_group_members))
            for pg in missing_group_members:
                ucsm.add_vlan_to_group(ManagedUCS.ucs_name_from_portgroup(pg))
            extra_group_members = vlan_group_members.difference(expected_group_members)
            extra_group_members = [pg for pg in extra_group_members if pg in port_groups_by_name.keys()]
            print("Extra Group Members {}".format(extra_group_members))
            for member in extra_group_members:
                ucsm.remove_vlan_from_group(member)

        # vlans that exist in ucs but not in ACI
        extra_vlans = ucs_vlans.difference(aci_vlans)
        # vlan id 1 cannot be removed from UCS
        extra_vlans.discard('1')
        print "Need to de-provision {}".format(extra_vlans)
        for v in extra_vlans:
            epg = port_groups_by_vlan[v]
            print("Removing {}".format(epg))
            ucsm.deprovision_portgroup(epg, v)

        # logout
        ucsm.logout()


@run_async
def binding_event_handler(session, epg, binding):
    # create/delete events
    if 'vlan-' in binding.dn and binding.node and binding.port:
        print("Checking for UCS chassis on {} port {}: ".format(binding.node, binding.port)),
        try:
            ucsm_ip = config.UCSM_VIP_MAP[topology[binding.node][binding.port]]
        except KeyError:
            ucsm_ip = None

        if ucsm_ip:
            print("Found UCSM on {}".format(ucsm_ip))
            send_event(binding.status, epg.name, binding.node, binding.port, binding.vlan, ucsm_ip)
            ucsm = ManagedUCS(ucsm_ip, config.UCSM_LOGIN, config.UCSM_PASSWORD)
            ucsm.login()

            if binding.status == 'created':
                print("Adding {} to {}".format(epg.name, ucsm_ip))
                ucsm.provision_portgroup(epg.name, binding.vlan)
            elif binding.status == 'deleted':
                print("Removing {} from {}".format(epg.name, ucsm_ip))
                ucsm.deprovision_portgroup(epg.name, binding.vlan)
                #deprovision_ucs_pod(handle, epg.name, binding.vlan)
            else:
                print("Existing Binding - Verifying {} has {} provisoned".format(ucsm_ip, binding.vlan))
                #provision_ucs_pod(handle, epg.name, binding.vlan)
            ucsm.logout()

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
    print("Collecting Topology Information")
    topology = ManagedTopology.get(apic, config.UCSM_VIP_MAP)

    print("Gathering DVS information")
    # these objects are referenced to ensure we only operate against DVS vlans/portgroups
    port_groups = PortGroup.get(apic)
    port_groups_by_vlan = dict()
    port_groups_by_name = dict()
    for item in port_groups:
        # normalize portgroup name
        item.name = ManagedUCS.ucs_name_from_portgroup(item.name)
        port_groups_by_name[item.name] = item.vlan
        port_groups_by_vlan[item.vlan] = item.name
    dvs_vlans = set([v.vlan for v in port_groups])

    full_sync()

    last_full_sync = datetime.datetime.now()

    print("Creating subscription to ACI fabric")
    print("=" * 80)
    subscription = VlanBinding.subscribe(apic, only_new=True)

    while True:
        if VlanBinding.has_events(apic):
            binding = VlanBinding.get_event(apic)
            # Determine if it's already provisioned
            already_provsioned = False
            epg = PortGroup.get(apic, encap=binding.vlan)

            if not already_provsioned:
                binding_event_handler(apic, epg, binding)

        #Run garbage collection periodically
        if config.GARBAGE_COLLECTION_INTERVAL:
            # if config.GARBAGE_COLLECTION_INTERVAL < 15:
            #     config.GARBAGE_COLLECTION_INTERVAL = 15
            #
            delta = datetime.datetime.now() - last_full_sync
            if delta > datetime.timedelta(minutes=config.GARBAGE_COLLECTION_INTERVAL):
                full_sync()
                last_full_sync = datetime.datetime.now()
