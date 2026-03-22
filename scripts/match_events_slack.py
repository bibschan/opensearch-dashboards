#!/usr/bin/env python3
"""
Match event attendees with Slack workspace members
"""
import requests
from requests.auth import HTTPBasicAuth
import json
from datetime import datetime
from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# OpenSearch configuration
OPENSEARCH_URL = "https://localhost:9200"
AUTH = HTTPBasicAuth("admin", "GrimoireLab.1")

def get_slack_members():
    """Get all unique Slack members with their emails"""
    query = {
        "size": 10000,
        "query": {
            "bool": {
                "must": [
                    {"exists": {"field": "data.user_data.profile.email"}},
                    {"term": {"data.user_data.is_bot": False}}
                ]
            }
        },
        "_source": [
            "data.user_data.profile.email",
            "data.user_data.profile.real_name",
            "data.user_data.profile.display_name",
            "data.user_data.id",
            "data.user_data.updated"
        ]
    }

    response = requests.get(
        f"{OPENSEARCH_URL}/slack_demo_raw/_search",
        json=query,
        auth=AUTH,
        verify=False
    )

    result = response.json()
    if "error" in result:
        print(f"Error querying Slack data: {result}")
        return {}

    slack_members = {}
    seen_user_ids = set()
    for hit in result.get("hits", {}).get("hits", []):
        user_data = hit["_source"]["data"]["user_data"]
        user_id = user_data.get("id")

        # Skip duplicates and bots
        if user_id in seen_user_ids:
            continue
        seen_user_ids.add(user_id)

        email = user_data.get("profile", {}).get("email", "").lower().strip()
        if email:
            slack_members[email] = {
                "slack_user_id": user_data.get("id"),
                "slack_real_name": user_data.get("profile", {}).get("real_name"),
                "slack_display_name": user_data.get("profile", {}).get("display_name"),
                "slack_joined_timestamp": user_data.get("updated")
            }

    return slack_members

def get_event_attendees():
    """Get all event attendees"""
    query = {
        "size": 10000,
        "query": {"match_all": {}},
        "_source": [
            "email",
            "name",
            "event_name",
            "source_file",
            "raw_created_at",
            "raw_approval_status",
            "raw_checked_in_at",
            "author_name",
            "uuid"
        ]
    }

    response = requests.get(
        f"{OPENSEARCH_URL}/events_demo_enriched/_search",
        json=query,
        auth=AUTH,
        verify=False
    )

    return response.json()["hits"]["hits"]

def create_matched_documents():
    """Create enriched documents matching events with Slack data"""
    print("Fetching Slack members...")
    slack_members = get_slack_members()
    print(f"Found {len(slack_members)} unique Slack members with emails")

    print("\nFetching event attendees...")
    attendees = get_event_attendees()
    print(f"Found {len(attendees)} event attendee records")

    matched_docs = []
    matched_count = 0
    unmatched_count = 0

    for attendee in attendees:
        source = attendee["_source"]
        email = source.get("email", "").lower().strip()

        # Create base document
        doc = {
            "uuid": source.get("uuid"),
            "email": email,
            "attendee_name": source.get("name") or source.get("author_name"),
            "event_name": source.get("event_name"),
            "event_source_file": source.get("source_file"),
            "event_created_at": source.get("raw_created_at"),
            "event_approval_status": source.get("raw_approval_status"),
            "event_checked_in": source.get("raw_checked_in_at", "") != "",
            "matched_in_slack": False,
            "metadata__timestamp": datetime.utcnow().isoformat() + "+00:00",
            "grimoire_creation_date": datetime.utcnow().isoformat() + "+00:00",
            "project": "interledger-community"
        }

        # Check if email matches a Slack member
        if email in slack_members:
            slack_info = slack_members[email]
            doc.update({
                "matched_in_slack": True,
                "slack_user_id": slack_info["slack_user_id"],
                "slack_real_name": slack_info["slack_real_name"],
                "slack_display_name": slack_info["slack_display_name"],
                "slack_joined_timestamp": slack_info["slack_joined_timestamp"]
            })
            matched_count += 1
        else:
            unmatched_count += 1

        matched_docs.append(doc)

    print(f"\n=== Matching Results ===")
    print(f"Total attendees: {len(attendees)}")
    print(f"Matched with Slack: {matched_count} ({100*matched_count/len(attendees):.1f}%)")
    print(f"Not found in Slack: {unmatched_count} ({100*unmatched_count/len(attendees):.1f}%)")

    return matched_docs

def index_documents(docs, index_name="events_slack_matched"):
    """Index the matched documents to OpenSearch"""
    print(f"\nIndexing {len(docs)} documents to {index_name}...")

    # Delete index if exists
    requests.delete(
        f"{OPENSEARCH_URL}/{index_name}",
        auth=AUTH,
        verify=False
    )

    # Create index with mapping
    mapping = {
        "mappings": {
            "properties": {
                "email": {"type": "keyword"},
                "attendee_name": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                "event_name": {"type": "keyword"},
                "event_source_file": {"type": "keyword"},
                "event_created_at": {"type": "date"},
                "event_approval_status": {"type": "keyword"},
                "event_checked_in": {"type": "boolean"},
                "matched_in_slack": {"type": "boolean"},
                "slack_user_id": {"type": "keyword"},
                "slack_real_name": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                "slack_display_name": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                "slack_joined_timestamp": {"type": "date", "format": "epoch_second"},
                "metadata__timestamp": {"type": "date"},
                "grimoire_creation_date": {"type": "date"},
                "project": {"type": "keyword"}
            }
        }
    }

    response = requests.put(
        f"{OPENSEARCH_URL}/{index_name}",
        json=mapping,
        auth=AUTH,
        verify=False
    )

    if response.status_code not in [200, 201]:
        print(f"Error creating index: {response.text}")
        return

    # Bulk index documents
    bulk_data = []
    for doc in docs:
        bulk_data.append(json.dumps({"index": {"_index": index_name}}))
        bulk_data.append(json.dumps(doc))

    bulk_body = "\n".join(bulk_data) + "\n"

    response = requests.post(
        f"{OPENSEARCH_URL}/_bulk",
        data=bulk_body,
        headers={"Content-Type": "application/x-ndjson"},
        auth=AUTH,
        verify=False
    )

    result = response.json()
    if result.get("errors"):
        print("Some errors occurred during indexing:")
        for item in result["items"]:
            if "error" in item.get("index", {}):
                print(f"  {item['index']['error']}")
    else:
        print(f"Successfully indexed {len(docs)} documents!")

    # Print sample matched records
    print("\n=== Sample Matched Attendees (in Slack) ===")
    matched_samples = [d for d in docs if d["matched_in_slack"]][:5]
    for doc in matched_samples:
        print(f"  • {doc['attendee_name']} ({doc['email']}) -> Slack: {doc.get('slack_real_name')} - Event: {doc['event_name']}")

    print(f"\n=== Sample Unmatched Attendees (not in Slack) ===")
    unmatched_samples = [d for d in docs if not d["matched_in_slack"]][:5]
    for doc in unmatched_samples:
        print(f"  • {doc['attendee_name']} ({doc['email']}) - Event: {doc['event_name']}")

if __name__ == "__main__":
    docs = create_matched_documents()
    index_documents(docs)
    print("\n✓ Done! You can now create a dashboard using the 'events_slack_matched' index.")
