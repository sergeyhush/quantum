# Copyright (c) 2012 OpenStack, LLC.
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from unittest2 import TestCase
from sqlalchemy.orm import exc

from quantum.db import api as db
from quantum.plugins.cisco.db.nexus1000v_db import NetworkProfile
from quantum.plugins.cisco.db import nexus1000v_db


TEST_PROFILE = {'profile': {'name': 'test_profile',
                            'segment_type': 'vlan',
                            'multicast_ip_range': '200-300'}}
TEST_PROFILE_1 = {'profile': {'name': 'test_profile_1'}}


class NetworkProfileTests(TestCase):
    def setUp(self):
        nexus1000v_db.initialize()
        self.session = db.get_session()

    def tearDown(self):
        db.clear_db()

    def _create_test_profile_if_not_there(self, profile=TEST_PROFILE):
        try:
            _profile = self.session.query(NetworkProfile).filter_by(name=profile['profile']['name']).one()
        except exc.NoResultFound:
            _profile = nexus1000v_db.create_network_profile(profile)
        return _profile

    def test_create_network_profile(self):
        _db_profile = nexus1000v_db.create_network_profile(TEST_PROFILE)
        self.assertIsNotNone(_db_profile)
        db_profile = self.session.query(NetworkProfile).filter_by(name=TEST_PROFILE['profile']['name']).one()
        self.assertIsNotNone(db_profile)
        self.assertTrue(_db_profile.id == db_profile.id and
                        _db_profile.name == db_profile.name and
                        _db_profile.segment_type == db_profile.segment_type and
                        _db_profile.segment_range == db_profile.segment_range and
                        _db_profile.multicast_ip_index == db_profile.multicast_ip_index and
                        _db_profile.multicast_ip_range == db_profile.multicast_ip_range)

    def test_delete_network_profile(self):
        try:
            profile = self.session.query(NetworkProfile).filter_by(name=TEST_PROFILE['profile']['name']).one()
        except exc.NoResultFound:
            profile = nexus1000v_db.create_network_profile(TEST_PROFILE)

        nexus1000v_db.delete_network_profile(profile.id)
        try:
            _profile = self.session.query(NetworkProfile).filter_by(name=TEST_PROFILE['profile']['name']).one()
        except exc.NoResultFound:
            pass
        else:
            self.fail("Network Profile (%s) was not deleted" % TEST_PROFILE['profile']['name'])

    def test_update_network_profile(self):
        profile = self._create_test_profile_if_not_there()
        updated_profile = nexus1000v_db.update_network_profile(profile.id, TEST_PROFILE_1)
        try:
            _profile = self.session.query(NetworkProfile).filter_by(name=profile['profile']['name']).one()
        except exc.NoResultFound:
            pass
        else:
            self.fail("Profile name was not updated")
        self.assertEqual(updated_profile.name, TEST_PROFILE_1['profile']['name'])
        self.fail("test not implemented")

    def test_get_network_profile(self):
        profile = self._create_test_profile_if_not_there()
        got_profile = nexus1000v_db.get_network_profile(profile.id)
        self.assertEqual(profile.id, got_profile.id)
        self.assertEqual(profile.name, got_profile.name)


