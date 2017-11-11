from flask import Flask, render_template
from flask_restful import Api, Resource
import os
from acitoolkit.acitoolkit import Session, Tenant
from aci import ManagedTopology
from ucsmsdk.ucshandle import UcsHandle
import json
from collections import OrderedDict
import config

sandbox = False

if sandbox:
    APIC_URL = 'https://sandboxapicdc.cisco.com'
    APIC_PASSWORD = '1vtG@lw@y'
    APIC_LOGIN = 'admin'
else:
    APIC_URL = os.getenv("APIC_URL")
    APIC_LOGIN = os.getenv("APIC_LOGIN")
    APIC_PASSWORD = os.getenv("APIC_PASSWORD")

SESSION = Session(APIC_URL, APIC_LOGIN, APIC_PASSWORD)
SESSION.login()


# Eliminate Trailing slash
if APIC_URL.endswith('/'):
    APIC_URL = APIC_URL[:-1]

def sample_data():
    data = {
        "nodes": [
            {"id": 100, "x": 410, "y": 100, "name": "12K-1"},
            {"id": 101, "x": 410, "y": 280, "name": "12K-2"},
            {"id": 102, "x": 660, "y": 280, "name": "Of-9k-03"},
            {"id": 103, "x": 660, "y": 100, "name": "Of-9k-02"},
            {"id": 104, "x": 180, "y": 190, "name": "Of-9k-01"}
        ],
        "links": [
            {"source": 0, "target": 1},
            {"source": 1, "target": 2},
            {"source": 1, "target": 3},
            {"source": 4, "target": 1},
            {"source": 2, "target": 3},
            {"source": 2, "target": 0},
            {"source": 3, "target": 0},
            {"source": 3, "target": 0},
            {"source": 3, "target": 0},
            {"source": 0, "target": 4},
            {"source": 0, "target": 4},
            {"source": 0, "target": 3}
        ]
    }

    return data


def get_topology():

    node_ret = list()
    nodes = SESSION.get('/api/class/fabricNode.json').json()['imdata']

    s_count = 0
    l_count = 0
    c_count = 0
    for n in nodes:
        d = dict()
        d['id'] = int(n['fabricNode']['attributes']['id'])
        d['name'] = str(n['fabricNode']['attributes']['name'])
        d['foo'] = 'bar'

        if n['fabricNode']['attributes']['role'] == 'spine':
            s_count += 1
            d['y'] = 50
            d['x'] = s_count * 200
            node_ret.append(d)
        elif n['fabricNode']['attributes']['role'] == 'leaf':
            l_count += 1
            d['y'] = 250
            d['x'] = l_count * 200
            node_ret.append(d)
        # we dont care about APIC controllers really
        # else:
        #     c_count += 1
        #     d['y'] = 400
        #     d['x'] = c_count * 200
        #     # must be a node/controller



    managed_fis = set(config.UCSM_VIP_MAP.keys())
    fi_url = '/api/class/fabricLooseNode.json'
    resp = SESSION.get(fi_url)
    fis = resp.json()['imdata']
    fis = [ln for ln in fis if ln['fabricLooseNode']['attributes']['id'] in managed_fis]
    for fi in fis:

        d = OrderedDict()
        d['id'] = str(fi['fabricLooseNode']['attributes']['id'])
        d['name'] = str(fi['fabricLooseNode']['attributes']['sysName'])
        d['sysDesc'] = str(fi['fabricLooseNode']['attributes']['sysDesc'])
        d['foo'] = 'bar'
        d['y'] = 400
        c_count +=1
        d['x'] = c_count * 200

        node_ret.append(d)

    # ACI links
    links = SESSION.get('/api/class/fabricLink.json').json()['imdata']
    link_ret = list()
    for l in links:
        d = dict()

        d['source'] = int(l['fabricLink']['attributes']['n1'])
        d['target'] = int(l['fabricLink']['attributes']['n2'])
        link_ret.append(d)

    # UCS links
    topology = ManagedTopology.get(SESSION, config.UCSM_VIP_MAP)
    ucs_links = list()
    for k,v in topology.items():
        if topology[k]:
            for i, fi in topology[k].items():
                l = dict()
                l['source'] = k
                l['target'] = fi
                link_ret.append(l)

    ret = {'nodes': node_ret,
          'links': link_ret}

    return ret



class TopologyEndpoint(Resource):
    def get(self):
        sample = sample_data()

        topo = get_topology()

        return topo

def topology():
    return render_template('topology.html')


def resources():
    pods = list()

    for pod in config.UCS.keys():
        handle = UcsHandle(pod, config.UCSM_LOGIN, config.UCSM_PASSWORD)
        handle.login()
        fis = handle.query_classid('swVlanPortNs')
        data = dict()
        data["vip"] = pod
        for fi in fis:
            current = fi.total_vlan_port_count
            max = fi.vlan_comp_on_limit
            # set to artifical value for effect
            #max = 2000

            data[fi.switch_id] = {"current": fi.total_vlan_port_count,
                                  #"max": fi.vlan_comp_on_limit,
                                  "max": max,
                                  "percentage": int(100 * float(current)/float(max))
                                  }
        pods.append(data)
    return render_template('resources-ucs.html', pods=pods)


def leaf_capacity():
    capacity_url = '/api/class/eqptcapacityEntity.json?query-target=self' \
                   '&rsp-subtree-include=stats' \
                   '&rsp-subtree-class=' \
                   'eqptcapacityVlanUsage5min,' \
                   'eqptcapacityPolUsage5min,' \
                   'eqptcapacityL2Usage5min'
    resp = SESSION.get(capacity_url)
    ret = list()
    capdata = resp.json()['imdata']
    for fn in capdata:

        node = dict()
        node['name'] = fn['eqptcapacityEntity']['attributes']['dn'].split('/sys')[0]
        for capentity in fn['eqptcapacityEntity']['children']:
            # collect vlan usage
            if 'eqptcapacityVlanUsage5min' in capentity:
                current = capentity['eqptcapacityVlanUsage5min']['attributes']['totalCum']
                maximum =  capentity['eqptcapacityVlanUsage5min']['attributes']['totalCapCum']
                if not maximum:
                    percentage = int(100 * float(current)/float(maximum))
                else:
                    percentage = "N/A"
                node['vlan'] = {"current": current, "max": maximum, "percentage": percentage}
            # collect mac usage
            elif 'eqptcapacityL2Usage5min' in capentity:
                current = capentity['eqptcapacityL2Usage5min']['attributes']['localEpCum']
                maximum =  capentity['eqptcapacityL2Usage5min']['attributes']['localEpCapCum']
                if not maximum:
                    percentage = int(100 * float(current)/float(maximum))
                else:
                    percentage = "N/A"
                node['mac'] = {"current": current, "max": maximum, "percentage": percentage}
            # collect epg usage
            elif 'eqptcapacityPolUsage5min' in capentity:
                current = capentity['eqptcapacityPolUsage5min']['attributes']['polUsageCum']
                maximum = capentity['eqptcapacityPolUsage5min']['attributes']['polUsageCapCum']
                if not maximum:
                    percentage = int(100 * float(current)/float(maximum))
                else:
                    percentage = "N/A"
                node['epg'] = {"current": current, "max": maximum, "percentage": percentage}
        ret.append(node)

    return render_template('resources-aci.html', capdata=ret)