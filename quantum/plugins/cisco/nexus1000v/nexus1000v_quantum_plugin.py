# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright 2011,2012,2013 Cisco Systems, Inc.  All rights reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
# @author: Rudrajit Tapadar, Cisco Systems, Inc.
# @author: Abhishek Raut, Cisco Systems, Inc.
# @author: Sergey Sudakovich, Cisco Systems, Inc.

import logging
import sys
from quantum.db import dhcp_rpc_base
from quantum.db import l3_rpc_base
from quantum.common import rpc as q_rpc
from quantum.openstack.common.rpc import proxy
from quantum.common import topics
from quantum.plugins.cisco.common import cisco_constants as const
from quantum.common import constants as q_const
from quantum.db import db_base_plugin_v2
from  quantum.plugins.cisco.db import nexus1000v_db
from quantum.plugins.cisco.n1kv import n1kv_configuration as n1kv_conf


LOG = logging.getLogger(__name__)


class Nexus1000vQuantumPlugin(db_base_plugin_v2.QuantumDbPluginV2):
    __native_bulk_support = True
    supported_extension_aliases = ["provider", "network_profile", "policy_profile", "n1kv_profile", "router"]

    def __init__(self):
        nexus1000v_db.initialize()
        # TBD Begin : To be removed. No need for this parameters
        self._parse_network_vlan_ranges()
        self.enable_tunneling = n1kv_conf.N1KV['enable_tunneling']
        self.vxlan_id_ranges = []
        if self.enable_tunneling:
            self._parse_vxlan_id_ranges()
            nexus1000v_db.sync_vxlan_allocations(self.vxlan_id_ranges)
        # TBD end
        self._setup_vsm()

    def _setup_vsm(self):
        """ Establish Communication with Cisco Nexus1000V VSM """
        LOG.debug('_setup_vsm')
        self.agent_vsm = True
        self._send_register_request()

    #TBD: remove added for compilation
    def _send_register_request(self):
        LOG.debug('_send_register_request')

        # TBD Begin : To be removed. Needs some change in logic before removal
    def _parse_network_vlan_ranges(self):
        self.network_vlan_ranges = {}
        ranges = n1kv_conf.N1KV['network_vlan_ranges']
        ranges = ranges.split(',')
        for entry in ranges:
            entry = entry.strip()
            if ':' in entry:
                try:
                    physical_network, vlan_min, vlan_max = entry.split(':')
                    self._add_network_vlan_range(physical_network.strip(),
                                                 int(vlan_min),
                                                 int(vlan_max))
                except ValueError as ex:
                    LOG.error("Invalid network VLAN range: \'%s\' - %s",
                              entry, ex)
                    sys.exit(1)
            else:
                self._add_network(entry)
        LOG.info("Network VLAN ranges: %s", self.network_vlan_ranges)

    def _add_network_vlan_range(self, physical_network, vlan_min, vlan_max):
        self._add_network(physical_network)
        self.network_vlan_ranges[physical_network].append((vlan_min, vlan_max))

    def _add_network(self, physical_network):
        if physical_network not in self.network_vlan_ranges:
            self.network_vlan_ranges[physical_network] = []

    def _parse_vxlan_id_ranges(self):
        ranges = n1kv_conf.N1KV['vxlan_id_ranges']
        ranges = ranges.split(',')
        for entry in ranges:
            entry = entry.strip()
            try:
                tun_min, tun_max = entry.split(':')
                self.vxlan_id_ranges.append((int(tun_min), int(tun_max)))
            except ValueError as ex:
                LOG.error("Invalid vxlan ID range: \'%s\' - %s", entry, ex)
                sys.exit(1)
        LOG.info("Tunnel ID ranges: %s", self.vxlan_id_ranges)

        # TODO(rkukura) Use core mechanism for attribute authorization
        # when available.

        # TBD End

    ####### Network CRUD #######
    def create_network(self, context, network): pass
    def get_network(self, context, id, fields=None): pass
    def get_networks(self, context, filters=None, fields=None): pass
    def update_network(self, context, id, network): pass
    def delete_network(self, context, id): pass
    ####### Port CRUD #######
    def create_port(self, context, port): pass
    def get_port(self, context, id, fields=None): pass
    def get_ports(self, context, filters=None, fields=None): pass
    def update_port(self, context, id, port): pass
    def delete_port(self, context, id): pass
    ####### Subnet CRUD #######
    def create_subnet(self, context, subnet):pass
    def get_subnet(self, context, id, fields=None):pass
    def get_subnets(self, context, filters=None, fields=None):pass
    def update_subnet(self, context, id, subnet):pass
    def delete_subnet(self, context, id):pass



class N1kvRpcCallbacks(dhcp_rpc_base.DhcpRpcCallbackMixin,
                       l3_rpc_base.L3RpcCallbackMixin):

    # Set RPC API version to 1.0 by default.
    RPC_API_VERSION = '1.0'

    def __init__(self, notifier):
        self.notifier = notifier

    def create_rpc_dispatcher(self):
        '''Get the rpc dispatcher for this manager.

        If a manager would like to set an rpc API version, or support more than
        one class as the target of rpc messages, override this method.
        '''
        return q_rpc.PluginRpcDispatcher([self])

    def get_device_details(self, rpc_context, **kwargs):
        """Agent requests device details"""
        agent_id = kwargs.get('agent_id')
        device = kwargs.get('device')
        LOG.debug(_("Device %(device)s details requested from %(agent_id)s"),
                  locals())
        port = nexus1000v_db.get_port(device)
        if port:
            binding = n1kv_db_v2.get_network_binding(None, port['network_id'])
            entry = {'device': device,
                     'network_id': port['network_id'],
                     'port_id': port['id'],
                     'admin_state_up': port['admin_state_up'],
                     'network_type': binding.network_type,
                     'segmentation_id': binding.segmentation_id,
                     'physical_network': binding.physical_network}
            # Set the port status to UP
            nexus1000v_db.set_port_status(port['id'], q_const.PORT_STATUS_ACTIVE)
        else:
            entry = {'device': device}
            LOG.debug(_("%s can not be found in database"), device)
        return entry

    def update_device_down(self, rpc_context, **kwargs):
        """Device no longer exists on agent"""
        # (TODO) garyk - live migration and port status
        agent_id = kwargs.get('agent_id')
        device = kwargs.get('device')
        LOG.debug(_("Device %(device)s no longer exists on %(agent_id)s"),
                  locals())
        port = nexus1000v_db.get_port(device)
        if port:
            entry = {'device': device,
                     'exists': True}
            # Set port status to DOWN
            nexus1000v_db.set_port_status(port['id'], q_const.PORT_STATUS_DOWN)
        else:
            entry = {'device': device,
                     'exists': False}
            LOG.debug(_("%s can not be found in database"), device)
        return entry

    def vxlan_sync(self, rpc_context, **kwargs):
        """Update new vxlan.

        Updates the datbase with the vxlan IP. All listening agents will also
        be notified about the new vxlan IP.
        """
        vxlan_ip = kwargs.get('vxlan_ip')
        # Update the database with the IP
        vxlan = nexus1000v_db.add_vxlan_endpoint(vxlan_ip)
        vxlans = nexus1000v_db.get_vxlan_endpoints()
        entry = dict()
        entry['vxlans'] = vxlans
        # Notify all other listening agents
        self.notifier.vxlan_update(rpc_context, vxlan.ip_address,
                                   vxlan.id)
        # Return the list of vxlans IP's to the agent
        return entry


class AgentNotifierApi(proxy.RpcProxy):
    '''Agent side of the N1kv rpc API.

    API version history:
        1.0 - Initial version.

    '''

    BASE_RPC_API_VERSION = '1.0'

    def __init__(self, topic):
        super(AgentNotifierApi, self).__init__(
            topic=topic, default_version=self.BASE_RPC_API_VERSION)
        self.topic_network_delete = topics.get_topic_name(topic,
                                                          topics.NETWORK,
                                                          topics.DELETE)
        self.topic_port_update = topics.get_topic_name(topic,
                                                       topics.PORT,
                                                       topics.UPDATE)
        self.topic_vxlan_update = topics.get_topic_name(topic,
                                                        const.TUNNEL,
                                                        topics.UPDATE)

    def network_delete(self, context, network_id):
        self.fanout_cast(context,
                         self.make_msg('network_delete',
                                       network_id=network_id),
                         topic=self.topic_network_delete)

    def port_update(self, context, port, network_type, segmentation_id,
                    physical_network):
        self.fanout_cast(context,
                         self.make_msg('port_update',
                                       port=port,
                                       network_type=network_type,
                                       segmentation_id=segmentation_id,
                                       physical_network=physical_network),
                         topic=self.topic_port_update)

    def vxlan_update(self, context, vxlan_ip, vxlan_id):
        self.fanout_cast(context,
                         self.make_msg('vxlan_update',
                                       vxlan_ip=vxlan_ip,
                                       vxlan_id=vxlan_id),
                         topic=self.topic_vxlan_update)