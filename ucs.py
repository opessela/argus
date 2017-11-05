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
    """
    add vlan to UCS Pod
    :param handle: ucsmsdk handler
    :param vlan_id: str vlan number
    :param name: str vlan name
    :return:
    """
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
    """
    removes vlan from UCS pod
    :param handle: ucsmsdk handler
    :param vlan_id: str vlan number
    :param name: str vlan name
    :return:
    """
    mo = FabricVlan(parent_mo_or_dn="fabric/lan",
                    sharing="none",
                    name=name, id=vlan_id)
    try:
        handle.remove_mo(mo)
        handle.commit()
    except UcsException as e:
        print e

    return mo


def deprovision_ucs_pod(handle, vlan_number):
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


def provision_ucs_pod(handle, vlan_number):
    # TODO remove constant
    vlan_name = config.OBJECT_PREFIX.format(vlan_number)

    # Add vlan globally
    add_vlan(handle, vlan_number, vlan_name)

    # Add vlan to pool
    try:
        # TODO remove constant

        add_to_pool = FabricPooledVlan('fabric/lan/net-group-DVS-01', vlan_name)
        handle.add_mo(add_to_pool)
        handle.commit()

    except UcsException as e:
        print e
