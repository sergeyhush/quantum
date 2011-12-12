#!/usr/bin/env python
# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright 2011 Cisco Systems, Inc.
# All Rights Reserved.
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
#
# Performs per host Linux Bridge configuration for Quantum.
# Based on the structure of the OpenVSwitch agent in the 
# Quantum OpenVSwitch Plugin.
# @author: Sumit Naiksatam, Cisco Systems, Inc.
#

import ConfigParser
import logging as LOG
import MySQLdb
import os
import sys
import time
import signal

from optparse import OptionParser
from subprocess import *

BRIDGE_NAME_PREFIX = "brq-"
GATEWAY_INTERFACE_PREFIX = "gw-"
TAP_INTERFACE_PREFIX = "tap"
BRIDGE_FS = "/sys/devices/virtual/net/"
BRIDGE_NAME_PLACEHOLDER = "bridge_name"
BRIDGE_INTERFACES_FS = BRIDGE_FS + BRIDGE_NAME_PLACEHOLDER + "/brif/"

class LinuxBridge:
    def __init__(self, br_name_prefix, physical_interface):
        self.br_name_prefix = br_name_prefix
        self.physical_interface = physical_interface

    def run_cmd(self, args):
        LOG.debug("Running command: " + " ".join(args))
        p = Popen(args, stdout=PIPE)
        retval = p.communicate()[0]
        if p.returncode == -(signal.SIGALRM):
            LOG.debug("Timeout running command: " + " ".join(args))
        if retval:
            LOG.debug("Command returned: %s" % retval)
        return retval

    def device_exists(self, device):
        """Check if ethernet device exists."""
        retval = self.run_cmd(['ip', 'link', 'show', 'dev', device])
        if retval:
            return True
        else:
            return False

    def get_bridge_name(self, network_id):
        if not network_id:
            LOG.error("Invalid Network ID, will lead to incorrect bridge" \
                      "name")
        bridge_name = self.br_name_prefix + network_id[0:11]
        return bridge_name

    def get_subinterface_name(self, vlan_id):
        if not vlan_id:
            LOG.error("Invalid VLAN ID, will lead to incorrect subinterface" \
                      "name")
        subinterface_name = '%s.%s' % (self.physical_interface, vlan_id)
        return subinterface_name

    def get_tap_device_name(self, interface_id):
        if not interface_id:
            LOG.error("Invalid Interface ID, will lead to incorrect " \
                      "tap device name")
        tap_device_name = TAP_INTERFACE_PREFIX + interface_id[0:11]
        return tap_device_name

    def get_all_quantum_bridges(self):
        quantum_bridge_list = []
        bridge_list = os.listdir(BRIDGE_FS)
        for bridge in bridge_list:
            if bridge.startswith(BRIDGE_NAME_PREFIX):
                quantum_bridge_list.append(bridge)
        return quantum_bridge_list

    def get_enslaved_interfaces(self, bridge_name):
        if self.device_exists(bridge_name):
            bridge_interface_path = \
                    BRIDGE_INTERFACES_FS.replace(BRIDGE_NAME_PLACEHOLDER,
                                                 bridge_name)
            return os.listdir(bridge_interface_path)

    def get_all_tap_devices(self):
        tap_devices = []
        retval = self.run_cmd(['ip', 'tuntap'])
        rows = retval.split('\n')
        for row in rows:
            split_row = row.split(':')
            if split_row[0].startswith(TAP_INTERFACE_PREFIX):
                tap_devices.append(split_row[0])

        return tap_devices

    def get_bridge_for_tap_device(self, tap_device_name):
        bridges = self.get_all_quantum_bridges()
        for bridge in bridges:
            interfaces = self.get_enslaved_interfaces(bridge)
            if tap_device_name in interfaces:
                return bridge

        return None

    def ensure_vlan_bridge(self, network_id, vlan_id):
        """Create a vlan and bridge unless they already exist."""
        interface = self.ensure_vlan(vlan_id)
        bridge_name = self.get_bridge_name(network_id)
        self.ensure_bridge(bridge_name, interface)
        return interface

    def ensure_vlan(self, vlan_id):
        """Create a vlan unless it already exists."""
        interface = self.get_subinterface_name(vlan_id)
        if not self.device_exists(interface):
            LOG.debug("Creating subinterface %s for VLAN %s on interface %s" %
                      (interface, vlan_id, self.physical_interface))
            if self.run_cmd(['ip', 'link', 'add', 'link',
                             self.physical_interface,
                             'name', interface, 'type', 'vlan', 'id',
                             vlan_id]):
                return
            if self.run_cmd(['ip', 'link', 'set', interface, 'up']):
                return
            LOG.debug("Done creating subinterface %s" % interface)
        return interface

    def ensure_bridge(self, bridge_name, interface):
        """
        Create a bridge unless it already exists.
        """
        if not self.device_exists(bridge_name):
            LOG.debug("Starting bridge %s for subinterface %s" % (bridge_name,
                                                                interface))
            if self.run_cmd(['brctl', 'addbr', bridge_name]):
                return
            if self.run_cmd(['brctl', 'setfd', bridge_name, str(0)]):
                return
            if self.run_cmd(['brctl', 'stp', bridge_name, 'off']):
                return
            if self.run_cmd(['ip', 'link', 'set', bridge_name, 'up']):
                return
            if self.run_cmd(['brctl', 'addif', bridge_name, interface]):
                return
            LOG.debug("Done starting bridge %s for subinterface %s" %
                      (bridge_name, interface))

    def add_tap_interface(self, network_id, vlan_id, interface_id):
        """
        If a VIF has been plugged into a network, this function will
        add the corresponding tap device to the relevant bridge
        """
        if not interface_id:
            """
            Since the VIF id is null, no VIF is plugged into this port
            no more processing is required
            """
            return
        tap_device_name = self.get_tap_device_name(interface_id)
        bridge_name = self.get_bridge_name(network_id)
        if not self.device_exists(tap_device_name):
            LOG.debug("Tap device: %s does not exist on this host, skipped" %
                      tap_device_name) 
            return

        if interface_id:
            current_bridge_name = \
                    self.get_bridge_for_tap_device(tap_device_name)
            if bridge_name == current_bridge_name:
                return
            LOG.debug("Adding device %s to bridge %s" % (tap_device_name,
                                                         bridge_name))
            if current_bridge_name:
                if self.run_cmd(['brctl', 'delif', current_bridge_name,
                                 tap_device_name]):
                    return

            self.ensure_vlan_bridge(network_id, vlan_id)
            if self.run_cmd(['brctl', 'addif', bridge_name, tap_device_name]):
                return
            LOG.debug("Done adding device %s to bridge %s" % (tap_device_name,
                                                              bridge_name))

    def add_gateway_interface(self, network_id, vlan_id, interface_id):
        """
        If a Gateway VIF has been plugged into a network, this function will
        add the corresponding tap device to the relevant bridge
        """
        if not interface_id:
            """
            Since the VIF id is null, no VIF is plugged into this port
            no more processing is required
            """
            return
        bridge_name = self.get_bridge_name(network_id)
        if not self.device_exists(interface_id):
            LOG.debug("Gateway interface: %s does not exist on this host, skipped" %
                      interface_id) 
            return

        if interface_id:
            self.ensure_vlan_bridge(network_id, vlan_id)
            if self.run_cmd(['brctl', 'addif', bridge_name, interface_id]):
                return
            LOG.debug("Done adding device %s to bridge %s" % (tap_device_name,
                                                              bridge_name))

    def add_interface(self, network_id, vlan_id, interface_id):
        if not interface_id:
            return
        if interface_id.startswith(GATEWAY_INTERFACE_PREFIX):
            return self.add_gateway_interface(network_id, vlan_id,
                                              interface_id)
        else:
            return self.add_tap_interface(network_id, vlan_id,
                                          interface_id)

    def delete_vlan_bridge(self, bridge_name):
        if self.device_exists(bridge_name):
            enslaved_interfaces = self.get_enslaved_interfaces(bridge_name)
            for interface in enslaved_interfaces:
                self.remove_interface(bridge_name, interface)
                if interface.startswith(self.physical_interface):
                    self.delete_vlan(interface)

            LOG.debug("Deleting bridge %s" % bridge_name)
            if self.run_cmd(['ip', 'link', 'set', bridge_name, 'down']):
                return
            if self.run_cmd(['brctl', 'delbr', bridge_name]):
                return
            LOG.debug("Done deleting bridge %s" % bridge_name)

        else:
            LOG.error("Cannot delete bridge %s, does not exist" % bridge_name)

    def remove_interface(self, bridge_name, interface_name):
        if self.device_exists(bridge_name):
            LOG.debug("Removing device %s from bridge %s" % \
                      (interface_name, bridge_name))
            if self.run_cmd(['brctl', 'delif', bridge_name, interface_name]):
                return
            LOG.debug("Done removing device %s from bridge %s" % \
                      (interface_name, bridge_name))

    def delete_vlan(self, interface):
        if self.device_exists(interface):
            LOG.debug("Deleting subinterface %s for vlan" % interface)
            if self.run_cmd(['ip', 'link', 'set', interface, 'down']):
                return
            if self.run_cmd(['ip', 'link', 'delete', interface]):
                return
            LOG.debug("Done deleting subinterface %s" % interface)


class LinuxBridgeQuantumAgent:

    def __init__(self, br_name_prefix, physical_interface, polling_interval):
        self.polling_interval = int(polling_interval)
        self.setup_linux_bridge(br_name_prefix, physical_interface)

    def setup_linux_bridge(self, br_name_prefix, physical_interface):
        self.linux_br = LinuxBridge(br_name_prefix, physical_interface)

    def process_port_binding(self, port_id, network_id, interface_id,
                             vlan_id):
        self.linux_br.add_interface(network_id, vlan_id, interface_id)

    def process_unplugged_interfaces(self, plugged_interfaces):
        """
        If there are any tap devices that are not corresponding to the
        list of attached VIFs, then those are corresponding to recently
        unplugged VIFs, so we need to remove those tap devices from their
        current bridge association
        """
        plugged_tap_device_names = []
        for interface in plugged_interfaces:
            tap_device_name = self.linux_br.get_tap_device_name(interface)
            plugged_tap_device_names.append(tap_device_name)

        for tap_device in self.linux_br.get_all_tap_devices():
            if tap_device not in plugged_tap_device_names:
                current_bridge_name = \
                        self.linux_br.get_bridge_for_tap_device(tap_device)
                if current_bridge_name:
                    self.linux_br.remove_interface(current_bridge_name,
                                                   tap_device)

    def process_deleted_networks(self, vlan_bindings):
        current_quantum_networks = vlan_bindings.keys()
        current_quantum_bridge_names = []
        for network in current_quantum_networks:
            bridge_name = self.linux_br.get_bridge_name(network)
            current_quantum_bridge_names.append(bridge_name)

        quantum_bridges_on_this_host = self.linux_br.get_all_quantum_bridges()
        for bridge in quantum_bridges_on_this_host:
            if bridge not in current_quantum_bridge_names:
                self.linux_br.delete_vlan_bridge(bridge)

    def daemon_loop(self, conn):

        while True:
            cursor = MySQLdb.cursors.DictCursor(conn)
            cursor.execute("SELECT * FROM vlan_bindings")
            rows = cursor.fetchall()
            cursor.close()
            vlan_bindings = {}
            vlans_string = ""
            for r in rows:
                vlan_bindings[r['network_id']] = r
                vlans_string = "%s %s" % (vlans_string, r)

            LOG.debug("VLAN-bindings: %s" % vlans_string) 

            plugged_interfaces = []
            cursor = MySQLdb.cursors.DictCursor(conn)
            cursor.execute("SELECT * FROM ports where state = 'ACTIVE'")
            rows = cursor.fetchall()
            cursor.close()
            port_bindings = {}
            ports_string = ""
            for r in rows:
                ports_string = "%s %s" % (ports_string, r)
                if r['interface_id']:
                    vlan_id = str(vlan_bindings[r['network_id']]['vlan_id'])
                    self.process_port_binding(r['uuid'], r['network_id'],
                                              r['interface_id'], vlan_id)
                    plugged_interfaces.append(r['interface_id'])
            LOG.debug("Port-bindings: %s" % ports_string) 

            self.process_unplugged_interfaces(plugged_interfaces)
            
            self.process_deleted_networks(vlan_bindings)

            conn.commit()
            time.sleep(self.polling_interval)

if __name__ == "__main__":
    usagestr = "%prog [OPTIONS] <config file>"
    parser = OptionParser(usage=usagestr)
    parser.add_option("-v", "--verbose", dest="verbose",
      action="store_true", default=False, help="turn on verbose logging")

    options, args = parser.parse_args()

    if options.verbose:
        LOG.basicConfig(level=LOG.DEBUG)
    else:
        LOG.basicConfig(level=LOG.WARN)

    if len(args) != 1:
        parser.print_help()
        sys.exit(1)

    config_file = args[0]
    config = ConfigParser.ConfigParser()
    try:
        fh = open(config_file)
        fh.close()
        config.read(config_file)
        br_name_prefix = BRIDGE_NAME_PREFIX
        physical_interface = config.get("LINUX_BRIDGE", "physical_interface")
        polling_interval = config.get("AGENT", "polling_interval")
        db_name = config.get("DATABASE", "name")
        db_user = config.get("DATABASE", "user")
        db_pass = config.get("DATABASE", "pass")
        db_host = config.get("DATABASE", "host")
    except Exception, e:
        LOG.error("Unable to parse config file \"%s\": \nException%s"
                  % (config_file, str(e)))
        sys.exit(1)

    conn = None
    try:
        LOG.info("Connecting to database \"%s\" on %s" % (db_name, db_host))
        conn = MySQLdb.connect(host=db_host, user=db_user,
          passwd=db_pass, db=db_name)
        plugin = LinuxBridgeQuantumAgent(br_name_prefix, physical_interface,
                                         polling_interval)
        plugin.daemon_loop(conn)
    finally:
        if conn:
            conn.close()

    sys.exit(0)