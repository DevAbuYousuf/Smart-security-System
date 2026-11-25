
import cv2
import json
import os
import time
import queue
import threading
import requests

from datetime import datetime
from collections import deque
from ultralytics import YOLO

from camera_stream import (
    start_stream_server,
    update_frame,
    update_stats,
    stop_stream_server,
)


# =========================================================
# 1. CONFIGURATION
# =========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

BACKEND_URL = "http://localhost:5000/api/events"

CAMERA_ID = "CAMERA_01"
CAMERA_INDEX = 0

YOLO_MODEL_PATH = os.path.join(BASE_DIR, "yolo11n.pt")
FACE_MODEL_PATH = os.path.join(BASE_DIR, "face_model.yml")
LABELS_PATH = os.path.join(BASE_DIR, "labels.json")

UNKNOWN_DIR = os.path.join(BASE_DIR, "unknown_faces")
SNAPSHOT_DIR = os.path.join(BASE_DIR, "event_snapshots")

os.makedirs(UNKNOWN_DIR, exist_ok=True)
os.makedirs(SNAPSHOT_DIR, exist_ok=True)


# =========================================================
# 2. SECURITY SETTINGS
# =========================================================

CONFIDENCE_THRESHOLD = 75

MAX_FACE_VOTES = 5
AUTHORIZED_VOTES_REQUIRED = 3
UNKNOWN_VOTES_REQUIRED = 4

FACE_CHECK_INTERVAL = 0.20

UNKNOWN_SAVE_COOLDOWN = 10
AUTHORIZED_EVENT_COOLDOWN = 30

ID_TIMEOUT = 5.0

LINE_Y = 300
ENTRY_DIRECTION = "DOWN"

PERSON_CLASS_ID = 0
YOLO_CONFIDENCE = 0.45

COUNT_SMOOTHING_WINDOW = 7

REQUEST_TIMEOUT = 10


# =========================================================
# 3. LOAD YOLO MODEL
# =========================================================

print("Loading YOLO model...")

person_model = YOLO(YOLO_MODEL_PATH)

print("YOLO model loaded successfully.")


# =========================================================
# 4. LOAD FACE RECOGNITION MODEL
# =========================================================

print("Loading face recognition model...")

if not os.path.exists(FACE_MODEL_PATH):
    raise FileNotFoundError(
        "Face model not found. Run: python train_faces.py"
    )

if not os.path.exists(LABELS_PATH):
    raise FileNotFoundError(
        "labels.json not found."
    )

face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades +
    "haarcascade_frontalface_default.xml"
)

if face_cascade.empty():
    raise RuntimeError("Could not load Haar Cascade.")

recognizer = cv2.face.LBPHFaceRecognizer_create()
recognizer.read(FACE_MODEL_PATH)

with open(LABELS_PATH, "r", encoding="utf-8") as file:
    raw_labels = json.load(file)

labels = {
    int(label): name
    for label, name in raw_labels.items()
}

print("Face model loaded successfully.")
print("Registered face labels:", labels)


# =========================================================
# 5. GLOBAL VARIABLES
# =========================================================

event_queue = queue.Queue(maxsize=100)

person_states = {}

last_unknown_save = {}
last_authorized_event = {}

total_entry = 0
total_exit = 0
current_inside = 0

detection_count_history = deque(maxlen=COUNT_SMOOTHING_WINDOW)

camera = None
running = True


# =========================================================
# 6. SAVE SNAPSHOT
# =========================================================

def save_snapshot(frame, event_type, track_id):

    now = datetime.now()

    filename = (
        f"{event_type.lower()}_"
        f"{track_id}_"
        f"{now.strftime('%Y%m%d_%H%M%S_%f')}.jpg"
    )

    filepath = os.path.join(SNAPSHOT_DIR, filename)

    if cv2.imwrite(filepath, frame):
        return filepath

    return None


# =========================================================
# 7. BACKEND EVENT WORKER
# =========================================================

def backend_worker():

    while True:

        event = event_queue.get()

        if event is None:
            event_queue.task_done()
            break

        files = None

        try:

            data = {
                "eventType": event["eventType"],
                "personName": event["personName"],
                "status": event["status"],
                "cameraId": event["cameraId"],
                "trackId": str(event["trackId"])
            }

            if event.get("confidence") is not None:
                data["confidence"] = str(event["confidence"])

            snapshot_path = event.get("snapshot")

            if snapshot_path and os.path.exists(snapshot_path):

                files = {
                    "snapshot": (
                        os.path.basename(snapshot_path),
                        open(snapshot_path, "rb"),
                        "image/jpeg"
                    )
                }

            response = requests.post(
                BACKEND_URL,
                data=data,
                files=files,
                timeout=REQUEST_TIMEOUT
            )

            if response.ok:
                print("BACKEND SUCCESS:", response.status_code)
            else:
                print(
                    "BACKEND ERROR:",
                    response.status_code,
                    response.text
                )

        except requests.exceptions.RequestException as error:

            print("BACKEND CONNECTION ERROR:", error)

        except Exception as error:

            print("EVENT UPLOAD ERROR:", error)

        finally:

            if files:
                files["snapshot"][1].close()

            event_queue.task_done()


backend_thread = threading.Thread(
    target=backend_worker,
    daemon=True
)

backend_thread.start()


# =========================================================
# 8. SEND EVENT TO BACKEND
# =========================================================

def send_event(
    event_type,
    person_name,
    status,
    track_id,
    confidence=None,
    frame=None
):

    snapshot_path = None

    if frame is not None:
        snapshot_path = save_snapshot(
            frame,
            event_type,
            track_id
        )

    event = {
        "eventType": event_type,
        "personName": person_name,
        "status": status,
        "confidence": confidence,
        "trackId": track_id,
        "cameraId": CAMERA_ID,
        "snapshot": snapshot_path
    }

    try:

        event_queue.put_nowait(event)

        print(
            f"EVENT QUEUED | {event_type} | "
            f"{person_name} | Track ID: {track_id}"
        )

    except queue.Full:

        print("WARNING: Event queue is full. Event skipped.")


# =========================================================
# 9. FACE RECOGNITION
# =========================================================

def recognize_face(person_roi):

    if person_roi is None or person_roi.size == 0:
        return None

    gray = cv2.cvtColor(
        person_roi,
        cv2.COLOR_BGR2GRAY
    )

    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(80, 80)
    )

    if len(faces) == 0:
        return None

    x, y, w, h = max(
        faces,
        key=lambda face: face[2] * face[3]
    )

    face = gray[y:y+h, x:x+w]

    face = cv2.resize(
        face,
        (200, 200)
    )

    label, distance = recognizer.predict(face)

    distance = float(distance)

    if (
        distance < CONFIDENCE_THRESHOLD
        and label in labels
    ):

        return {
            "name": labels[label],
            "distance": distance,
            "face_box": (x, y, w, h),
            "face_image": face,
            "authorized": True
        }

    return {
        "name": "UNKNOWN",
        "distance": distance,
        "face_box": (x, y, w, h),
        "face_image": face,
        "authorized": False
    }


# =========================================================
# 10. CREATE PERSON STATE
# =========================================================

def create_person_state(current_time):

    return {
        "last_seen": current_time,
        "last_center_y": None,
        "last_event": 0,

        "name": None,
        "match_distance": None,

        "face_votes": [],
        "face_status": "VERIFYING",

        "last_face_check": 0
    }


# =========================================================
# 11. ENTRY / EXIT DETECTION
# =========================================================

def detect_entry_exit(track_id, center_y, state, frame):

    global total_entry
    global total_exit

    previous_y = state["last_center_y"]

    state["last_center_y"] = center_y

    if previous_y is None:
        return

    crossed_down = (
        previous_y < LINE_Y
        and center_y >= LINE_Y
    )

    crossed_up = (
        previous_y > LINE_Y
        and center_y <= LINE_Y
    )

    event_type = None

    if ENTRY_DIRECTION == "DOWN":

        if crossed_down:
            event_type = "ENTRY"

        elif crossed_up:
            event_type = "EXIT"

    else:

        if crossed_up:
            event_type = "ENTRY"

        elif crossed_down:
            event_type = "EXIT"

    if event_type is None:
        return

    current_time = time.time()

    if current_time - state["last_event"] < 1.5:
        return

    state["last_event"] = current_time

    if event_type == "ENTRY":
        total_entry += 1

    elif event_type == "EXIT":
        total_exit += 1

    print(
        f"{event_type} DETECTED | "
        f"Track ID: {track_id} | "
        f"Previous Y: {previous_y} | "
        f"Current Y: {center_y}"
    )

    send_event(
        event_type=event_type,
        person_name=state["name"] or "Unverified Person",
        status="UNVERIFIED",
        track_id=track_id,
        frame=frame
    )


# =========================================================
# 12. FACE VOTING SYSTEM
# =========================================================

def process_face_recognition(
    frame,
    person_roi,
    x1,
    y1,
    state,
    track_id,
    current_time
):

    display_name = "VERIFYING"
    box_color = (0, 165, 255)

    if state["face_status"] == "AUTHORIZED":

        display_name = state["name"] or "AUTHORIZED"
        box_color = (0, 255, 0)

    elif state["face_status"] == "UNKNOWN":

        display_name = "UNKNOWN"
        box_color = (0, 0, 255)

    if (
        current_time - state["last_face_check"]
        < FACE_CHECK_INTERVAL
    ):

        return display_name, box_color

    state["last_face_check"] = current_time

    face_result = recognize_face(person_roi)

    if face_result is None:

        if state["face_status"] == "VERIFYING":
            return "Face not detected", (0, 165, 255)

        return display_name, box_color

    fx, fy, fw, fh = face_result["face_box"]

    votes = state["face_votes"]

    votes.append({
        "name": face_result["name"],
        "authorized": face_result["authorized"],
        "distance": face_result["distance"]
    })

    if len(votes) > MAX_FACE_VOTES:
        votes.pop(0)

    authorized_votes = [
        vote for vote in votes
        if vote["authorized"]
    ]

    unknown_votes = [
        vote for vote in votes
        if not vote["authorized"]
    ]

    authorized_names = [
        vote["name"]
        for vote in authorized_votes
    ]

    best_name = None
    matching_votes = 0

    if authorized_names:

        best_name = max(
            set(authorized_names),
            key=authorized_names.count
        )

        matching_votes = authorized_names.count(best_name)

    if matching_votes >= AUTHORIZED_VOTES_REQUIRED:

        display_name = best_name

        state["name"] = best_name
        state["face_status"] = "AUTHORIZED"

        matching_distances = [
            vote["distance"]
            for vote in authorized_votes
            if vote["name"] == best_name
        ]

        average_distance = (
            sum(matching_distances) / len(matching_distances)
        )

        state["match_distance"] = round(average_distance, 2)

        box_color = (0, 255, 0)

        last_event_time = last_authorized_event.get(track_id, 0)

        if (
            current_time - last_event_time
            >= AUTHORIZED_EVENT_COOLDOWN
        ):

            send_event(
                event_type="AUTHORIZED_PERSON",
                person_name=best_name,
                status="AUTHORIZED",
                track_id=track_id,
                confidence=average_distance,
                frame=frame
            )

            last_authorized_event[track_id] = current_time

    elif len(unknown_votes) >= UNKNOWN_VOTES_REQUIRED:

        display_name = "UNKNOWN"

        state["name"] = None
        state["face_status"] = "UNKNOWN"

        state["match_distance"] = round(
            face_result["distance"], 2
        )

        box_color = (0, 0, 255)

        last_save_time = last_unknown_save.get(track_id, 0)

        if (
            current_time - last_save_time
            >= UNKNOWN_SAVE_COOLDOWN
        ):

            now = datetime.now()

            filename = (
                f"unknown_{track_id}_"
                f"{now.strftime('%Y%m%d_%H%M%S_%f')}.jpg"
            )

            filepath = os.path.join(UNKNOWN_DIR, filename)

            cv2.imwrite(filepath, face_result["face_image"])

            send_event(
                event_type="UNKNOWN_PERSON",
                person_name="Unknown Person",
                status="UNAUTHORIZED",
                track_id=track_id,
                confidence=face_result["distance"],
                frame=frame
            )

            last_unknown_save[track_id] = current_time

            print(f"UNKNOWN PERSON | Track ID: {track_id}")

    else:

        display_name = "VERIFYING"
        box_color = (0, 165, 255)

    cv2.rectangle(
        frame,
        (x1 + fx, y1 + fy),
        (x1 + fx + fw, y1 + fy + fh),
        box_color,
        2
    )

    cv2.putText(
        frame,
        f"Votes: {len(votes)}/{MAX_FACE_VOTES}",
        (x1, max(45, y1 - 30)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        box_color,
        2
    )

    return display_name, box_color


# =========================================================
# 13. CLEANUP OLD TRACKS
# =========================================================

def cleanup_old_tracks(current_time):

    expired_ids = []

    for track_id, state in person_states.items():

        if current_time - state["last_seen"] > ID_TIMEOUT:
            expired_ids.append(track_id)

    for track_id in expired_ids:

        del person_states[track_id]

        last_unknown_save.pop(track_id, None)
        last_authorized_event.pop(track_id, None)

        print(f"TRACK REMOVED | ID: {track_id}")


# =========================================================
# 14. PREPARE LIVE PERSON DATA
# =========================================================

def get_live_persons():

    live_people = []

    for track_id, state in person_states.items():

        status = state["face_status"]

        if status == "AUTHORIZED":
            name = state["name"] or "Unknown"
        elif status == "UNKNOWN":
            name = "Unknown"
        else:
            name = "Verifying"

        live_people.append({
            "trackId": str(track_id),
            "name": name,
            "status": status,
            "matchDistance": state["match_distance"],
        })

    return live_people


# =========================================================
# 15. DRAW CAMERA DASHBOARD
# =========================================================

def draw_dashboard(frame):

    height, width = frame.shape[:2]

    cv2.line(
        frame,
        (0, LINE_Y),
        (width, LINE_Y),
        (255, 255, 0),
        2
    )

    cv2.putText(
        frame,
        "ENTRY / EXIT LINE",
        (10, LINE_Y - 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 0),
        2
    )

    cv2.rectangle(
        frame,
        (10, 10),
        (320, 150),
        (30, 30, 30),
        -1
    )

    cv2.putText(
        frame,
        f"Total Entry: {total_entry}",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (0, 255, 0),
        2
    )

    cv2.putText(
        frame,
        f"Total Exit: {total_exit}",
        (20, 75),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (0, 165, 255),
        2
    )

    cv2.putText(
        frame,
        f"Current Inside: {current_inside}",
        (20, 110),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2
    )

    cv2.putText(
        frame,
        "Press Q to quit",
        (20, 138),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.4,
        (200, 200, 200),
        1
    )


# =========================================================
# 16. MAIN SECURITY SYSTEM
# =========================================================

def main():

    global camera
    global running
    global current_inside

    print("\nStarting Smart Security System...")

    camera = cv2.VideoCapture(CAMERA_INDEX)

    if not camera.isOpened():

        print("ERROR: Could not open webcam.")
        return

    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    print("Camera started successfully.")

    start_stream_server(host="0.0.0.0", port=8000)

    print("Live camera stream: http://localhost:8000/video_feed")
    print("Live statistics: http://localhost:8000/stats")
    print("Press Q to stop the system.\n")

    try:

        while running:

            success, frame = camera.read()

            if not success:

                print("WARNING: Could not read camera frame.")
                break

            current_time = time.time()

            detected_people_count = 0

            results = person_model.track(
                frame,
                persist=True,
                classes=[PERSON_CLASS_ID],
                conf=YOLO_CONFIDENCE,
                tracker="bytetrack.yaml",
                verbose=False
            )

            if results and results[0].boxes is not None:

                boxes = results[0].boxes

                coordinates = boxes.xyxy.int().cpu().tolist()

                if boxes.id is not None:
                    track_ids = boxes.id.int().cpu().tolist()
                else:
                    track_ids = [None] * len(coordinates)

                for box, track_id in zip(coordinates, track_ids):

                    x1, y1, x2, y2 = box

                    x1 = max(0, x1)
                    y1 = max(0, y1)

                    x2 = min(frame.shape[1], x2)
                    y2 = min(frame.shape[0], y2)

                    if x2 <= x1 or y2 <= y1:
                        continue

                    detected_people_count += 1

                    if track_id is None:

                        cv2.rectangle(
                            frame,
                            (x1, y1),
                            (x2, y2),
                            (0, 165, 255),
                            2
                        )

                        cv2.putText(
                            frame,
                            "Person | Tracking...",
                            (x1, max(20, y1 - 10)),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.55,
                            (0, 165, 255),
                            2
                        )

                        continue

                    center_y = (y1 + y2) // 2

                    if track_id not in person_states:

                        person_states[track_id] = (
                            create_person_state(current_time)
                        )

                        print(f"NEW PERSON | ID: {track_id}")

                    state = person_states[track_id]

                    state["last_seen"] = current_time

                    detect_entry_exit(
                        track_id,
                        center_y,
                        state,
                        frame
                    )

                    person_roi = frame[y1:y2, x1:x2]

                    display_name, box_color = (
                        process_face_recognition(
                            frame,
                            person_roi,
                            x1,
                            y1,
                            state,
                            track_id,
                            current_time
                        )
                    )

                    cv2.rectangle(
                        frame,
                        (x1, y1),
                        (x2, y2),
                        box_color,
                        2
                    )

                    cv2.putText(
                        frame,
                        f"ID: {track_id} | {display_name}",
                        (x1, max(20, y1 - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.55,
                        box_color,
                        2
                    )

            cleanup_old_tracks(current_time)

            detection_count_history.append(detected_people_count)

            sorted_counts = sorted(detection_count_history)
            middle_index = len(sorted_counts) // 2

            current_inside = int(sorted_counts[middle_index])

            draw_dashboard(frame)

            # Publish current live person information.
            live_persons = get_live_persons()

            update_stats(
                detected_people=detected_people_count,
                current_inside=current_inside,
                total_entry=total_entry,
                total_exit=total_exit,
                live_people=live_persons,
            )

            update_frame(frame)

            cv2.imshow(
                "Smart House / Office Security System",
                frame
            )

            key = cv2.waitKey(1) & 0xFF

            if key == ord("q"):
                break

    except KeyboardInterrupt:

        print("\nSystem stopped by user.")

    except Exception as error:

        print("\nSYSTEM ERROR:", error)
        raise

    finally:

        running = False

        if camera is not None:
            camera.release()

        stop_stream_server()
        cv2.destroyAllWindows()

        print("\nWaiting for pending backend events...")

        event_queue.join()

        event_queue.put(None)
        backend_thread.join(timeout=15)

        print("\n========== FINAL RESULT ==========")

        print("Total Entry:", total_entry)
        print("Total Exit:", total_exit)
        print("Current Inside:", current_inside)

        print("Camera stopped.")
        print("Security system closed.")


# =========================================================
# 17. RUN APPLICATION
# =========================================================

if __name__ == "__main__":
    main()
