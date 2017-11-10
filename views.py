from flask import Flask, render_template
from flask_restful import Api, Resource
import os
from acitoolkit.acitoolkit import Session, Tenant
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


def get_topology():
    node_ret = list()
    nodes = SESSION.get('/api/class/fabricNode.json').json()['imdata']
    print nodes
    s_count = 0
    l_count = 0
    c_count = 0
    for n in nodes:
        d = OrderedDict()
        d['id'] = int(n['fabricNode']['attributes']['id'])
        d['name'] = str(n['fabricNode']['attributes']['name'])
        d['foo'] = 'bar'

        if n['fabricNode']['attributes']['role'] == 'spine':
            s_count += 1
            d['y'] = 50
            d['x'] = s_count * 200
        elif n['fabricNode']['attributes']['role'] == 'leaf':
            l_count += 1
            d['y'] = 250
            d['x'] = l_count * 200
        else:
            c_count += 1
            d['y'] = 400
            d['x'] = c_count * 200
            # must be a node/controller

        node_ret.append(d)

    managed_fis = set(config.UCSM_VIP_MAP.keys())
    fi_url = '/api/class/fabricLooseNode.json'
    resp = SESSION.get(fi_url)
    fis = resp.json()['imdata']
    fis = [ln for ln in fis if ln['fabricLooseNode']['attributes']['id'] in managed_fis]
    fi_count = 0
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


    node_ret = node_ret + fis


    print fis
    links = SESSION.get('/api/class/fabricLink.json').json()['imdata']
    link_ret = list()
    for l in links:
        d = dict()

        d['source'] = int(l['fabricLink']['attributes']['n1'])
        d['target'] = int(l['fabricLink']['attributes']['n2'])
        link_ret.append(d)
    ret = json.dumps({'nodes': node_ret,
                       'links': link_ret}, indent=2)
    print ret
    return ret


def topology():

    return render_template('topology.html', topologyData=get_topology())


