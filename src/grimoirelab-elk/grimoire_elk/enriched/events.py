# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2023 Bitergia
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
#   Bibiana Souza <bibiana@bitergia.com>
#

import logging

from .enrich import Enrich, metadata
from ..elastic_mapping import Mapping as BaseMapping
from grimoirelab_toolkit.datetime import str_to_datetime

logger = logging.getLogger(__name__)


class Mapping(BaseMapping):

    @staticmethod
    def get_elastic_mappings(es_major):
        """Get Elasticsearch mapping.

        :param es_major: major version of Elasticsearch, as string
        :returns:        dictionary with a key, 'items', with the mapping
        """

        mapping = """
        {
            "properties": {
                "name": {
                    "type": "text",
                    "fielddata": true,
                    "fields": {
                        "keyword": {
                            "type": "keyword"
                        }
                    }
                },
                "email": {
                    "type": "keyword"
                },
                "event_name": {
                    "type": "text",
                    "fielddata": true,
                    "fields": {
                        "keyword": {
                            "type": "keyword"
                        }
                    }
                },
                "event_date": {
                    "type": "date"
                },
                "status": {
                    "type": "keyword"
                }
           }
        } """

        return {"items": mapping}


class EventsEnrich(Enrich):
    """Events enrichment class for event attendee data"""

    mapping = Mapping

    def get_identities(self, item):
        """Return the identities from an item"""

        identity = self.get_sh_identity(item)
        yield identity

    def get_sh_identity(self, item, identity_field=None):
        """Extract identity information for SortingHat"""

        attendee = item['data']

        identity = {
            'username': None,
            'email': attendee.get('email', None),
            'name': attendee.get('name', None)
        }

        return identity

    def get_field_author(self):
        """Return the field that contains author information"""
        return 'name'

    @metadata
    def get_rich_item(self, item):
        """Enrich event attendee item for OpenSearch"""

        eitem = {}

        # Copy standard raw fields
        self.copy_raw_fields(self.RAW_FIELDS_COPY, item, eitem)

        # Get the actual data
        attendee = item['data']

        # Core attendee fields
        eitem['name'] = attendee.get('name')
        eitem['email'] = attendee.get('email')
        eitem['event_name'] = attendee.get('event_name')
        eitem['source_file'] = attendee.get('source_file')
        eitem['status'] = attendee.get('status')

        # Event date handling
        event_date = attendee.get('event_date')
        if event_date:
            try:
                eitem['event_date'] = str_to_datetime(event_date).isoformat()
            except Exception as e:
                logger.warning(f"Could not parse event_date '{event_date}': {e}")
                eitem['event_date'] = None
        else:
            eitem['event_date'] = None

        # Add all raw data fields under 'raw_' prefix for flexibility
        raw_data = attendee.get('raw_data', {})
        for key, value in raw_data.items():
            # Skip fields we've already processed
            if key not in ['name', 'email', 'event_name', 'status', 'event_date']:
                eitem[f'raw_{key}'] = value

        # Add SortingHat identity enrichment
        if self.sortinghat:
            eitem.update(self.get_item_sh(item))

        # Add project mapping if available
        if self.prjs_map:
            eitem.update(self.get_item_project(eitem))

        # Use event_date if available, otherwise use metadata time
        grimoire_date = eitem.get('event_date')
        if not grimoire_date:
            grimoire_date = item.get('metadata__updated_on')

        # Add grimoire fields
        eitem.update(self.get_grimoire_fields(grimoire_date, "event"))

        # Add repository labels and metadata filters
        self.add_repository_labels(eitem)
        self.add_metadata_filter_raw(eitem)

        return eitem
