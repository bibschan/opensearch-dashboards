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
#   Daniel Izquierdo Cortazar <dizquierdo@bitergia.com>
#


import pandas
from elasticsearch import Elasticsearch, helpers
import datetime
#from ConfigParser import SafeConfigParser
import configparser
import re

from perceval.backends.core.git import Git

import cereslib.events

from cereslib.enrich import Gender, FileType, EmailFlag, SplitLists, MaxMin, SplitEmail, ToUTF8, MessageLogFlag, SplitEmailDomain

from cereslib.filter import FilterRows

MAPPING_GIT = {
"mappings" : {
    "item" : {
        "properties": {
            "filepath": {
                "index": "not_analyzed",
                "type": "string"
            },
            "date": {
                "type": "date"
            },
            "owner": {
                "index": "not_analyzed",
                "type": "string"
            },
            "committer": {
                "index": "not_analyzed",
                "type": "string"
            },
            "committer_date": {
                "type": "date"
            },
            "user": {
                "index": "not_analyzed",
                "type": "string"
            },
            "email": {
                "index": "not_analyzed",
                "type": "string"
            },
            "domain": {
                "index": "not_analyzed",
                "type": "string"
            }
        }
    }
}
}

def ESConnection():

    parser = configparser.ConfigParser()
    conf_file = 'settings'
    fd = open(conf_file, 'r')
    parser.readfp(fd)
    fd.close()

    sections = parser.sections()
    for section in sections:
        options = parser.options(section)
        for option in options:
            if option == 'user': user = parser.get(section, option)
            if option == 'password': password = parser.get(section, option)
            if option == 'host': host = parser.get(section, option)
            if option == 'port': port = parser.get(section, option)
            if option == 'path': path = parser.get(section, option)
            #if option == 'genderize_key': key = parser.get(section, option)


    connection = "https://" + user + ":" + password + "@" + host + ":" + port + "/" + path
    es_write = Elasticsearch([connection], verify_certs=False)

    #es_write = Elasticsearch(["127.0.0.1:9200"])
    return es_write


def analyze_git(es_write):

    #INDEX = 'git_gecko'
    #PROJECT = 'gecko'
    #git = Git("https://github.com/mozilla/gecko-dev.git", "../gecko_all_commits_final_version_no_cm_options_nobrowser_nochrome_notoolkit.log")

    #INDEX = 'git_webkit'
    #PROJECT = 'webkit'
    #git = Git("https://github.com/WebKit/webkit.git", "../webkit_final_log_no_mc_options.log")

    INDEX = "git_blink"
    PROJECT = "blink"
    git = Git("https://chromium.googlesource.com/chromium", "../blink_final_log_no_cm_options.log")

    commits = []
    cont = 1
    uniq_id = 1
    first = True
    docs = []

    all_files = pandas.DataFrame()

    es_write.indices.delete(INDEX, ignore=[400, 404])
    es_write.indices.create(INDEX, body=MAPPING_GIT)

    for item in git.fetch():
        commits.append(item)

        if cont % 15000 == 0:
            git_events = events.Git(commits)
            events_df = git_events.eventize(1)

            # Add flags if found
            message_log = MessageLogFlag(events_df)
            events_df = message_log.enrich('message')

            splitemail = SplitEmail(events_df)
            events_df = splitemail.enrich("owner")

            # Code for webkit
            # If there's a bot committing code, then we need to use the values flag
            if PROJECT == 'webkit':
                ## Fix values in the owner column
                events_df.loc[events_df["email"]=='commit-queue@webkit.org', "owner"] = events_df["values"]
                # Re-do this analysis to calculate the right email and user
                splitemail = SplitEmail(events_df)
                events_df = splitemail.enrich("owner")

            # Code for Blink
            # If there's a flag, then we need to update the owner
            if PROJECT == 'blink':
                events_df.loc[(events_df["values"]=='') ^ True, "owner"] = events_df["values"]
                splitemail = SplitEmail(events_df)
                events_df = splitemail.enrich("owner")

            splitdomain = SplitEmailDomain(events_df)
            events_df = splitdomain.enrich("email")
            #events_df.drop("message", axis=1, inplace=True)

            # Add project information
            events_df["project"] = PROJECT

            test = events_df.to_dict("index")

            docs = []
            for i in test.keys():
                header = {
                      "_index": INDEX,
                      "_type": "item",
                      "_id": int(uniq_id),
                      "_source": test[i]
                      }
                docs.append(header)
                uniq_id = uniq_id + 1

            helpers.bulk(es_write, docs)

            commits = []
        cont = cont + 1

    helpers.bulk(es_write, docs)


def main():

    es_write = ESConnection()

    analyze_git(es_write)

if __name__ == "__main__":
    main()
