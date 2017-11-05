
def get_vlan_number_from_dn(dn):
    """
    replace this with something better
    """
    return dn.split('vlan-[vlan-')[1].split(']')[0]


def get_node_id_from_dn(dn):
    """
    glean leaf id from msg from websocket
    e.g topology/pod-1/node-101/sys/ctx-[vxlan-2883584]/bd-[vxlan-16187325]/vlan-[vlan-3171]/rspathDomAtt-[topology/pod-1/node-101/sys/conng/path-[po11]]
    :param dn:
    :return:
    """
    return dn.split('node-')[1].split('/')[0]


def path_ep(node, port):
    """
    construct pathep from node and port
    :param node:
    :param port:
    :return:
    """
    pass

def get_port_from_pathdn(dn):
    intf = dn.split('path-')[1].split('[')[1].split(']')[0]
    #ignore port-channels
    if 'po' not in intf:
        mod_port = 'Ethernet' + intf.split('eth')[1]
    return mod_port


def get_port_from_lldp_dn(dn):
    intf = dn.split('if-')[1].split('[')[1].split(']')[0]
    #ignore port-channels
    if 'po' not in intf:
        mod_port = 'Ethernet' + intf.split('eth')[1]
    return mod_port
