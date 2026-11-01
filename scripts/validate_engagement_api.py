import json
import os
import sys
from urllib.request import urlopen

import django

# Add the backend directory to Python's import path.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
sys.path.insert(0, BACKEND_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db.models import Count, F, Sum
from analytics.models import Interaction


BASE_URL = "http://127.0.0.1:8000"
API_URL = f"{BASE_URL}/api/analytics/engagement-by-course/"

# Fetch every API page.
api_results = []
url = API_URL

while url:
    with urlopen(url) as response:
        if response.status != 200:
            raise RuntimeError(
                f"API request failed: HTTP {response.status}"
            )

        data = json.load(response)

    api_results.extend(data["results"])

    next_url = data["next"]

    # DRF returns an absolute URL for the next page.
    url = next_url

# Calculate the same metrics directly from the database.
db_results = list(
    Interaction.objects.values(
        code_module=F("enrollment__course__code_module"),
        code_presentation=F(
            "enrollment__course__code_presentation"
        ),
    )
    .annotate(
        total_clicks=Sum("total_clicks"),
        interaction_records=Count("id"),
    )
    .order_by("code_module", "code_presentation")
)

# Summarize API results.
api_clicks = sum(row["total_clicks"] for row in api_results)
api_records = sum(row["interaction_records"] for row in api_results)

# Summarize database results.
db_clicks = sum(row["total_clicks"] or 0 for row in db_results)
db_records = sum(row["interaction_records"] for row in db_results)

print("API groups:", len(api_results))
print("API clicks:", api_clicks)
print("API records:", api_records)

print("Database groups:", len(db_results))
print("Database clicks:", db_clicks)
print("Database records:", db_records)

# Compare every course-presentation group.
api_by_course = {
    (row["code_module"], row["code_presentation"]): (
        row["total_clicks"],
        row["interaction_records"],
    )
    for row in api_results
}

db_by_course = {
    (row["code_module"], row["code_presentation"]): (
        row["total_clicks"],
        row["interaction_records"],
    )
    for row in db_results
}

print(
    "All course-level results match:",
    api_by_course == db_by_course,
)