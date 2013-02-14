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
from quantum.plugins.cisco.db.nexus1000v_db import NetworkProfile, PolicyProfile, ProfileBinding
from quantum.plugins.cisco.db import nexus1000v_db

TEST_NETWORK_PROFILE = {'name': 'test_profile', 'segment_type': 'vlan', 'multicast_ip_range': '200-300'}
TEST_POLICY_PROFILE = {'id': '4a417990-76fb-11e2-bcfd-0800200c9a66', 'name': 'test_policy_profile'}


class NetworkProfileTests(TestCase):
    def setUp(self):
        nexus1000v_db.initialize()
        self.session = db.get_session()

    def tearDown(self):
        db.clear_db()

    def _create_test_profile_if_not_there(self, profile=TEST_NETWORK_PROFILE):
        try:
            _profile = self.session.query(NetworkProfile).filter_by(name=profile['name']).one()
        except exc.NoResultFound:
            _profile = nexus1000v_db.create_network_profile(profile)
        return _profile

    def test_create_network_profile(self):
        _db_profile = nexus1000v_db.create_network_profile(TEST_NETWORK_PROFILE)
        self.assertIsNotNone(_db_profile)
        db_profile = self.session.query(NetworkProfile).filter_by(name=TEST_NETWORK_PROFILE['name']).one()
        self.assertIsNotNone(db_profile)
        self.assertTrue(_db_profile.id == db_profile.id and
                        _db_profile.name == db_profile.name and
                        _db_profile.segment_type == db_profile.segment_type and
                        _db_profile.segment_range == db_profile.segment_range and
                        _db_profile.multicast_ip_index == db_profile.multicast_ip_index and
                        _db_profile.multicast_ip_range == db_profile.multicast_ip_range)

    def test_delete_network_profile(self):
        try:
            profile = self.session.query(NetworkProfile).filter_by(name=TEST_NETWORK_PROFILE['name']).one()
        except exc.NoResultFound:
            profile = nexus1000v_db.create_network_profile(TEST_NETWORK_PROFILE)

        nexus1000v_db.delete_network_profile(profile.id)
        try:
            _profile = self.session.query(NetworkProfile).filter_by(name=TEST_NETWORK_PROFILE['name']).one()
        except exc.NoResultFound:
            pass
        else:
            self.fail("Network Profile (%s) was not deleted" % TEST_NETWORK_PROFILE['name'])

    def test_update_network_profile(self):
        TEST_PROFILE_1 = {'name': 'test_profile_1'}
        profile = self._create_test_profile_if_not_there()
        updated_profile = nexus1000v_db.update_network_profile(profile.id, TEST_PROFILE_1)
        try:
            self.session.query(NetworkProfile).filter_by(name=profile.name).one()
        except exc.NoResultFound:
            pass
        else:
            self.fail("Profile name was not updated")
        self.assertEqual(updated_profile.name, TEST_PROFILE_1['name'])

    def test_get_network_profile(self):
        profile = self._create_test_profile_if_not_there()
        got_profile = nexus1000v_db.get_network_profile(profile.id)
        self.assertEqual(profile.id, got_profile.id)
        self.assertEqual(profile.name, got_profile.name)

    def test_get_all_network_profiles(self):
        test_profiles = [{'name': 'test_profile1', 'segment_type': 'vlan', 'multicast_ip_range': '200-210'},
                         {'name': 'test_profile2', 'segment_type': 'vlan', 'multicast_ip_range': '211-220'},
                         {'name': 'test_profile3', 'segment_type': 'vlan', 'multicast_ip_range': '221-230'},
                         {'name': 'test_profile4', 'segment_type': 'vlan', 'multicast_ip_range': '231-240'},
                         {'name': 'test_profile5', 'segment_type': 'vlan', 'multicast_ip_range': '241-250'},
                         {'name': 'test_profile6', 'segment_type': 'vlan', 'multicast_ip_range': '251-260'},
                         {'name': 'test_profile7', 'segment_type': 'vlan', 'multicast_ip_range': '261-270'}]
        [nexus1000v_db.create_network_profile(p) for p in test_profiles]
        #TODO Fix this test to work with real tenant_td
        profiles = nexus1000v_db.get_all_network_profiles(None)
        self.assertEqual(len(test_profiles), len(profiles))


class PolicyProfileTests(TestCase):
    def setUp(self):
        nexus1000v_db.initialize()
        self.session = db.get_session()

    def tearDown(self):
        db.clear_db()

    def test_create_policy_profile(self):
        _db_profile = nexus1000v_db.create_policy_profile(TEST_POLICY_PROFILE)
        self.assertIsNotNone(_db_profile)
        db_profile = self.session.query(PolicyProfile).filter_by(name=TEST_POLICY_PROFILE['name']).one()
        self.assertIsNotNone(db_profile)
        self.assertTrue(_db_profile.id == db_profile.id and _db_profile.name == db_profile.name)

    def test_delete_policy_profile(self):
        self.fail("test not implemented")

    def test_update_policy_profile(self):
        self.fail("test not implemented")

    def test_get_policy_profile(self):
        self.fail("test not implemented")

    def test_get_all_policy_profiles(self):
        self.fail("test not implemented")


class ProfileBindingTests(TestCase):
    def setUp(self):
        nexus1000v_db.initialize()
        self.session = db.get_session()

    def tearDown(self):
        db.clear_db()

    def _create_test_binding_if_not_there(self, tenant_id, profile_id, profile_type):
        try:
            _binding = self.session.query(ProfileBinding).filter_by(profile_type=profile_type, tenant_id=tenant_id,
                                                                    profile_id=profile_id).one()
        except exc.NoResultFound:
            _binding = nexus1000v_db.create_profile_binding(tenant_id, profile_id, profile_type)
        return _binding

    def test_create_profile_binding(self):
        test_tenant_id = "d434dd90-76ec-11e2-bcfd-0800200c9a66"
        test_profile_id = "dd7b9741-76ec-11e2-bcfd-0800200c9a66"
        test_profile_type = "network"
        nexus1000v_db.create_profile_binding(test_tenant_id, test_profile_id, test_profile_type)
        try:
            self.session.query(ProfileBinding).filter_by(profile_type=test_profile_type, tenant_id=test_tenant_id,
                                                         profile_id=test_profile_id).one()
        except exc.NoResultFound:
            self.fail("Could not create Profile Binding")

    def test_get_profile_binding(self):
        test_tenant_id = "d434dd90-76ec-11e2-bcfd-0800200c9a66"
        test_profile_id = "dd7b9741-76ec-11e2-bcfd-0800200c9a66"
        test_profile_type = "network"
        self._create_test_binding_if_not_there(test_tenant_id, test_profile_id, test_profile_type)
        binding = nexus1000v_db.get_profile_binding(test_tenant_id,test_profile_id)
        self.assertEqual(binding.tenant_id, test_tenant_id)
        self.assertEqual(binding.profile_id, test_profile_id)
        self.assertEqual(binding.profile_type, test_profile_type)

    def test_delete_profile_binding(self):
        self.fail("test not implemented")
