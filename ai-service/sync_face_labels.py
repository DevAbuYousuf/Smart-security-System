
import requests
import json
import os

API_URL = "http://localhost:5000/api/faces/labels"

LABELS_FILE = os.path.join(
    os.path.dirname(__file__),
    "labels.json"
)


def sync_face_labels():
    try:
        response = requests.get(API_URL, timeout=10)
        response.raise_for_status()

        result = response.json()

        if not result.get("success"):
            print("Face label sync failed:", result.get("message"))
            return False

        labels = result.get("data", {})

        with open(LABELS_FILE, "w", encoding="utf-8") as file:
            json.dump(labels, file, indent=4, ensure_ascii=False)

        print("Face labels synced successfully!")
        print("Total active persons:", len(labels))
        print(json.dumps(labels, indent=4))

        return True

    except requests.RequestException as error:
        print("API connection error:", error)

    except (OSError, ValueError) as error:
        print("File or JSON error:", error)

    return False


if __name__ == "__main__":
    sync_face_labels()
