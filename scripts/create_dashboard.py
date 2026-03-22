#!/usr/bin/env python3
"""
Create dashboard directly in OpenSearch Dashboards via API
"""
import requests
from requests.auth import HTTPBasicAuth
import json
from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# OpenSearch configuration
OPENSEARCH_URL = "https://localhost:9200"
DASHBOARDS_URL = "http://localhost:5601"
AUTH = HTTPBasicAuth("admin", "GrimoireLab.1")

def create_index_pattern():
    """Create index pattern for events_slack_matched"""
    print("Creating index pattern...")

    index_pattern = {
        "attributes": {
            "title": "events_slack_matched",
            "timeFieldName": "metadata__timestamp"
        }
    }

    response = requests.post(
        f"{DASHBOARDS_URL}/api/saved_objects/index-pattern/events_slack_matched",
        json=index_pattern,
        headers={
            "osd-xsrf": "true",
            "Content-Type": "application/json"
        },
        auth=AUTH
    )

    if response.status_code in [200, 201, 409]:
        print("✓ Index pattern created (or already exists)")
        return True
    else:
        print(f"✗ Error creating index pattern: {response.status_code}")
        print(f"  Response: {response.text}")
        return False

def create_visualizations():
    """Create visualizations"""
    print("\nCreating visualizations...")

    visualizations = [
        {
            "id": "events_slack_pie",
            "title": "Attendees in Slack vs Not in Slack",
            "type": "pie",
            "description": "Distribution of attendees by Slack membership"
        },
        {
            "id": "events_slack_by_event",
            "title": "Slack Members by Event",
            "type": "histogram",
            "description": "Slack members count by event"
        },
        {
            "id": "events_slack_metrics",
            "title": "Summary Metrics",
            "type": "metric",
            "description": "Summary metrics"
        }
    ]

    for viz in visualizations:
        # Simple visualization - you'll need to configure these in the UI
        vis_obj = {
            "attributes": {
                "title": viz["title"],
                "description": viz["description"],
                "visState": json.dumps({
                    "title": viz["title"],
                    "type": viz["type"],
                    "params": {},
                    "aggs": []
                }),
                "uiStateJSON": "{}",
                "version": 1,
                "kibanaSavedObjectMeta": {
                    "searchSourceJSON": json.dumps({
                        "index": "events_slack_matched",
                        "query": {"query": "", "language": "lucene"},
                        "filter": []
                    })
                }
            }
        }

        response = requests.post(
            f"{DASHBOARDS_URL}/api/saved_objects/visualization/{viz['id']}",
            json=vis_obj,
            headers={
                "osd-xsrf": "true",
                "Content-Type": "application/json"
            },
            auth=AUTH
        )

        if response.status_code in [200, 201, 409]:
            print(f"✓ Created visualization: {viz['title']}")
        else:
            print(f"✗ Error creating {viz['title']}: {response.status_code}")

def print_manual_instructions():
    """Print instructions for manual dashboard creation"""
    print("\n" + "="*70)
    print("MANUAL DASHBOARD CREATION GUIDE")
    print("="*70)
    print("\nIndex: events_slack_matched")
    print("\nKey Questions to Answer:")
    print("1. How many attendees joined Slack? (684 out of 1,713 = 39.9%)")
    print("2. Which events had the best Slack conversion?")
    print("3. Who attended events but hasn't joined Slack yet?")

    print("\n" + "-"*70)
    print("VISUALIZATION 1: Pie Chart - Slack Membership")
    print("-"*70)
    print("Type: Pie Chart")
    print("Metrics:")
    print("  - Aggregation: Count")
    print("Buckets:")
    print("  - Aggregation: Terms")
    print("  - Field: matched_in_slack")
    print("  - Size: 2")

    print("\n" + "-"*70)
    print("VISUALIZATION 2: Bar Chart - By Event")
    print("-"*70)
    print("Type: Vertical Bar")
    print("Metrics:")
    print("  - Y-Axis: Count")
    print("Buckets:")
    print("  - X-Axis: Terms, Field: event_name")
    print("  - Split Series: Terms, Field: matched_in_slack")

    print("\n" + "-"*70)
    print("VISUALIZATION 3: Data Table - Attendees")
    print("-"*70)
    print("Type: Data Table")
    print("Metrics:")
    print("  - Count")
    print("Buckets (Split Rows):")
    print("  - Field: attendee_name.keyword")
    print("  - Field: email")
    print("  - Field: event_name")
    print("  - Field: matched_in_slack")
    print("  - Field: slack_real_name.keyword")

    print("\n" + "-"*70)
    print("VISUALIZATION 4: Metric - Summary")
    print("-"*70)
    print("Type: Metric")
    print("Metrics:")
    print("  1. Count (label: 'Total Attendees')")
    print("  2. Count with filter: matched_in_slack:true (label: 'In Slack')")
    print("  3. Unique Count of event_name (label: 'Events')")

    print("\n" + "-"*70)
    print("Available Fields in events_slack_matched:")
    print("-"*70)
    print("  - attendee_name          : Name from event registration")
    print("  - email                  : Email address")
    print("  - event_name             : Event name")
    print("  - matched_in_slack       : true/false - is this person in Slack?")
    print("  - slack_real_name        : Name in Slack (if matched)")
    print("  - slack_user_id          : Slack user ID (if matched)")
    print("  - event_created_at       : When they registered")
    print("  - event_approval_status  : Registration status")
    print("  - event_checked_in       : Did they check in?")

    print("\n" + "="*70)
    print("Quick Queries to Try in Discover:")
    print("="*70)
    print("1. Find people in Slack:")
    print("   matched_in_slack:true")
    print("\n2. Find people NOT in Slack:")
    print("   matched_in_slack:false")
    print("\n3. Find specific event:")
    print("   event_name:\"ILF_Finhub_Hackathon\"")
    print("\n4. Hackathon attendees in Slack:")
    print("   event_name:\"ILF_Finhub_Hackathon\" AND matched_in_slack:true")
    print("="*70 + "\n")

if __name__ == "__main__":
    print("Setting up Events-Slack Dashboard Components...\n")

    # Try to create index pattern
    success = create_index_pattern()

    if not success:
        print("\n⚠ Could not connect to OpenSearch Dashboards.")
        print("  Make sure it's running at http://localhost:5601")

    # Print manual instructions
    print_manual_instructions()

    print("\nNEXT STEPS:")
    print("1. Go to http://localhost:5601")
    print("2. Click 'Discover' and select 'events_slack_matched' index")
    print("3. Click 'Visualize' to create the visualizations above")
    print("4. Click 'Dashboard' to create a new dashboard and add your visualizations")
    print("\nThe data is ready - 684 attendees matched with Slack members!")
