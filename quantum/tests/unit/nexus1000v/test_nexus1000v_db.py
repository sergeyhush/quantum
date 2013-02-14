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
from quantum.db import api as db

from quantum.plugins.cisco.db.nexus1000v_db import NetworkProfile
from quantum.plugins.cisco.db import nexus1000v_db


class NetworkProfileTests(TestCase):
    def setUp(self):
        nexus1000v_db.initialize()
        self.session = db.get_session()

    def tearDown(self):
        db.clear_db()

    def test_create_network_profile(self):
        test_profile = {'profile': {'name': 'test_profile',
                                    'segment_type': 'vlan',
                                     'multicast_ip_range': '200-300'}}
        _db_profile = nexus1000v_db.create_network_profile(test_profile)
        self.assertIsNotNone(_db_profile)
        db_profile = self.session.query(NetworkProfile).filter_by(name=test_profile['profile']['name']).one()
        self.assertIsNotNone(db_profile)
        self.assertTrue(_db_profile.id == db_profile.id and
                        _db_profile.name == db_profile.name and
                        _db_profile.segment_type == db_profile.segment_type and
                        _db_profile.segment_range == db_profile.segment_range and
                        _db_profile.multicast_ip_index == db_profile.multicast_ip_index and
                        _db_profile.multicast_ip_range == db_profile.multicast_ip_range)

    def test_delete_network_profile(self):
        self.fail("test not implemented")

    def test_update_network_profile(self):
        self.fail("test not implemented")

    def test_get_network_profile(self):
        self.fail("test not implemented")

