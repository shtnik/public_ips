#!/usr/bin/env python
# -*- coding: utf-8 -*-


__author__ = "Alexander Gubanov (shtnik@gmail.com)"
__version__ = "0.1"
__copyright__ = "Copyright (c) 2016 Alexander Gubanov"

import ipaddress

from keystoneauth1.identity import v3
from keystoneauth1 import session
from keystoneclient.v3 import client as keystoneclient
from novaclient import client as novaclient
from neutronclient.v2_0 import client as neutronclient
from ceilometerclient import client as ceilometerclient

auth = v3.Password(
    auth_url='http://controller:35357/v3',
    username='admin',
    password='eeYaij2a',
    project_name='admin',
    user_domain_id='default',
    project_domain_id='default'
)
sess = session.Session(auth=auth)

keystone = keystoneclient.Client(session=sess)
nova = novaclient.Client('2.1', session=sess)
neutron = neutronclient.Client(session=sess)
ceilometer = ceilometerclient.Client(2, session=sess)

servers_list = nova.servers.list(search_opts={'all_tenants': 1})
routers_list = neutron.list_routers()[u'routers']
lbs_list = neutron.list_lbaas_loadbalancers()[u'loadbalancers']

plaint_private_networks = (u'127.0.0.0/8', u'10.0.0.0/8', u'172.16.0.0/12',
                           u'192.168.0.0/16')
private_networks = []
for network in plaint_private_networks:
    private_networks.append(ipaddress.ip_network(network))

for project in keystone.projects.list():
    instance_public_ips = []
    router_public_ips = []
    lbs_public_ips = []

    for server in servers_list:
        if server.tenant_id == project.id:
            if u'provider' in server.networks.keys():
                instance_public_ips.extend(server.networks[u'provider'])

    for router in routers_list:
        if router[u'tenant_id'] == project.id:
            if router[u'external_gateway_info']:
                for ext_fixed_ips in router[u'external_gateway_info'][u'external_fixed_ips']:
                    router_public_ips.append(ext_fixed_ips[u'ip_address'])

    for lb in lbs_list:
        if lb[u'tenant_id'] == project.id:
            ip_address = ipaddress.ip_address(lb[u'vip_address'])
            for network in private_networks:
                if ip_address in network:
                    break
            else:
                lbs_public_ips.append(lb[u'vip_address'])

    public_ips = instance_public_ips + router_public_ips + lbs_public_ips

    ceilometer.samples.create(
        counter_name='tenant.public.ips',
        counter_type='gauge',
        counter_unit='ips',
        counter_volume=len(public_ips),
        project_id=project.id,
        resource_id='tenant_public_ips_%s' % (project.id, )
    )
