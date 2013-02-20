# vim: tabstop=4 shiftwidth=4 softtabstop=4
# Copyright 2011 Nicira Networks, Inc.
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
# @author: Aaron Rosen, Nicira Networks, Inc.
# @author: Bob Kukura, Red Hat, Inc.
# @author: Aruna Kushwaha, Cisco Systems Inc.
# @author: Abhishek Raut, Cisco Systems Inc.
# @author: Rudrajit Tapadar, Cisco Systems Inc.
# @author: Sergey Sudakovich, Cisco Systems Inc.


import logging

from sqlalchemy.orm import exc
from sqlalchemy.sql import and_

from quantum.common import exceptions as q_exc
from quantum.db import models_v2
import quantum.db.api as db
from quantum.plugins.cisco.common import cisco_constants as const
from quantum.plugins.cisco.db import n1kv_models_v2
from quantum.plugins.cisco.db import n1kv_profile_db
from quantum.plugins.cisco.common import cisco_exceptions as c_exc
from quantum.extensions import profile

LOG = logging.getLogger(__name__)


def initialize():
    db.configure_db()


def get_network_binding(session, network_id):
    session = session or db.get_session()
    try:
        binding = (session.query(n1kv_models_v2.N1kvNetworkBinding).
                   filter_by(network_id=network_id).
                   one())
        return binding
    except exc.NoResultFound:
        return


def add_network_binding(session, network_id, network_type,
                 physical_network, segmentation_id, multicast_ip, profile_id):
    """
    Explanation for the parameters

    network_type : Whether its a VLAN or VXLAN based network
    physical_network : Only applicable for VLAN networks. It represents a
                       L2 Domain
    segmentation_id : VLAN / VXLAN ID
    multicast IP : VXLAN technology needs a multicast IP to be associated
                   with every VXLAN ID to deal with broadcast packets. A
                   single Multicast IP can be shared by multiple VXLAN IDs.
    profile_id : Network Profile ID based by which this network is created
    """
    with session.begin(subtransactions=True):
        binding = n1kv_models_v2.N1kvNetworkBinding(network_id, network_type,
            physical_network,
            segmentation_id, multicast_ip, profile_id)
        session.add(binding)


def get_port_binding(session, port_id):
    session = session or db.get_session()
    try:
        binding = (session.query(n1kv_models_v2.N1kvPortBinding).
                   filter_by(port_id=port_id).
                   one())
        return binding
    except exc.NoResultFound:
        return


def add_port_binding(session, port_id, profile_id):
    with session.begin(subtransactions=True):
        binding = n1kv_models_v2.N1kvPortBinding(port_id, profile_id)
        session.add(binding)


def sync_vlan_allocations(network_vlan_ranges):
    """Synchronize vlan_allocations table with configured VLAN ranges"""

    session = db.get_session()
    with session.begin():
        # process vlan ranges for each physical network separately
        for physical_network, vlan_ranges in network_vlan_ranges.iteritems():

            # determine current configured allocatable vlans for this
            # physical network
            vlan_ids = set()
            for vlan_range in vlan_ranges:
                vlan_ids |= set(xrange(vlan_range[0], vlan_range[1] + 1))

            # remove from table unallocated vlans not currently allocatable
            allocs = (session.query(n1kv_models_v2.N1kvVlanAllocation).
                        filter_by(physical_network=physical_network).
                        all())
            for alloc in allocs:
                try:
                    # see if vlan is allocatable
                    vlan_ids.remove(alloc.vlan_id)
                except KeyError:
                    # it's not allocatable, so check if its allocated
                    if not alloc.allocated:
                        # it's not, so remove it from table
                        LOG.debug("removing vlan %s on physical network "
                                    "%s from pool" %
                                    (alloc.vlan_id, physical_network))
                        session.delete(alloc)

            # add missing allocatable vlans to table
            for vlan_id in sorted(vlan_ids):
                alloc = n1kv_models_v2.N1kvVlanAllocation(physical_network,
                                                         vlan_id)
                session.add(alloc)


def get_vlan_allocation(physical_network, vlan_id):
    session = db.get_session()
    try:
        alloc = (session.query(n1kv_models_v2.N1kvVlanAllocation).
                 filter_by(physical_network=physical_network,
            vlan_id=vlan_id).
                 one())
        return alloc
    except exc.NoResultFound:
        return


def reserve_vlan(session, profile):
    seg_min, seg_max = profile.get_segment_range(session)
    segment_type = 'vlan'

    with session.begin(subtransactions=True):
        try:
            alloc = (session.query(n1kv_models_v2.N1kvVlanAllocation).
                    filter(and_(
                        n1kv_models_v2.N1kvVlanAllocation.vlan_id >= seg_min,
                        n1kv_models_v2.N1kvVlanAllocation.vlan_id <= seg_max,
                        n1kv_models_v2.N1kvVlanAllocation.allocated == False)
                        )).first()
            segment_id = alloc.vlan_id
            physical_network = alloc.physical_network
            alloc.allocated = True
            return (physical_network, segment_type, segment_id, '0.0.0.0')
        except exc.NoResultFound:
            raise q_exc.VlanIdInUse(vlan_id=segment_id,
                    physical_network=segment_type)


def reserve_vxlan(session, profile):
    seg_min, seg_max = profile.get_segment_range(session)
    segment_type = 'vxlan'
    physical_network = ""

    with session.begin(subtransactions=True):
        try:
            alloc = (session.query(n1kv_models_v2.N1kvVxlanAllocation).
                    filter(and_(
                       n1kv_models_v2.N1kvVxlanAllocation.vxlan_id >=
                           seg_min,
                       n1kv_models_v2.N1kvVxlanAllocation.vxlan_id <=
                           seg_max,
                       n1kv_models_v2.N1kvVxlanAllocation.allocated == False)
                       ).first())
            segment_id = alloc.vxlan_id
            alloc.allocated = True
            return (physical_network, segment_type,
                    segment_id, profile.get_multicast_ip(session))
        except exc.NoResultFound:
            raise c_exc.VxlanIdInUse(vxlan_id=segment_id)


def alloc_network(session, profile_id):
    with session.begin(subtransactions=True):
        try:
            profile = (session.query(n1kv_profile_db.N1kvProfile_db).
                    filter_by(id=profile_id).one())
                    #filter_by(profile_id=profile_id).one())   @@@@@@@@@@
            if profile:
                if profile.segment_type == 'vlan':
                    return reserve_vlan(session, profile)
                else:
                    return reserve_vxlan(session, profile)
        except q_exc.NotFound:
            LOG.debug("N1kvProfile_db not found")


def reserve_specific_vlan(session, physical_network, vlan_id):
    with session.begin(subtransactions=True):
        try:
            alloc = (session.query(n1kv_models_v2.N1kvVlanAllocation).
                     filter_by(physical_network=physical_network,
                vlan_id=vlan_id).
                     one())
            if alloc.allocated:
                if vlan_id == const.FLAT_VLAN_ID:
                    raise q_exc.FlatNetworkInUse(
                        physical_network=physical_network)
                else:
                    raise q_exc.VlanIdInUse(vlan_id=vlan_id,
                        physical_network=physical_network)
            LOG.debug("reserving specific vlan %s on physical network %s "
                      "from pool" % (vlan_id, physical_network))
            alloc.allocated = True
        except exc.NoResultFound:
            LOG.debug("reserving specific vlan %s on physical network %s "
                      "outside pool" % (vlan_id, physical_network))
            alloc = n1kv_models_v2.N1kvVlanAllocation(physical_network,
                                                      vlan_id)
            alloc.allocated = True
            session.add(alloc)


def release_vlan(session, physical_network, vlan_id, network_vlan_ranges):
    with session.begin(subtransactions=True):
        try:
            alloc = (session.query(n1kv_models_v2.N1kvVlanAllocation).
                     filter_by(physical_network=physical_network,
                vlan_id=vlan_id).
                     one())
            alloc.allocated = False
            inside = False
            for vlan_range in network_vlan_ranges.get(physical_network, []):
                if vlan_id >= vlan_range[0] and vlan_id <= vlan_range[1]:
                    inside = True
                    break
            if not inside:
                session.delete(alloc)
            LOG.debug("releasing vlan %s on physical network %s %s pool" %
                      (vlan_id, physical_network,
                       inside and "to" or "outside"))
        except exc.NoResultFound:
            LOG.warning("vlan_id %s on physical network %s not found" %
                        (vlan_id, physical_network))


def sync_vxlan_allocations(vxlan_id_ranges):
    """Synchronize vxlan_allocations table with configured vxlan ranges"""

    # determine current configured allocatable vxlans
    vxlan_ids = set()
    for vxlan_id_range in vxlan_id_ranges:
        tun_min, tun_max = vxlan_id_range
        if tun_max + 1 - tun_min > 1000000:
            LOG.error("Skipping unreasonable vxlan ID range %s:%s" %
                      vxlan_id_range)
        else:
            vxlan_ids |= set(xrange(tun_min, tun_max + 1))

    session = db.get_session()
    with session.begin():
        # remove from table unallocated vxlans not currently allocatable
        allocs = (session.query(n1kv_models_v2.N1kvVxlanAllocation).all())
        for alloc in allocs:
            try:
                # see if vxlan is allocatable
                vxlan_ids.remove(alloc.vxlan_id)
            except KeyError:
                # it's not allocatable, so check if its allocated
                if not alloc.allocated:
                    # it's not, so remove it from table
                    LOG.debug("removing vxlan %s from pool" %
                                alloc.vxlan_id)
                    session.delete(alloc)

        # add missing allocatable vxlans to table
        for vxlan_id in sorted(vxlan_ids):
            alloc = n1kv_models_v2.N1kvVxlanAllocation(vxlan_id)
            session.add(alloc)


def get_vxlan_allocation(vxlan_id):
    session = db.get_session()
    try:
        alloc = (session.query(n1kv_models_v2.N1kvVxlanAllocation).
                 filter_by(vxlan_id=vxlan_id).
                 one())
        return alloc
    except exc.NoResultFound:
        return


def reserve_specific_vxlan(session, vxlan_id):
    with session.begin(subtransactions=True):
        try:
            alloc = (session.query(n1kv_models_v2.N1kvVxlanAllocation).
                     filter_by(vxlan_id=vxlan_id).
                     one())
            if alloc.allocated:
                raise c_exc.VxlanIdInUse(vxlan_id=vxlan_id)
            LOG.debug("reserving specific vxlan %s from pool" % vxlan_id)
            alloc.allocated = True
        except exc.NoResultFound:
            LOG.debug("reserving specific vxlan %s outside pool" % vxlan_id)
            alloc = n1kv_models_v2.N1kvVxlanAllocation(vxlan_id)
            alloc.allocated = True
            session.add(alloc)


def release_vxlan(session, vxlan_id, vxlan_id_ranges):
    with session.begin(subtransactions=True):
        try:
            alloc = (session.query(n1kv_models_v2.N1kvVxlanAllocation).
                     filter_by(vxlan_id=vxlan_id).
                     one())
            alloc.allocated = False
            inside = False
            for vxlan_id_range in vxlan_id_ranges:
                if (vxlan_id >= vxlan_id_range[0]
                    and vxlan_id <= vxlan_id_range[1]):
                    inside = True
                    break
            if not inside:
                session.delete(alloc)
            LOG.debug("releasing vxlan %s %s pool" %
                      (vxlan_id, inside and "to" or "outside"))
        except exc.NoResultFound:
            LOG.warning("vxlan_id %s not found" % vxlan_id)


def get_port(port_id):
    session = db.get_session()
    try:
        port = session.query(models_v2.Port).filter_by(id=port_id).one()
    except exc.NoResultFound:
        port = None
    return port


def set_port_status(port_id, status):
    session = db.get_session()
    try:
        port = session.query(models_v2.Port).filter_by(id=port_id).one()
        port['status'] = status
        session.merge(port)
        session.flush()
    except exc.NoResultFound:
        raise q_exc.PortNotFound(port_id=port_id)


def get_vxlan_endpoints():
    session = db.get_session()
    try:
        vxlans = session.query(n1kv_models_v2.N1kvVxlanEndpoint).all()
    except exc.NoResultFound:
        return []
    return [{'id': vxlan.id,
             'ip_address': vxlan.ip_address} for vxlan in vxlans]


def _generate_vxlan_id(session):
    try:
        vxlans = session.query(n1kv_models_v2.N1kvVxlanEndpoint).all()
    except exc.NoResultFound:
        return 0
    vxlan_ids = ([vxlan['id'] for vxlan in vxlans])
    if vxlan_ids:
        id = max(vxlan_ids)
    else:
        id = 0
    return id + 1


def add_vxlan_endpoint(ip):
    session = db.get_session()
    try:
        vxlan = (session.query(n1kv_models_v2.N1kvVxlanEndpoint).
                  filter_by(ip_address=ip).one())
    except exc.NoResultFound:
        id = _generate_vxlan_id(session)
        vxlan = n1kv_models_v2.N1kvVxlanEndpoint(ip, id)
        session.add(vxlan)
        session.flush()
    return vxlan


def get_vm_network(profile_id, network_id):
    """Retrieve a vm_network based on profile and network id"""
    session = db.get_session()
    try:
        vm_network = (session.query(n1kv_models_v2.N1kVmNetwork).
                      filter_by(profile_id=profile_id).
                      filter_by(network_id=network_id).one())
        return vm_network
    except exc.NoResultFound:
        return None


def add_vm_network(name, profile_id, network_id):
    session = db.get_session()
    with session.begin(subtransactions=True):
        vm_network = n1kv_models_v2.N1kVmNetwork(name, profile_id, network_id)
        session.add(vm_network)


def create_network_profile(profile):
    """
     Create Network Profile

    :param profile:
    :return:
    """
    LOG.debug("create_network_profile()")
    session = db.get_session()
    _validate_network_profile_obj(profile)
    with session.begin(subtransactions=True):
        if profile['segment_type'] == 'vlan':
            net_profile = n1kv_models_v2.NetworkProfile(name=profile['name'], segment_type=profile['segment_type'],
                                                        segment_range=profile['segment_range'])
        elif profile['segment_type'] == 'vxlan':
            net_profile = n1kv_models_v2.NetworkProfile(name=profile['name'], segment_type=profile['segment_type'],
                                                        mcast_ip_index=0, mcast_ip_range=profile['multicast_ip_range'])
        session.add(net_profile)
        return net_profile


def _validate_network_profile_obj(profile):
    """
    Validate Network profile object that was passed in
    :param profile:
    """
    if profile['segment_type'] not in ('vlan', 'vxlan'):
        raise q_exc.QuantumException('Profile type must be VLAN or VxLAN')
    #TODO Finish all validations
    if profile['segment_type'] == 'vlan':
        pass
    elif profile['segment_type'] == 'vxlan':
        pass

def delete_network_profile(id):
    """
    Delete Network Profile

    :param id:
    :return:
    """
    LOG.debug("delete_network_profile()")
    session = db.get_session()
    profile = get_network_profile(id)
    with session.begin(subtransactions=True):
        session.delete(profile)


def update_network_profile(id, profile):
    """
    Update Network Profile

    :param id:
    :param profile:
    :return:
    """
    LOG.debug("update_network_profile()")
    session = db.get_session()
    with session.begin(subtransactions=True):
        _profile = get_network_profile(id)
        _profile.update(profile)
        session.merge(_profile)
        return _profile


def get_network_profile(id, fields=None):
    """
    Get Network Profile
    :param id:
    :param fields:
    :return:
    """
    LOG.debug("get_network_profile()")
    session = db.get_session()
    try:
        profile = session.query(n1kv_models_v2.NetworkProfile).filter_by(id=id).one()
        return profile
    except exc.NoResultFound:
        raise c_exc.ProfileIdNotFound(profile_id=id)


def get_all_network_profiles(tenant_id):
    """
    List all network profiles
    :param tenant_id:
    :return:
    """
    LOG.debug("get_all_network_profiles()")
    session = db.get_session()
    try:
        #TODO Filter by tenant id
        profiles = (session.query(n1kv_models_v2.NetworkProfile).all())
        return profiles
    except exc.NoResultFound:
        return []

def create_policy_profile(profile):
    """
     Create Policy Profile

    :param profile:
    :return:
    """
    LOG.debug("create_policy_profile()")
    session = db.get_session()
    with session.begin(subtransactions=True):
        p_profile = n1kv_models_v2.PolicyProfile(id=profile['id'], name=profile['name'])
        session.add(p_profile)
        return p_profile


def delete_policy_profile(id):
    """
    Delete Policy Profile

    :param id:
    :return:
    """
    LOG.debug("delete_policy_profile()")
    session = db.get_session()
    profile = get_policy_profile(id)
    with session.begin(subtransactions=True):
        session.delete(profile)

def update_policy_profile(id, profile):
    """

    :param context:
    :param id:
    :param profile:
    :return:
    """
    LOG.debug("update_policy_profile()")
    session = db.get_session()
    with session.begin(subtransactions=True):
        _profile = get_policy_profile(id)
        _profile.update(profile)
        session.merge(_profile)
        return _profile


def get_policy_profile(id, fields=None):
    """
    Get Policy Profile

    :param id:
    :param fields:
    :return:
    """
    LOG.debug("get_policy_profile()")
    session = db.get_session()
    try:
        profile = session.query(n1kv_models_v2.PolicyProfile).filter_by(id=id).one()
        return profile
    except exc.NoResultFound:
        raise c_exc.ProfileIdNotFound(profile_id=id)


def get_all_policy_profiles(tenant_id):
    """
    List all policy profiles
    :param tenant_id:
    :return:
    """
    LOG.debug("get_all_policy_profiles()")
    session = db.get_session()
    try:
        #TODO Filter by tenant id
        profiles = (session.query(n1kv_models_v2.PolicyProfile).all())
        return profiles
    except exc.NoResultFound:
        return []

def create_profile_binding(tenant_id, profile_id, profile_type):
    """
    Create Network/Policy Profile binding
    :param tenant_id:
    :param profile_id:
    :param profile_type:
    :return:
    """
    if  profile_type not in ['network', 'policy']:
        raise q_exc.QuantumException("Invalid profile type")
    session = db.get_session()
    with session.begin(subtransactions=True):
        binding = n1kv_models_v2.ProfileBinding(profile_type=profile_type, profile_id=profile_id, tenant_id=tenant_id)
        session.add(binding)
        return binding


def get_profile_binding(tenant_id, profile_id):
    """
    Get Network/Policy Profile - Tenant binding
    :param tenant_id:
    :param profile_id:
    :return:
    """
    LOG.debug("get_profile_binding()")
    session = db.get_session()
    try:
        binding = session.query(n1kv_models_v2.ProfileBinding).filter_by(tenant_id=tenant_id, profile_id=profile_id).one()
        return binding
    except exc.NoResultFound:
        raise q_exc.QuantumException("Profile-Tenant binding not found")
    except exc.MultipleResultsFound:
        raise q_exc.QuantumException("Profile-Tenant binding must be unique")

def delete_profile_binding(tenant_id, profile_id):
    """
    Delete Policy Binding
    :param tenant_id:
    :param profile_id:
    :return:
    """
    LOG.debug("delete_profile_binding()")
    session = db.get_session()
    binding = get_profile_binding(tenant_id, profile_id)
    with session.begin(subtransactions=True):
        session.delete(binding)

class NetworkProfile_db_mixin(object):

    def _make_network_profile_dict(self, profile, fields=None):
        res = {'id': profile['id'],
               'name': profile['name'],
               'segment_type': profile['segment_type'],
               'segment_range': profile['segment_range'],
               'multicast_ip_index': profile['multicast_ip_index'],
               'multicast_ip_range': profile['multicast_ip_range']}
        return self._fields(res, fields)

    def create_network_profile(self, context, network_profile):
        p = network_profile['network_profile']
        tenant_id = self._get_tenant_id_for_create(context, p)
        net_profile = create_network_profile(p)
        create_profile_binding(tenant_id, net_profile.id, 'network')
        return self._make_network_profile_dict(net_profile)

    def delete_network_profile(self, context, id):
        delete_network_profile(id)

    def get_network_profile(self, context, id, fields=None):
        profile = get_network_profile(id, fields)
        return self._make_network_profile_dict(profile, fields)

    def update_network_profile(self, context, id, profile):
        p = profile['networkprofile']
        return self._make_network_profile_dict(update_network_profile(id, p))

    def get_network_profiles(self, context, filters=None, fields=None):
        # profiles = get_all_network_profiles()
        # return profiles
        return self._get_collection(context, n1kv_models_v2.NetworkProfile,
                                    self._make_network_profile_dict,
                                    filters=filters, fields=fields)


class PolicyProfile_db_mixin(object):

    def _make_policy_profile_dict(self, profile, fields=None):
        res = {'id': profile['id'], 'name': profile['name']}
        return self._fields(res, fields)

    def get_policy_profile(self, context, id, fields=None):
        # return get_policy_profile(id, fields)
        profile = get_policy_profile(id, fields)
        return self._make_policy_profile_dict(profile, fields)

    def get_policy_profiles(self, context, filters=None, fields=None):
        # return get_all_policy_profiles()
        return self._get_collection(context, n1kv_models_v2.PolicyProfile,
                                    self._make_policy_profile_dict,
                                    filters=filters, fields=fields)

    def _replace_fake_tanant_id_with_real(self, context):
        """
        Replace fake tenant id for all Policy Profile binding with real admin tenant ID
        :param context:
        :return:
        """
        if context.is_admin and context.tenant_id:
            tenant_id = context.tenant_id
            session = db.get_session()
            with session.begin(subtransactions=True):
                session.query(n1kv_models_v2.ProfileBinding).\
                    filter_by(tenant_id=n1kv_models_v2.TENANT_ID_NOT_SET).\
                    update({'tenant_id': tenant_id})


    def _add_policy_profile(self, profile_name, profile_id, tenant_id=None):
        """
        Add Policy profile and tenant binding
        :param profile_name:
        :param profile_id:
        :param tenant_id:
        :return:
        """
        profile = {'id': profile_id, 'name': profile_name}
        tenant_id = tenant_id or n1kv_models_v2.TENANT_ID_NOT_SET
        create_policy_profile(profile)
        create_profile_binding(tenant_id, profile['id'], 'policy')