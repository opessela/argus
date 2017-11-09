from ucsmsdk.ucshandle import UcsHandle
from ucsmsdk.mometa.fabric.FabricVlan import FabricVlan
from ucsmsdk.mometa.fabric.FabricPooledVlan import FabricPooledVlan
from ucsmsdk.mometa.network import NetworkElement
from ucsmsdk.ucsexception import UcsException

import config


class ManagedUCS(UcsHandle):
    """
    A managed UCS system
    """
    def __init__(self, ip, username, password, port=None, secure=None,
                 proxy=None):
        self._fabric_interconnects = list()
        self._vlans = list()
        self._managed_vlan_group = config.DVS_NAME
        super(ManagedUCS, self).__init__(ip, username, password, port=port, secure=secure,
                                         proxy=proxy)

    @staticmethod
    def ucs_name_from_portgroup(name, aci_delimter='|', ucs_delimter=config.DELIMTER):
        """
        sanitize portgroup name for ucs provisioning
        Args:
            name: name of portgroup
        Returns:

        """
        return name.replace(aci_delimter, ucs_delimter)[-30:]

    @property
    def vlans(self):
        return self._vlans

    def get_fabric_interconnects(self):
        fis = self.query_classid('networkElement')
        self._fabric_interconnects = fis
        return self._fabric_interconnects

    def get_neighbors(self, ):
        neighbors = self.query_classid('networkLanNeighborEntry')
        return neighbors

    def get_vlans(self):
        vlans = self.query_classid('FabricVlan')

        self._vlans = vlans
        return self._vlans

    def get_vlan_group(self):
        """
        returns the managed vlan group object
        Returns:

        """
        vlan_group = self.query_dn('fabric/lan/net-group-{}'.format(self._managed_vlan_group))
        return vlan_group

    def get_vlan_group_members(self):
        mo = self.get_vlan_group()
        vlans = self.query_children(in_dn=mo.dn, class_id='fabricPooledVlan')
        return vlans

    def add_vlan(self, vlan_id=None, vlan_name=None):
        """
        adds a vlan to the managed ucs system.
        """
        mo = FabricVlan(parent_mo_or_dn="fabric/lan",
                        sharing="none",
                        name=vlan_name, id=vlan_id)
        exists = self.query_dn(mo.dn)

        if exists:
            return exists
        else:
            try:
                self.add_mo(mo)
                self.commit()
                self._vlans.append(mo)
                obj = self.query_dn(mo.dn)
                return obj
            except UcsException as e:
                if 'already exists' in str(e):
                    pass
                else:
                    raise e
            return mo

    def remove_vlan(self, vlan_object):
        """
        adds a vlan to the managed ucs system.
        """
        self.remove_mo(vlan_object)
        self.commit()
        return True

    def add_vlan_to_group(self, name, vlan_group=config.VLAN_GROUP_DN):
        # Add vlan to pool
        add_to_pool = FabricPooledVlan(vlan_group, name)
        mo = self.query_dn(add_to_pool.dn)
        if mo is None:
            try:
                self.add_mo(add_to_pool)
                self.commit()
                return True
            except UcsException as e:
                if 'already exists' in str(e):
                    return False
                else:
                    raise e

    def remove_vlan_from_group(self, name):

        dn = config.VLAN_GROUP_DN + '/net-{}'.format(name)
        mo = self.query_dn(dn)
        if mo:
            self.remove_mo(mo)
            self.commit()
            return True

    def provision_portgroup(self, name, vlan_id, vlan_group=config.DVS_NAME):

        """
        provisions a portgroup into ucs

        1. sanitizes name
        2. provisions vlan globally
        3. add's vlan to group
        Args:
            portgroup_vlan_tuple: tuple (portgroup_name, vlan_id)

        Returns: bool

        """
        try:
            name = self.ucs_name_from_portgroup(name)
            vlan = self.add_vlan(vlan_id=vlan_id, vlan_name=name)
            self.add_vlan_to_group(vlan.name)
            return True
        except UcsException as e:
            if 'already exists' in str(e):
                return True
            else:
                raise e

    def deprovision_portgroup(self, name, vlan_id, vlan_group=config.DVS_NAME):

        """
        removes a portgroups configuration from ucs

        1. sanitizes name
        2. removes vlan from group
        3. removes vlan globally
        Args:
            portgroup_vlan_tuple: tuple (portgroup_name, vlan_id)

        Returns: bool

        """
        try:

            name = self.ucs_name_from_portgroup(name)
            print name
            vlan = FabricVlan(parent_mo_or_dn="fabric/lan",
                sharing="none",
                name=name, id=vlan_id)
            self.remove_vlan_from_group(vlan.name)
            self.remove_vlan(vlan)
            return True

        except UcsException as e:
            if 'already exists' in str(e):
                return False
            else:
                raise e


    @property
    def fi_ips(self):
        return [ip.oob_if_ip for ip in self._fabric_interconnects]

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
                    name=name[-32:], id=vlan_id)

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
                    name=name[-32:], id=vlan_id)
    handle.remove_mo(mo)
    handle.commit()
    return mo

def check_vlan_provisioned(handle, vlan_name, vlan_number):
    mo = FabricVlan(parent_mo_or_dn="fabric/lan",
                    sharing="none",
                    name=vlan_name[-32:], id=vlan_number)
    vlan_exists = handle.query_dn(mo.dn)
    group_member = FabricPooledVlan(config.VLAN_GROUP_DN, vlan_name[-32:])
    in_group = handle.query_dn(group_member.dn)
    if vlan_exists and in_group and (mo.id == vlan_exists.id):
        return True
    else:
        return False


def deprovision_ucs_pod(handle, vlan_name, vlan_number):
    # UCS vlans can only be 32 chars and cannot contain '|'
    vlan_name = vlan_name[-32:].replace('|', config.DELIMTER)

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
    vlan_name = vlan_name[-32:].replace('|', config.DELIMTER)

    # Add vlan globally
    add_vlan(handle, vlan_number, vlan_name)

    # Add vlan to pool
    add_to_pool = FabricPooledVlan(config.VLAN_GROUP_DN, vlan_name[-32:])
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
