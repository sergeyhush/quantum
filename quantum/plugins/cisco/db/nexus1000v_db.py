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

from quantum.extensions import profile
from nexus1000v_models import NetworkProfile
import quantum.db.api as db
from quantum.plugins.cisco.common import cisco_exceptions


LOG = logging.getLogger(__name__)

def initialize():
    """Establish database connection and load models"""
    db.configure_db()


def create_network_profile(profile):
    """
    Create Network Profile
    :param context:
    :param profile:
    :return:
    """
    LOG.debug("create_network_profile()")
    _profile = profile['profile']
    _validate_network_profile(_profile)
    session = db.get_session()
    with session.begin(subtransactions=True):
        net_profile = NetworkProfile(_profile['name'], _profile['segment_type'], 0, _profile['multicast_ip_range'])
        session.add(net_profile)
        return net_profile

def delete_network_profile(id):
    """
    Delete Network Profile
    :param context:
    :param id:
    :return:
    """
    LOG.debug("delete_network_profile()")
    session = db.get_session()
    profile = get_network_profile( id)
    with session.begin(subtransactions=True):
        session.delete(profile)

def update_network_profile(id, profile):
    """
    Update Network Profile
    :param context:
    :param id:
    :param profile:
    :return:
    """
    LOG.debug("update_network_profile()")
    session = db.get_session()
    _profile = profile['profile']
    with session.begin(subtransactions=True):
        profile = get_network_profile(id)
        profile.update(_profile)
        return profile

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



def _validate_network_profile(profile):
    """
    Validate Network Profile object
    :param profile:
    :return:
    """
    pass



def create_policy_profile(profile):
    """

    :param context:
    :param profile:
    :return:
    """
    pass
def delete_policy_profile(id):
    """

    :param context:
    :param id:
    :return:
    """
    pass
def update_policy_profile(id, profile):
    """

    :param context:
    :param id:
    :param profile:
    :return:
    """
    pass
def get_policy_profile(id, fields=None):
    """

    :param context:
    :param id:
    :param fields:
    :return:
    """
    pass
