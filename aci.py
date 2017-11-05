
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
