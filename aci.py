from acitoolkit import BaseACIObject
import config

class VlanBinding(BaseACIObject):

    def __init__(self, *args, **kwargs):
        self._attributes = dict()

    def __str__(self):
        return self.dn

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by this acitoolkit class.
        :returns: list of strings containing APIC class names
        """
        return ['l2RsPathDomAtt']

    @classmethod
    def get(cls, session, name=None):
        """
        Gets all of the virtual switches from the APIC.
        :param session: the instance of Session used for APIC communication
        :returns: a list of vswitch objects
        """
        url = '/api/class/l2RsPathDomAtt.json'
        data = session.get(url).json()['imdata']
        apic_class = cls._get_apic_classes()[0]
        resp = []
        for object_data in data:

            obj = cls()
            attribute_data = object_data[apic_class]['attributes']

            obj._populate_from_attributes(attribute_data)
            resp.append(obj)

        return resp

    def _populate_from_attributes(self, attributes):
        """Fills in an object with the desired attributes.
           Overridden by inheriting classes to provide the specific attributes
           when getting objects from the APIC.
        """
        self._attributes = attributes

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
            obj = cls()
            obj._attributes = attributes
            return obj

    @property
    def dn(self):
        return self._attributes['dn']

    @property
    def vlan(self):
        try:
            vlan = self._attributes['dn'].split('vlan-[vlan-')[1].split(']')[0]
            return vlan
        except IndexError:
            return None

    @property
    def node(self):
        return self._attributes['dn'].split('node-')[1].split('/')[0]

    @property
    def port(self):
        """
        retrieves a port number from pathdn
        port-channels are ignored
        :param dn: pathdn
        :return: str or None
        """
        intf = self.dn.split('path-')[1].split('[')[1].split(']')[0]
        # ignore port-channels
        if 'po' not in intf:
            mod_port = 'Ethernet' + intf.split('eth')[1]
            return mod_port
        else:
            return None

    @property
    def status(self):
        return self._attributes['status']


class DistributedVirtualSwitch(BaseACIObject):
    """
    The logical node, which represents a virtual switch across hypervisors.
    For example, when implementing VMWare, this object represents VMware vSphere Distributed Switch (VDS).
    """

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by this acitoolkit class.
        :returns: list of strings containing APIC class names
        """
        return ['hvsLNode']

    @classmethod
    def get(cls, session, name=None):
        """
        Gets all of the virtual switches from the APIC.
        :param session: the instance of Session used for APIC communication
        :returns: a list of vswitch objects
        """
        url = '/api/class/hvsLNode.json'
        data = session.get(url).json()['imdata']
        apic_class = cls._get_apic_classes()[0]
        resp = []
        for object_data in data:
            name = str(object_data[apic_class]['attributes']['name'])
            obj = cls(name)
            attribute_data = object_data[apic_class]['attributes']
            obj._populate_from_attributes(attribute_data)
            resp.append(obj)

        return resp


class PortGroup(BaseACIObject):
    """
    The extended policies, which are common policies for VM interfaces.
    For example, when implementing VMware,
    this represents the distributed virtual port group.
    """

    def _populate_from_attributes(self, attributes):
        """Fills in an object with the desired attributes.
           Overridden by inheriting classes to provide the specific attributes
           when getting objects from the APIC.
        """
        self.vlan = str(attributes['startEncap']).split('vlan-')[1]
        self.dn = str(attributes['dn'])
        self.descr = str(attributes['descr'])

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by this acitoolkit class.
        :returns: list of strings containing APIC class names
        """
        return ['hvsExtPol']

    @classmethod
    def get(cls, session, name=None, encap=None):
        """
        Gets all of the virtual switches from the APIC.
        :param session: the instance of Session used for APIC communication
        :returns: a list of vswitch objects
        """
        if name:
            url = '/api/node/class/hvsExtPol.json?query-target-filter=and(eq(hvsExtPol.name,"{}"))'.format(name)
        elif encap:
            url = '/api/node/class/hvsExtPol.json?query-target-filter=and(eq(hvsExtPol.startEncap,"vlan-{}"))'.format(encap)
        else:
            url = '/api/class/{}.json'.format(cls._get_apic_classes()[0])

        data = session.get(url).json()['imdata']
        apic_class = cls._get_apic_classes()[0]
        resp = []
        for object_data in data:
            name = str(object_data[apic_class]['attributes']['name'])
            obj = cls(name)
            attribute_data = object_data[apic_class]['attributes']
            obj._populate_from_attributes(attribute_data)
            resp.append(obj)

        if name and len(resp) == 1:
            return resp[0]
        elif encap and len(resp) == 1:
            return resp[0]
        else:
            return resp


class ManagedTopology(dict):

    @classmethod
    def get(cls, session, vip_map):
        # Discover topology
        lldp_adj = session.get('/api/class/lldpAdjEp.json').json()['imdata']
        topology = dict()
        for adj in lldp_adj:
            node = get_node_id_from_dn(adj['lldpAdjEp']['attributes']['dn'])
            if node not in topology.keys():
                topology[node] = dict()

            port = get_port_from_lldp_dn(adj['lldpAdjEp']['attributes']['dn'])
            mgmt_ip = adj['lldpAdjEp']['attributes']['mgmtIp']
            if mgmt_ip in vip_map.keys():
                topology[node][port] = mgmt_ip
        return topology


def get_vlan_number_from_dn(dn):
    """
    retrieves vlan id from l2RsPathDomAtt dn
    :param dn: str l2RsPathDomAtt dn
    :return: str vlan encap
    """
    return dn.split('vlan-[vlan-')[1].split(']')[0]


def get_node_id_from_dn(dn):
    """
    glean leaf id from msg from l2RsPathDomAtt dn
    :param dn: str l2RsPathDomAtt dn
    :return: str node id
    """
    return dn.split('node-')[1].split('/')[0]


def get_port_from_pathdn(dn):
    """
    retrieves a port number from pathdn
    port-channels are ignored
    :param dn: pathdn
    :return: str or None
    """
    intf = dn.split('path-')[1].split('[')[1].split(']')[0]
    # ignore port-channels
    if 'po' not in intf:
        mod_port = 'Ethernet' + intf.split('eth')[1]
        return mod_port
    else:
        return None


def get_port_from_lldp_dn(dn):
    """
    returns port number from lldpAdjEp dn
    :param dn: str lldpAdjEp dn
    :return: str port e.g EthernetX/Y
    """
    intf = dn.split('if-')[1].split('[')[1].split(']')[0]
    # ignore port-channels
    if 'po' not in intf:
        mod_port = 'Ethernet' + intf.split('eth')[1]
        return mod_port
    else:
        return None


def fixup_epg_name(name):
    # Tenant-app-epg becomes tn-Tenant/ap-app/epg-epg
    words = name.split(config.DELIMTER)
    if len(words) < 3:
        return
    else:
        dn = "tn-{}/ap-{}/epg-{}".format(words[0], words[1], words[2:])
    return dn


def get_bindings_for_lsnode(session, fi):
    url = '/api/node/class/fvDyPathAtt.json?query-target-filter=' \
          'and(eq(fvDyPathAtt.targetDn,"topology/pod-1/node-102/sys/lsnode-{}"))'.format(fi)
    resp = session.get(url)
    return resp.json()['imdata']

