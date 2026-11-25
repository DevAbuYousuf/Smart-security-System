
import os
import requests

API_URL = "http://localhost:5000/api/events"


def send_security_event(
    event_type,
    person_name="Unknown Person",
    status="UNAUTHORIZED",
    confidence=None,
    snapshot=None,
    camera_id="CAMERA_01",
    person_id=None,
    track_id=None
):
    payload = {
        "eventType": event_type,
        "personName": person_name,
        "status": status,
        "confidence": confidence,
        "cameraId": camera_id,
        "trackId": track_id
    }

    if person_id:
        payload["person"] = person_id

    try:
        # Upload image using multipart/form-data
        if snapshot and os.path.isfile(snapshot):

            with open(snapshot, "rb") as image_file:

                files = {
                    "snapshot": (
                        os.path.basename(snapshot),
                        image_file,
                        "image/jpeg"
                    )
                }

                response = requests.post(
                    API_URL,
                    data=payload,
                    files=files,
                    timeout=15
                )

        else:
            response = requests.post(
                API_URL,
                json=payload,
                timeout=10
            )

        response.raise_for_status()

        result = response.json()

        print("✅ Event sent to backend!")
        print("Event:", event_type)
        print("Track ID:", track_id)
        print("Snapshot:", result.get("data", {}).get("snapshot"))

        return True

    except (requests.RequestException, OSError) as error:
        print("❌ Backend upload failed:", error)
        return False
