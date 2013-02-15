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

import logging

from sqlalchemy.orm import exc
from quantum.common import exceptions
from sqlalchemy.sql import and_
from quantum.db import models_v2



from quantum.extensions import profile
from nexus1000v_models import NetworkProfile, PolicyProfile, ProfileBinding, N1kvVxlanAllocation, N1kvVxlanEndpoint
import quantum.db.api as db
from quantum.plugins.cisco.common import cisco_exceptions


LOG = logging.getLogger(__name__)


def initialize():
    """Establish database connection and load models"""
    db.configure_db()


def create_network_profile(profile):
    """
     Create Network Profile

    :param profile:
    :return:
    """
    LOG.debug("create_network_profile()")
    # _profile = profile['profile']
    _validate_network_profile(profile)
    session = db.get_session()
    with session.begin(subtransactions=True):
        net_profile = NetworkProfile(profile['name'], profile['segment_type'], 0, profile['multicast_ip_range'])
        session.add(net_profile)
        return net_profile


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
    # _profile = profile['profile']
    with session.begin(subtransactions=True):
        _profile = get_network_profile(id)
        _profile.update(profile)
        session.merge(_profile)
        return _profile


def get_network_profile(id, fields=None):
    """
    Get Network Profile
    :param context:
    :param id:
    :param fields:
    :return:
    """
    LOG.debug("get_network_profile()")
    session = db.get_session()
    try:
        profile = session.query(NetworkProfile).filter_by(id=id).one()
        return profile
    except exc.NoResultFound:
        raise cisco_exceptions.ProfileIdNotFound(profile_id=id)


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
        profiles = (session.query(NetworkProfile).all())
        return profiles
    except exc.NoResultFound:
        return []


def _validate_network_profile(profile):
    """
    Validate Network Profile object
    :param profile:
    :return:
    """
    pass


def create_policy_profile(profile):
    """
     Create Policy Profile

    :param profile:
    :return:
    """
    LOG.debug("create_policy_profile()")
    # _profile = profile['profile']
    _validate_network_profile(profile)
    session = db.get_session()
    with session.begin(subtransactions=True):
        p_profile = PolicyProfile(profile['id'], profile['name'])
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
    # _profile = profile['profile']
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
        profile = session.query(PolicyProfile).filter_by(id=id).one()
        return profile
    except exc.NoResultFound:
        raise cisco_exceptions.ProfileIdNotFound(profile_id=id)


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
        profiles = (session.query(PolicyProfile).all())
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
        raise exceptions.QuantumException("Invalid profile type")
    session = db.get_session()
    with session.begin(subtransactions=True):
        binding = ProfileBinding(profile_type, profile_id, tenant_id)
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
        binding = session.query(ProfileBinding).filter_by(tenant_id=tenant_id, profile_id=profile_id).one()
        return binding
    except exc.NoResultFound:
        raise exceptions.QuantumException("Profile-Tenant binding not found")
    except exc.MultipleResultsFound:
        raise exceptions.QuantumException("Profile-Tenant binding must be unique")

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

def release_vxlan(session, vxlan_id, vxlan_id_ranges):
    with session.begin(subtransactions=True):
        try:
            alloc = (session.query(N1kvVxlanAllocation).
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

def reserve_vxlan(session, profile):
    seg_min, seg_max = profile.get_segment_range(session)
    segment_type = 'vxlan'
    physical_network = ""

    with session.begin(subtransactions=True):
        try:
            alloc = (session.query(N1kvVxlanAllocation).filter(and_(N1kvVxlanAllocation.vxlan_id >= seg_min,
                                                                    N1kvVxlanAllocation.vxlan_id <= seg_max,
                                                                    N1kvVxlanAllocation.allocated == False)).first())
            segment_id = alloc.vxlan_id
            alloc.allocated = True
            return (physical_network, segment_type,
                    segment_id, profile.get_multicast_ip(session))
        except exc.NoResultFound:
            raise cisco_exceptions.VxlanIdInUse(vxlan_id=segment_id)

def reserve_specific_vxlan(session, vxlan_id):
    with session.begin(subtransactions=True):
        try:
            alloc = (session.query(N1kvVxlanAllocation).
                     filter_by(vxlan_id=vxlan_id).
                     one())
            if alloc.allocated:
                raise cisco_exceptions.VxlanIdInUse(vxlan_id=vxlan_id)
            LOG.debug("reserving specific vxlan %s from pool" % vxlan_id)
            alloc.allocated = True
        except exc.NoResultFound:
            LOG.debug("reserving specific vxlan %s outside pool" % vxlan_id)
            alloc = N1kvVxlanAllocation(vxlan_id)
            alloc.allocated = True
            session.add(alloc)

def get_vxlan_allocation(vxlan_id):
    session = db.get_session()
    try:
        alloc = (session.query(N1kvVxlanAllocation).
                 filter_by(vxlan_id=vxlan_id).
                 one())
        return alloc
    except exc.NoResultFound:
        return

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
        allocs = (session.query(N1kvVxlanAllocation).all())
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
            alloc = N1kvVxlanAllocation(vxlan_id)
            session.add(alloc)


def _generate_vxlan_id(session):
    try:
        vxlans = session.query(N1kvVxlanEndpoint).all()
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
        vxlan = (session.query(N1kvVxlanEndpoint).
                 filter_by(ip_address=ip).one())
    except exc.NoResultFound:
        id = _generate_vxlan_id(session)
        vxlan = N1kvVxlanEndpoint(ip, id)
        session.add(vxlan)
        session.flush()
    return vxlan

def get_vxlan_endpoints():
    """

    :return:
    """
    session = db.get_session()
    try:
        vxlans = session.query(N1kvVxlanEndpoint).all()
    except exc.NoResultFound:
        return []
    return [{'id': vxlan.id,
             'ip_address': vxlan.ip_address} for vxlan in vxlans]

def get_port(port_id):
    """

    :param port_id:
    :return:
    """
    session = db.get_session()
    try:
        port = session.query(models_v2.Port).filter_by(id=port_id).one()
    except exc.NoResultFound:
        port = None
    return port


def set_port_status(port_id, status):
    """

    :param port_id:
    :param status:
    :return:
    """
    session = db.get_session()
    try:
        port = session.query(models_v2.Port).filter_by(id=port_id).one()
        port['status'] = status
        session.merge(port)
        session.flush()
    except exc.NoResultFound:
        raise exceptions.PortNotFound(port_id=port_id)


def set_port_status(port_id, status):
    """

    :param port_id:
    :param status:
    :return:
    """
    session = db.get_session()
    try:
        port = session.query(models_v2.Port).filter_by(id=port_id).one()
        port['status'] = status
        session.merge(port)
        session.flush()
    except exc.NoResultFound:
        raise exceptions.PortNotFound(port_id=port_id)


