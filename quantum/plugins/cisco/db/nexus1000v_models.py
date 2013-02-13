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

from sqlalchemy import Column, String, Integer, Enum

from quantum.db import model_base
from quantum.db import models_v2


POLICY_TYPE = Enum('network', 'policy')
SEGMENT_TYPE = Enum('vlan', 'vxlan')

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
    segment_type = SEGMENT_TYPE
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


class ProfileBinding(model_base.BASEV2, models_v2.HasTenant):
    """ Represents a binding of Network Profile or Policy Profile to tenant_id"""
    __tablename__ = 'network_profile_bindings'

    policy_type = POLICY_TYPE
    network_profile_id = Column(String(36), nullable=False)

    def __init__(self, policy_type, tenant_id, network_profile_id):
        self.policy_type = policy_type
        self.tenant_id = tenant_id
        self.network_profile_id = network_profile_id

    def __repr__(self):
        return "<ProfileBinding (%s, %s, %s)>" % (self.policy_type, self.tenant_id, self.network_profile_id)