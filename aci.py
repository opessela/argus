from acitoolkit import BaseACIObject


class VlanBinding(BaseACIObject):

    def __init__(self, *args, **kwargs):
        self._attributes = None

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
        return self._attributes['dn'].split('vlan-[vlan-')[1].split(']')[0]

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

class Topology(dict):

    @classmethod
    def get(cls, session):
        # Discover topology
        lldp_adj = session.get('/api/class/lldpAdjEp.json').json()['imdata']
        topology = dict()
        for adj in lldp_adj:
            node = get_node_id_from_dn(adj['lldpAdjEp']['attributes']['dn'])
            if node not in topology.keys():
                topology[node] = dict()

            port = get_port_from_lldp_dn(adj['lldpAdjEp']['attributes']['dn'])
            mgmt_ip = adj['lldpAdjEp']['attributes']['mgmtIp']
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
