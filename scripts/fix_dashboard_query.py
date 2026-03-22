#!/usr/bin/env python3
"""
Fix the dashboard query that keeps returning
"""
import requests
from requests.auth import HTTPBasicAuth
import json

DASHBOARDS_URL = "http://localhost:5601"
AUTH = HTTPBasicAuth("admin", "GrimoireLab.1")
DASHBOARD_ID = "2ca19970-259c-11f1-9fef-cdc2c821d8a6"

print("Fetching current dashboard...")
response = requests.get(
    f"{DASHBOARDS_URL}/api/saved_objects/dashboard/{DASHBOARD_ID}",
    headers={"osd-xsrf": "true"},
    auth=AUTH
)

if response.status_code != 200:
    print(f"Error fetching dashboard: {response.status_code}")
    print(response.text)
    exit(1)

dashboard = response.json()
print(f"✓ Found dashboard: {dashboard['attributes']['title']}")

# Parse the search source
search_source = json.loads(dashboard['attributes']['kibanaSavedObjectMeta']['searchSourceJSON'])
print(f"\nCurrent query: {search_source['query']}")

# Fix the query - make it empty
search_source['query'] = {
    "query": "",
    "language": "kuery"
}

# Update the dashboard
dashboard['attributes']['kibanaSavedObjectMeta']['searchSourceJSON'] = json.dumps(search_source)

print("\nUpdating dashboard with empty query...")
response = requests.put(
    f"{DASHBOARDS_URL}/api/saved_objects/dashboard/{DASHBOARD_ID}",
    headers={
        "osd-xsrf": "true",
        "Content-Type": "application/json"
    },
    json={"attributes": dashboard['attributes']},
    auth=AUTH
)

if response.status_code == 200:
    print("✓ Dashboard fixed!")
    print("\nThe search query has been permanently cleared.")
    print("Refresh your dashboard - it should now show all data!")
else:
    print(f"✗ Error updating dashboard: {response.status_code}")
    print(response.text)
