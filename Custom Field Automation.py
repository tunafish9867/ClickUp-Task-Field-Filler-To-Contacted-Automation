import requests
from datetime import datetime
import json
import time

# === Configuration ===
API_TOKEN = "pk_XXXXXXXXXXXXXXX"  # 🔑 Your ClickUp API token
SPACE_ID = "90185483551"          # Your ClickUp space ID
FIELD_ID_FIRST = "3cc68963-5098-48c7-b293-cc37bc599084"   # Custom field for first status
FIELD_ID_CURRENT = "3b95375e-eb94-48f5-8223-fb5f308de582"  # Custom field for current status

# Base URL and headers
BASE_URL = "https://api.clickup.com/api/v2"
HEADERS = {
    "Authorization": API_TOKEN,
    "Content-Type": "application/json"
}
def safe_request(method, endpoint, **kwargs):
    """Safely send API requests with error handling."""
    url = f"{BASE_URL}/{endpoint}"
    try:
        response = requests.request(method, url, headers=HEADERS, **kwargs)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"⚠️ Error ({method} {endpoint}): {e}")
        return {}

# === Helper Functions ===
def get_lists_in_space(space_id):
    """Retrieve all lists (inside and outside folders) in a given space."""
    lists = []
    folder_data = safe_request("GET", f"space/{space_id}/folder")
    for folder in folder_data.get("folders", []):
        lists.extend(folder.get("lists", []))
    standalone_data = safe_request("GET", f"space/{space_id}/list")
    lists.extend(standalone_data.get("lists", []))
    return lists

def get_tasks_from_list(list_id):
    """Fetch all tasks from a ClickUp list (handles pagination)."""
    tasks, page = [], 0
    while True:
        data = safe_request("GET", f"list/{list_id}/task?page={page}")
        if not data or not data.get("tasks"):
            break
        tasks.extend(data["tasks"])
        page += 1
    return tasks

def get_time_in_status(task_id):
    """Retrieve the time in each status for a given task."""
    data = safe_request("GET", f"task/{task_id}/time_in_status")
    if not data:
        return {"current_status": {}, "first_status": {}}

    current = data.get("current_status", {})
    first = data.get("status_history", [{}])[0]

    return {
        "current_status": {
            "status": current.get("status"),
            "since": current.get("total_time", {}).get("since")
        },
        "first_status": {
            "status": first.get("status"),
            "since": first.get("total_time", {}).get("since")
        }
    }

def update_custom_field(task_id, field_id, value):
    """Update a task’s custom field."""
    payload = {"value": value}
    resp = requests.post(
        f"{BASE_URL}/task/{task_id}/field/{field_id}",
        headers=HEADERS,
        data=json.dumps(payload)
    )
    if resp.status_code == 200:
        print(f"✅ Updated {task_id} → {field_id}")
    else:
        print(f"❌ Failed to update {task_id}: {resp.text}")


# === Main Code ===
lists = get_lists_in_space(SPACE_ID)
updated_count = 0

for lst in lists:
    print(f"\n📋 List: {lst['name']}")
    for task in get_tasks_from_list(lst["id"]):
        task_id, task_name = task["id"], task["name"]
        time_info = get_time_in_status(task_id)

        current_status = time_info["current_status"].get("status", "").lower()
        first_status = time_info["first_status"].get("status", "").lower()
        current_since = time_info["current_status"].get("since")
        first_since = time_info["first_status"].get("since")

        if current_status == "contacted":
            updated_count += 1
            if first_status == "new leads" and first_since:
                update_custom_field(task_id, FIELD_ID_FIRST, first_since)
            if current_since:
                update_custom_field(task_id, FIELD_ID_CURRENT, current_since)
            time.sleep(0.5)

            print(f"🧱 {task_name}: first={first_status}, current={current_status}")

print(f"\n✅ Total tasks updated: {updated_count}")