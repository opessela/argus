
def get_vlan_number_from_dn(dn):
    """
    replace this with something better
    """
    return dn.split('vlan-[vlan-')[1].split(']')[0]
