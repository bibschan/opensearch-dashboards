# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2020 Bitergia
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
#     Bibiana Souza <bibiana@bitergia.com>
#

import csv
import logging
import os
from datetime import datetime

from grimoirelab_toolkit.datetime import str_to_datetime

from ...backend import (Backend,
                        BackendCommand,
                        BackendCommandArgumentParser)

CATEGORY_EVENT = "event"

logger = logging.getLogger(__name__)


class Events(Backend):
    """Events backend for Perceval.

    This class retrieves event attendee data from CSV files.
    Supports multiple CSV formats from platforms like Luma, Eventbrite, etc.
    The backend expects files to have at minimum: name and email columns.

    :param dirpath: path to directory containing CSV files
    :param tag: label used to mark the data
    :param archive: archive to store/retrieve items
    """
    version = '1.0.0'

    CATEGORIES = [CATEGORY_EVENT]

    def __init__(self, dirpath, tag=None, archive=None):
        origin = dirpath
        super().__init__(origin, tag=tag, archive=archive)
        self.dirpath = dirpath

    def fetch(self, category=CATEGORY_EVENT):
        """Fetch the event attendees from CSV files.

        :param category: the category of items to fetch

        :returns: a generator of event attendee records
        """
        kwargs = {}
        items = super().fetch(category, **kwargs)
        return items

    def fetch_items(self, category, **kwargs):
        """Fetch event attendees from CSV files.

        :param category: the category of items to fetch
        :param kwargs: backend arguments

        :returns: a generator of items
        """
        logger.info("Looking for event CSV files in '%s'", self.dirpath)

        nattendees = 0

        # Find all CSV files in the directory
        csv_files = [f for f in os.listdir(self.dirpath) if f.endswith('.csv')]

        logger.info("Found %i CSV files", len(csv_files))

        for csv_file in csv_files:
            filepath = os.path.join(self.dirpath, csv_file)
            logger.info("Processing file: %s", csv_file)

            # Extract event name from filename (remove .csv extension)
            event_name = os.path.splitext(csv_file)[0]

            with open(filepath, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)

                # Normalize column names (lowercase, strip spaces)
                reader.fieldnames = [field.lower().strip() for field in reader.fieldnames]

                for row in reader:
                    # Skip empty rows
                    if not any(row.values()):
                        continue

                    # Build attendee item
                    item = self._build_item(row, event_name, csv_file)
                    if item:
                        yield item
                        nattendees += 1

        logger.info("Total number of attendees: %i", nattendees)

    def _build_item(self, row, event_name, source_file):
        """Build an attendee item from a CSV row.

        :param row: CSV row as dictionary
        :param event_name: name of the event
        :param source_file: source CSV filename

        :returns: attendee item or None if invalid
        """
        # Try to find email field (common variations)
        email = None
        for field in ['email', 'email address', 'e-mail', 'attendee email']:
            if field in row and row[field]:
                email = row[field].strip().lower()
                break

        # Try to find name field (common variations)
        name = None
        for field in ['name', 'full name', 'attendee name', 'first name']:
            if field in row and row[field]:
                name = row[field].strip()
                break

        # If we have both first name and last name separately, combine them
        if not name and 'first name' in row and 'last name' in row:
            first = row['first name'].strip() if row['first name'] else ''
            last = row['last name'].strip() if row['last name'] else ''
            name = f"{first} {last}".strip()

        # Skip if we don't have at least email or name
        if not email and not name:
            logger.warning("Skipping row with no email or name: %s", row)
            return None

        # Build the item
        item = {
            'email': email,
            'name': name,
            'event_name': event_name,
            'source_file': source_file,
            'raw_data': dict(row)  # Keep all original fields
        }

        # Try to extract event date if available
        for field in ['event date', 'date', 'event_date', 'registered_at', 'registration date']:
            if field in row and row[field]:
                try:
                    item['event_date'] = row[field]
                except Exception:
                    pass
                break

        # Try to extract registration/ticket status
        for field in ['status', 'ticket status', 'registration status', 'attendance status']:
            if field in row and row[field]:
                item['status'] = row[field]
                break

        return item

    @classmethod
    def has_archiving(cls):
        """Returns whether it supports archiving items on the fetch process.

        :returns: this backend supports archiving
        """
        return True

    @classmethod
    def has_resuming(cls):
        """Returns whether it supports to resume the fetch process.

        :returns: this backend does not support resuming
        """
        return False

    @staticmethod
    def metadata_id(item):
        """Extracts the identifier from an event attendee item.

        Uses a combination of email and event name to create unique ID.
        """
        email = item.get('email', '')
        event = item.get('event_name', '')
        name = item.get('name', '')

        # Create unique identifier
        unique_str = f"{email}_{event}_{name}"
        return unique_str

    @staticmethod
    def metadata_updated_on(item):
        """Extracts the update time from an event item.

        Uses event_date if available, otherwise uses current time.

        :param item: item generated by the backend

        :returns: a UNIX timestamp
        """
        if 'event_date' in item:
            try:
                ts = str_to_datetime(item['event_date'])
                return ts.timestamp()
            except Exception:
                pass

        # Default to current time if no date available
        return datetime.utcnow().timestamp()

    @staticmethod
    def metadata_category(item):
        """Extracts the category from an event item.

        This backend only generates one type of item which is 'event'.
        """
        return CATEGORY_EVENT

    def _init_client(self, from_archive=False):
        """Init client (not needed for local CSV files)"""
        return None


class EventsCommand(BackendCommand):
    """Class to run Events backend from the command line."""

    BACKEND = Events

    @classmethod
    def setup_cmd_parser(cls):
        """Returns the Events argument parser."""

        parser = BackendCommandArgumentParser(cls.BACKEND,
                                              archive=True)

        # Required arguments
        parser.parser.add_argument('dirpath',
                                   help="Path to directory containing event CSV files")

        return parser
