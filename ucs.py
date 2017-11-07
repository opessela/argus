from ucsmsdk.mometa.fabric.FabricVlan import FabricVlan
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

    exists = handle.query_dn(mo.dn)

    if exists:
        return
    else:
        try:
            handle.add_mo(mo)
            handle.commit()
        except UcsException as e:
            if 'already exists' in str(e):
                pass
            else:
                raise e
        return mo


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
    handle.remove_mo(mo)
    handle.commit()
    return mo


def deprovision_ucs_pod(handle, vlan_name, vlan_number):
    # UCS vlans can only be 32 chars and cannot contain '|'
    vlan_name = vlan_name[-32:].replace('|', '-')

    dn = config.VLAN_GROUP_DN + '/net-{}'.format(vlan_name)
    mo = handle.query_dn(dn)
    if mo:
        handle.remove_mo(mo)
        handle.commit()
        remove_vlan(handle, vlan_number, vlan_name)

def get_vlan_id_by_name(handle, vlan_name):
    vlan = handle.query_dn('fabric/lan/net-{}'.format(vlan_name))
    if vlan:
        return vlan.id

def provision_ucs_pod(handle, vlan_name, vlan_number):
    # UCS vlans can only be 32 chars and cannot contain '|'
    vlan_name = vlan_name[-32:].replace('|', '-')

    # Add vlan globally
    add_vlan(handle, vlan_number, vlan_name)

    # Add vlan to pool
    # TODO remove constant
    add_to_pool = FabricPooledVlan(config.VLAN_GROUP_DN, vlan_name)
    mo = handle.query_dn(add_to_pool.dn)
    if mo is None:
        try:
            handle.add_mo(add_to_pool)
            handle.commit()
        except UcsException as e:
            if 'already exists' in str(e):
                pass
            else:
                raise e
