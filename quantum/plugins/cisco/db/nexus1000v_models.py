# Copyright 2013, Cisco Systems, Inc.
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
# @author: Sergey Sudakovich, Cisco Systems, Inc.

from sqlalchemy import Column, String, Integer, Enum, Boolean

from quantum.db import model_base
from quantum.db import models_v2

SEGMENT_TYPE = Enum('vlan', 'vxlan')
PROFILE_TYPE = Enum('network', 'policy')
# use this to indicate that tenant_id was not yet set
TENANT_ID_NOT_SET = '01020304-0506-0708-0901-020304050607'


class N1kvVlanAllocation(model_base.BASEV2):
    """Represents allocation state of vlan_id on physical network"""
    __tablename__ = 'n1kv_vlan_allocations'

    physical_network = Column(String(64), nullable=False, primary_key=True)
    vlan_id = Column(Integer, nullable=False, primary_key=True,
                     autoincrement=False)
    allocated = Column(Boolean, nullable=False)

    def __init__(self, physical_network, vlan_id):
        self.physical_network = physical_network
        self.vlan_id = vlan_id
        self.allocated = False

    def __repr__(self):
        return "<VlanAllocation(%s,%d,%s)>" % (self.physical_network,
                                               self.vlan_id, self.allocated)

class N1kvVxlanAllocation(model_base.BASEV2):
    """Represents allocation state of vxlan_id"""
    __tablename__ = 'n1kv_vxlan_allocations'

    vxlan_id = Column(Integer, nullable=False, primary_key=True,
                      autoincrement=False)
    allocated = Column(Boolean, nullable=False)

    def __init__(self, vxlan_id):
        self.vxlan_id = vxlan_id
        self.allocated = False

    def __repr__(self):
        return "<VxlanAllocation(%d,%s)>" % (self.vxlan_id, self.allocated)

class N1kvVxlanEndpoint(model_base.BASEV2):
    """Represents vxlan endpoint in RPC mode"""
    __tablename__ = 'n1kv_vxlan_endpoints'

    ip_address = Column(String(64), primary_key=True)
    id = Column(Integer, nullable=False)

    def __init__(self, ip_address, id):
        self.ip_address = ip_address
        self.id = id

    def __repr__(self):
        return "<VxlanEndpoint(%s,%s)>" % (self.ip_address, self.id)

class NetworkProfile(model_base.BASEV2, models_v2.HasId):
    """
    Nexus1000V Network Profiles

        segment_type - VLAN, VXLAN
        segment_range - '<integer>-<integer>'
        multicast_ip_index - <integer>
        multicast_ip_range - '<ip>-<ip>'
    """
    __tablename__ = 'network_profiles'

    name = Column(String(255))
    segment_type = Column(SEGMENT_TYPE, nullable=False)
    segment_range = Column(String(255))
    multicast_ip_index = Column(Integer)
    multicast_ip_range = Column(String(255))

    def __init__(self, name, type, index, range):
        self.name = name
        self.segment_type = type
        self.multicast_ip_index = index
        self.multicast_ip_range = range

    def __repr__(self):
        return "<NetworkProfile (%s, %s, %s, %d, %s)>" % (self.id, self.name, self.segment_type,
                                                          self.multicast_ip_index, self.multicast_ip_range)


class PolicyProfile(model_base.BASEV2):
    """
    Nexus1000V Network Profiles

        Both 'id' and 'name' are coming from Nexus1000V switch
    """
    __tablename__ = 'policy_profiles'

    id = Column(String(36), primary_key=True)
    name = Column(String(255))

    def __init__(self, id, name):
        self.id = id
        self.name = name

    def __repr__(self):
        return "<PolicyProfile (%s, %s)>" % (self.id, self.name)


class ProfileBinding(model_base.BASEV2):
    """ Represents a binding of Network Profile or Policy Profile to tenant_id"""
    __tablename__ = 'profile_bindings'

    profile_type = Column(PROFILE_TYPE, primary_key=True)
    tenant_id = Column(String(36), primary_key=True, default=TENANT_ID_NOT_SET)
    profile_id = Column(String(36), primary_key=True)

    def __init__(self, profile_type, tenant_id, profile_id):
        self.profile_type = profile_type
        self.tenant_id = tenant_id
        self.profile_id = profile_id

    def __repr__(self):
        return "<ProfileBinding (%s, %s, %s)>" % (self.profile_type, self.tenant_id, self.profile_id)