from ucsmsdk.ucshandle import UcsHandle
from ucsmsdk.mometa.fabric.FabricVlan import FabricVlan
from ucsmsdk.mometa.fabric.FabricEthVlanPc import FabricEthVlanPc
from ucsmsdk.mometa.vnic.VnicEtherIf import VnicEtherIf
from ucsmsdk.mometa.vnic.VnicLanConnTempl import VnicLanConnTempl
from ucsmsdk.mometa.fabric.FabricNetGroup import FabricNetGroup
from ucsmsdk.mometa.fabric.FabricPooledVlan import FabricPooledVlan
from ucsmsdk.ucsexception import UcsException
import config

def add_vlan(handle, vlan_id, name):
    mo = FabricVlan(parent_mo_or_dn="fabric/lan",
                    sharing="none",
                    name=name, id=vlan_id)
    try:
        handle.add_mo(mo)
        handle.commit()
        return mo
    except UcsException as e:
        print e

def remove_vlan(handle, vlan_id, name):
    mo = FabricVlan(parent_mo_or_dn="fabric/lan",
                    sharing="none",
                    name=name, id=vlan_id)
    try:
        handle.remove_mo(mo)
        handle.commit()
    except UcsException as e:
        print e

    return mo

def undo_cool_shit(handle, vlan_number):
    vlan_name = config.OBJECT_PREFIX.format(vlan_number)
    dn = 'fabric/lan/net-group-DVS-01/net-{}'.format(vlan_name)
    mo = handle.query_dn(dn)
    if mo:
        print "attempting to delete DN: {}".format(dn)
        handle.remove_mo(mo)
        handle.commit()
        remove_vlan(handle, vlan_number, vlan_name)
    else:
        print "Could not find, likely already cleaned up from previous link"


def do_cool_shit(handle, vlan_number):
    # TODO remove constant
    vlan_name = config.OBJECT_PREFIX.format(vlan_number)

    # Add vlan globally
    add_vlan(handle, vlan_number, vlan_name)

    # this works, moving to groups now
    # uplink1 = FabricEthVlanPc(vlan, 'B', '4')
    # handle.add_mo(uplink1)
    #
    # uplink2 = FabricEthVlanPc(vlan, 'A', '3')
    # handle.add_mo(uplink2)
    # handle.commit()
    #
    #
    # eth2_template = VnicEtherIf('org-root/lan-conn-templ-ESX-C0-eth2', vlan_name)
    # handle.add_mo(eth2_template)
    # handle.commit()
    #
    # eth3_template = VnicEtherIf('org-root/lan-conn-templ-ESX-C0-eth3', vlan_name)
    # handle.add_mo(eth3_template)
    # handle.commit()

    # TODO remove constant
    add_to_pool = FabricPooledVlan('fabric/lan/net-group-DVS-01', vlan_name)
    try:
        handle.add_mo(add_to_pool)
        handle.commit()

    except UcsException as e:
        print e


