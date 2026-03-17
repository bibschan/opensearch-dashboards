# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2019 Bitergia
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Authors:
#     Daniel Izquierdo <dizquierdo@bitergia.com>
#     Alberto Perez <alpgarcia@bitergia.com>
#

import os
import sys
import unittest

if '..' not in sys.path:
    sys.path.insert(0, '..')

import json

from cereslib.events.events import Git

from grimoire_elk.utils import get_connectors


class TestEvents(unittest.TestCase):
    """ Unit tests for Enrich classes
    """

    def setUp(self):
        self.__tests_dir = os.path.dirname(os.path.realpath(__file__))
        self.__events_dir = os.path.join(self.__tests_dir, "data/events/")
        self.connectors = get_connectors()

    def test_GitEvents(self):
        """ Test several cases for the PairProgramming class
        """

        connector = "git"

        with open(os.path.join(self.__events_dir, connector + ".json")) as f:
            items = json.load(f)

        enrich_backend = self.connectors[connector][2](json_projects_map="./data/projects_map.json")
        enrich_backend.sortinghat = True
        events = Git(items, enrich_backend)

        events_df = events.eventize(1)

        self.assertFalse(events_df.empty)
        self.assertEqual(len(events_df), 6)
        self.assertEqual(len(events_df.columns), 28)
        self.assertIn("metadata__timestamp", events_df)
        self.assertIn("metadata__updated_on", events_df)
        self.assertIn("metadata__enriched_on", events_df)
        self.assertIn("grimoire_creation_date", events_df)
        self.assertIn("project", events_df)
        self.assertIn("project_1", events_df)
        self.assertIn("perceval_uuid", events_df)
        self.assertIn("author_id", events_df)
        self.assertIn("author_org_name", events_df)
        self.assertIn("author_name", events_df)
        self.assertIn("author_uuid", events_df)
        self.assertIn("author_domain", events_df)
        self.assertIn("author_user_name", events_df)
        self.assertIn("author_bot", events_df)
        self.assertIn("author_multi_org_names", events_df)
        self.assertIn("id", events_df)
        self.assertIn("date", events_df)
        self.assertIn("owner", events_df)
        self.assertIn("committer", events_df)
        self.assertIn("committer_date", events_df)
        self.assertIn("tz", events_df)
        self.assertIn("repository", events_df)
        self.assertIn("message", events_df)
        self.assertIn("hash", events_df)
        self.assertIn("git_author_domain", events_df)

        events_df = events.eventize(2)

        self.assertFalse(events_df.empty)
        self.assertEqual(len(events_df), 10)
        self.assertEqual(len(events_df.columns), 30)
        self.assertIn("eventtype", events_df)
        self.assertIn("date", events_df)
        self.assertIn("owner", events_df)
        self.assertIn("committer", events_df)
        self.assertIn("committer_date", events_df)
        self.assertIn("tz", events_df)
        self.assertIn("repository", events_df)
        self.assertIn("message", events_df)
        self.assertIn("hash", events_df)
        self.assertIn("git_author_domain", events_df)
        self.assertIn("files", events_df)
        self.assertIn("fileaction", events_df)
        self.assertIn("filepath", events_df)
        self.assertIn("addedlines", events_df)
        self.assertIn("removedlines", events_df)
