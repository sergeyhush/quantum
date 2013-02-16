
from quantum.api.v2 import attributes as attr
from quantum.api.v2 import base
from quantum.api import extensions
from quantum import manager

# Attribute Map
RESOURCE_ATTRIBUTE_MAP = {
    'policy-profiles': {
        'id': {'allow_post': False, 'allow_put': False,
               'validate': {'type:regex': attr.UUID_PATTERN},
               'is_visible': True},
        'name': {'allow_post': False, 'allow_put': False,
                 'is_visible': True, 'default': ''},
        },
    }


class NetworkProfile(object):

    @classmethod
    def get_name(cls):
        return "Cisco N1kv Network Profiles"

    @classmethod
    def get_alias(cls):
        return "policy_profile"

    @classmethod
    def get_description(cls):
        return ("Profile includes the type of profile for N1kv")

    @classmethod
    def get_namespace(cls):
        return "http://docs.openstack.org/ext/n1kv/api/v2.0"

    @classmethod
    def get_updated(cls):
        return "2012-07-20T10:00:00-00:00"

    @classmethod
    def get_resources(cls):
        """ Returns Ext Resources """
        exts = []
        resource_name = "policy-profile"
        collection_name = resource_name + "s"
        plugin = manager.QuantumManager.get_plugin()
        params = RESOURCE_ATTRIBUTE_MAP.get(collection_name, dict())
        member_actions = {}
        controller = base.create_resource(collection_name,
                                          resource_name,
                                          plugin, params,
                                          member_actions=member_actions)
        return [extensions.ResourceExtension(collection_name,
                                             controller,
                                             member_actions=member_actions)]