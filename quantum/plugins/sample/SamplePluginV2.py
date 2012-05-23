# Copyright (c) 2012 OpenStack, LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import ConfigParser
import logging
import os

from quantum import quantum_plugin_base_v2
from quantum.api import api_common as common
from quantum.common import exceptions as exc
from quantum.db import api as db


LOG = logging.getLogger('quantum.plugins.sample.SamplePlugin')
CONFIG_FILE = 'sample_plugin.ini'
CONFIG_FILE_PATHS = []
if os.environ.get('QUANTUM_HOME', None):
    CONFIG_FILE_PATHS.append('%s/etc' % os.environ['QUANTUM_HOME'])
CONFIG_FILE_PATHS.append("/etc/quantum/plugins/sample_plugin")


def init_config(cfile=None):
    config = ConfigParser.ConfigParser()
    if cfile == None:
        if os.path.exists(CONFIG_FILE):
            cfile = CONFIG_FILE
        else:
            cfile = find_config(os.path.abspath(os.path.dirname(__file__)))

    if cfile == None:
        raise Exception("Configuration file \"%s\" doesn't exist" % (cfile))
    LOG.info("Using configuration file: %s" % cfile)
    config.read(cfile)
    LOG.debug("Config: %s" % config)
    return config


def find_config(basepath):
    LOG.info("Looking for %s in %s" % (CONFIG_FILE, basepath))
    for root, dirs, files in os.walk(basepath, followlinks=True):
        if CONFIG_FILE in files:
            return os.path.join(root, CONFIG_FILE)
    for alternate_path in CONFIG_FILE_PATHS:
        p = os.path.join(alternate_path, CONFIG_FILE)
        if os.path.exists(p):
            return p
    return None


class QuantumEchoPlugin(quantum_plugin_base_v2.QuantumPluginBaseV2):

    """
    QuantumEchoPlugin is a demo plugin that doesn't
    do anything but demonstrated the concept of a
    concrete Quantum Plugin. Any call to this plugin
    will result in just a log statement with the name
    method that was called and its arguments.
    """

    def _log(self, name, context, **kwargs):
        kwarg_msg = ' '.join([('%s: |%s|' % (str(key), kwargs[key]))
                              for key in kwargs])

        # TODO(anyone) Add a nice __repr__ and __str__ to context
        #LOG.debug('%s context: %s %s' % (name, context, kwarg_msg))
        LOG.debug('%s %s' % (name, kwarg_msg))

    def create_subnet(self, context, subnet):
        self._log(self, "create_subnet", context, subnet=subnet)

    def update_subnet(self, context, id, subnet):
        self._log(self, "update_subnet", context, id=id, subnet=subnet)

    def get_subnet(self, context, id, show=None, verbose=None):
        self._log(self, "get_subnet", context, id=id, show=show,
                  verbose=verbose)

    def delete_subnet(self, context, id):
        self._log(self, "delete_subnet", context, id=id)

    def get_subnets(self, context, filters=None, show=None, verbose=None):
        self._log(self, "get_subnets", context, filters=None, show=show,
                  verbose=verbose)

    def create_network(self, context, network):
        self._log(self, "create_network", context, network=network)

    def update_network(self, context, id, network):
        self._log(self, "update_network", context, id=id, network=network)

    def get_network(self, context, id, show=None, verbose=None):
        self._log(self, "get_network", context, id=id, show=show,
                  verbose=verbose)

    def delete_network(self, context, id):
        self._log(self, "delete_network", context, id=id)

    def get_networks(self, context, filters=None, show=None, verbose=None):
        self._log(self, "get_networks", context, filters=None, show=show,
                  verbose=verbose)

    def create_port(self, context, port):
        self._log(self, "create_port", context, port=port)

    def update_port(self, context, id, port):
        self._log(self, "update_port", context, id=id, port=port)

    def get_port(self, context, id, show=None, verbose=None):
        self._log(self, "get_port", context, id=id, show=show,
                  verbose=verbose)

    def delete_port(self, context, id):
        self._log(self, "delete_port", context, id=id)

    def get_ports(self, context, filters=None, show=None, verbose=None):
        self._log(self, "get_ports", context, filters=None, show=show,
                  verbose=verbose)

    supported_extension_aliases = ["FOXNSOX"]

    def method_to_support_foxnsox_extension(self):
        print("method_to_support_foxnsox_extension() called\n")


class FakePlugin(quantum_plugin_base_v2.QuantumPluginBaseV2):
    """
    FakePlugin is a demo plugin that provides
    in-memory data structures to aid in quantum
    client/cli/api development
    """

    def __init__(self):
        config = init_config()
        sql_connection = 'sqlite:///:memory:'
        if config.has_section('db'):
            sql_connection = config.get('db', 'sql_connection')
        db.configure_db({'sql_connection': sql_connection})
        FakePlugin._net_counter = 0

    def _get_network(self, tenant_id, network_id):

        db.validate_network_ownership(tenant_id, network_id)
        try:
            network = db.network_get(network_id)
        except:
            raise exc.NetworkNotFound(net_id=network_id)
        return network

    def _get_port(self, tenant_id, network_id, port_id):

        db.validate_port_ownership(tenant_id, network_id, port_id)
        net = self._get_network(tenant_id, network_id)
        try:
            port = db.port_get(port_id, network_id)
        except:
            raise exc.PortNotFound(net_id=network_id, port_id=port_id)
        # Port must exist and belong to the appropriate network.
        if port['network_id'] != net['uuid']:
            raise exc.PortNotFound(net_id=network_id, port_id=port_id)
        return port

    def _validate_port_state(self, port_state):
        if port_state.upper() not in ('ACTIVE', 'DOWN'):
            raise exc.StateInvalid(port_state=port_state)
        return True

    def _validate_attachment(self, tenant_id, network_id, port_id,
                             remote_interface_id):
        for port in db.port_list(network_id):
            if port['interface_id'] == remote_interface_id:
                raise exc.AlreadyAttached(net_id=network_id,
                                          port_id=port_id,
                                          att_id=port['interface_id'],
                                          att_port_id=port['uuid'])

    def get_all_networks(self, tenant_id, **kwargs):
        """
        Returns a dictionary containing all
        <network_uuid, network_name> for
        the specified tenant.
        """
        LOG.debug("FakePlugin.get_all_networks() called")
        filter_opts = kwargs.get('filter_opts', None)
        if not filter_opts is None and len(filter_opts) > 0:
            LOG.debug("filtering options were passed to the plugin"
                      "but the Fake plugin does not support them")
        nets = []
        for net in db.network_list(tenant_id):
            net_item = {'net-id': str(net.uuid),
                        'net-name': net.name,
                        'net-op-status': net.op_status}
            nets.append(net_item)
        return nets

    def get_network_details(self, tenant_id, net_id):
        """
        retrieved a list of all the remote vifs that
        are attached to the network
        """
        LOG.debug("FakePlugin.get_network_details() called")
        net = self._get_network(tenant_id, net_id)
        # Retrieves ports for network
        ports = self.get_all_ports(tenant_id, net_id)
        return {'net-id': str(net.uuid),
                'net-name': net.name,
                'net-op-status': net.op_status,
                'net-ports': ports}

    def create_network(self, tenant_id, net_name, **kwargs):
        """
        Creates a new Virtual Network, and assigns it
        a symbolic name.
        """
        LOG.debug("FakePlugin.create_network() called")
        new_net = db.network_create(tenant_id, net_name)
        # Put operational status UP
        db.network_update(new_net.uuid, net_name,
                          op_status=common.OperationalStatus.UP)
        # Return uuid for newly created network as net-id.
        return {'net-id': new_net.uuid}

    def delete_network(self, tenant_id, net_id):
        """
        Deletes the network with the specified network identifier
        belonging to the specified tenant.
        """
        LOG.debug("FakePlugin.delete_network() called")
        net = self._get_network(tenant_id, net_id)
        # Verify that no attachments are plugged into the network
        if net:
            for port in db.port_list(net_id):
                if port['interface_id']:
                    raise exc.NetworkInUse(net_id=net_id)
            db.network_destroy(net_id)
            return net
        # Network not found
        raise exc.NetworkNotFound(net_id=net_id)

    def update_network(self, tenant_id, net_id, **kwargs):
        """
        Updates the attributes of a particular Virtual Network.
        """
        LOG.debug("FakePlugin.update_network() called")
        net = db.network_update(net_id, tenant_id, **kwargs)
        return net

    def get_all_ports(self, tenant_id, net_id, **kwargs):
        """
        Retrieves all port identifiers belonging to the
        specified Virtual Network.
        """
        LOG.debug("FakePlugin.get_all_ports() called")
        db.validate_network_ownership(tenant_id, net_id)
        filter_opts = kwargs.get('filter_opts')
        if filter_opts:
            LOG.debug("filtering options were passed to the plugin"
                      "but the Fake plugin does not support them")
        port_ids = []
        ports = db.port_list(net_id)
        for x in ports:
            d = {'port-id': str(x.uuid)}
            port_ids.append(d)
        return port_ids

    def get_port_details(self, tenant_id, net_id, port_id):
        """
        This method allows the user to retrieve a remote interface
        that is attached to this particular port.
        """
        LOG.debug("FakePlugin.get_port_details() called")
        port = self._get_port(tenant_id, net_id, port_id)
        return {'port-id': str(port.uuid),
                'attachment': port.interface_id,
                'port-state': port.state,
                'port-op-status': port.op_status}

    def create_port(self, tenant_id, net_id, port_state=None, **kwargs):
        """
        Creates a port on the specified Virtual Network.
        """
        LOG.debug("FakePlugin.create_port() called")
        # verify net_id
        self._get_network(tenant_id, net_id)
        port = db.port_create(net_id, port_state)
        # Put operational status UP
        db.port_update(port.uuid, net_id,
                       op_status=common.OperationalStatus.UP)
        port_item = {'port-id': str(port.uuid)}
        return port_item

    def update_port(self, tenant_id, net_id, port_id, **kwargs):
        """
        Updates the attributes of a port on the specified Virtual Network.
        """
        LOG.debug("FakePlugin.update_port() called")
        #validate port and network ids
        self._get_network(tenant_id, net_id)
        self._get_port(tenant_id, net_id, port_id)
        port = db.port_update(port_id, net_id, **kwargs)
        port_item = {'port-id': port_id, 'port-state': port['state']}
        return port_item

    def delete_port(self, tenant_id, net_id, port_id):
        """
        Deletes a port on a specified Virtual Network,
        if the port contains a remote interface attachment,
        the remote interface is first un-plugged and then the port
        is deleted.
        """
        LOG.debug("FakePlugin.delete_port() called")
        self._get_network(tenant_id, net_id)
        port = self._get_port(tenant_id, net_id, port_id)
        if port['interface_id']:
            raise exc.PortInUse(net_id=net_id, port_id=port_id,
                                att_id=port['interface_id'])
        try:
            port = db.port_destroy(port_id, net_id)
        except Exception, e:
            raise Exception("Failed to delete port: %s" % str(e))
        d = {}
        d["port-id"] = str(port.uuid)
        return d

    def plug_interface(self, tenant_id, net_id, port_id, remote_interface_id):
        """
        Attaches a remote interface to the specified port on the
        specified Virtual Network.
        """
        LOG.debug("FakePlugin.plug_interface() called")
        port = self._get_port(tenant_id, net_id, port_id)
        # Validate attachment
        self._validate_attachment(tenant_id, net_id, port_id,
                                  remote_interface_id)
        if port['interface_id']:
            raise exc.PortInUse(net_id=net_id, port_id=port_id,
                                att_id=port['interface_id'])
        db.port_set_attachment(port_id, net_id, remote_interface_id)

    def unplug_interface(self, tenant_id, net_id, port_id):
        """
        Detaches a remote interface from the specified port on the
        specified Virtual Network.
        """
        LOG.debug("FakePlugin.unplug_interface() called")
        self._get_port(tenant_id, net_id, port_id)
        # TODO(salvatore-orlando):
        # Should unplug on port without attachment raise an Error?
        db.port_unset_attachment(port_id, net_id)
