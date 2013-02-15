# Copyright (c) 2012 Cisco Systems, Inc.
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
#
# @author: Abhishek Raut, Cisco Systems, Inc.
# @author: Rudrajit Tapadar, Cisco Systems, Inc.
# @author: Sergey Sudakovich, Cisco Systems, Inc.


from quantum.api import extensions
from quantum.api.v2 import attributes



#TODO this was copied over - fix for network and policy profiles
PROFILE_ID = 'n1kv:profile_id'
MULTICAST_IP = 'n1kv:multicast_ip'

EXTENDED_ATTRIBUTES_2_0 = {
    'networks': {
        PROFILE_ID: {'allow_post': True, 'allow_put': True,
                     'validate': {'type:regex': attributes.UUID_PATTERN},
                     'default': attributes.ATTR_NOT_SPECIFIED,
                     'is_visible': True},
        MULTICAST_IP: {'allow_post': True, 'allow_put': True,
                       'default': attributes.ATTR_NOT_SPECIFIED,
                       'is_visible': True},
        },
    'ports': {
        PROFILE_ID: {'allow_post': True, 'allow_put': True,
                     'validate': {'type:regex': attributes.UUID_PATTERN},
                     'default': attributes.ATTR_NOT_SPECIFIED,
                     'is_visible': True}
    }
}

class Nexus1000vNetworkProfile(extensions.ExtensionDescriptor):
    @classmethod
    def get_name(cls):
        return "Nexus 1000V Network Profile"

    @classmethod
    def get_alias(cls):
        return "network_profile"

    @classmethod
    def get_description(cls):
        return "Exposes network profile"

    @classmethod
    def get_namespace(cls):
        return "http://docs.openstack.org/ext/network_profile/api/v2.0"

    @classmethod
    def get_updated(cls):
        return "2013-02-14T10:00:00-00:00"

    def get_extended_resources(self, version):
        return {}
        # We might not need them
        # if version == "2.0":
        #     return EXTENDED_ATTRIBUTES_2_0
        # else:
        #     return {}


class Nexus1000vPolicyProfile(extensions.ExtensionDescriptor):
    @classmethod
    def get_name(cls):
        return "Nexus 1000V Policy Profile"

    @classmethod
    def get_alias(cls):
        return "policy_profile"

    @classmethod
    def get_description(cls):
        return "Exposes policy profile"

    @classmethod
    def get_namespace(cls):
        return "http://docs.openstack.org/ext/policy_profile/api/v2.0"

    @classmethod
    def get_updated(cls):
        return "2013-02-14T10:00:00-00:00"

    def get_extended_resources(self, version):
        return {}
        # We might not need them
        # if version == "2.0":
        #     return EXTENDED_ATTRIBUTES_2_0
        # else:
        #     return {}