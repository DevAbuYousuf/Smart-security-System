import cv2
import json
import os
import time
from datetime import datetime

MODEL_FILE = "face_model.yml"
LABELS_FILE = "labels.json"

UNKNOWN_DIR = "unknown_faces"
EVENT_FILE = "security_events.json"

UNKNOWN_SAVE_COOLDOWN = 5  # seconds
CONFIDENCE_THRESHOLD = 75

# Create folders/files
os.makedirs(UNKNOWN_DIR, exist_ok=True)

if not os.path.exists(EVENT_FILE):
    with open(EVENT_FILE, "w", encoding="utf-8") as file:
        json.dump([], file, indent=4)


# =========================
# Load Face Detection
# =========================

face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades +
    "haarcascade_frontalface_default.xml"
)

if face_cascade.empty():
    print("❌ Haar Cascade failed to load!")
    exit()


# =========================
# Load Model
# =========================

if not os.path.exists(MODEL_FILE):
    print("❌ face_model.yml not found!")
    exit()

if not os.path.exists(LABELS_FILE):
    print("❌ labels.json not found!")
    exit()


recognizer = cv2.face.LBPHFaceRecognizer_create()
recognizer.read(MODEL_FILE)


with open(LABELS_FILE, "r", encoding="utf-8") as file:
    labels = json.load(file)

labels = {
    int(key): value
    for key, value in labels.items()
}


# =========================
# Event Function
# =========================

def save_security_event(snapshot_path, confidence):

    now = datetime.now()

    event = {
        "event_type": "UNKNOWN_PERSON",
        "status": "UNAUTHORIZED",
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "timestamp": now.isoformat(),
        "confidence": round(float(confidence), 2),
        "snapshot": snapshot_path
    }

    # Read existing events
    try:
        with open(EVENT_FILE, "r", encoding="utf-8") as file:
            events = json.load(file)

    except (json.JSONDecodeError, FileNotFoundError):
        events = []

    # Add new event
    events.append(event)

    # Save events
    with open(EVENT_FILE, "w", encoding="utf-8") as file:
        json.dump(events, file, indent=4)

    print("\n🚨 SECURITY EVENT")
    print(f"   Type       : {event['event_type']}")
    print(f"   Status     : {event['status']}")
    print(f"   Date       : {event['date']}")
    print(f"   Time       : {event['time']}")
    print(f"   Confidence : {event['confidence']}")
    print(f"   Snapshot   : {event['snapshot']}")


# =========================
# Start Camera
# =========================

print("===================================")
print(" SMART SECURITY FACE SYSTEM")
print("===================================")

print("✅ Model loaded")
print("👤 Registered:", list(labels.values()))
print("📁 Event file:", EVENT_FILE)
print("📁 Unknown folder:", UNKNOWN_DIR)
print("📷 Starting camera...")
print("Press Q to exit.")


cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("❌ Camera could not be opened!")
    exit()


last_unknown_save = 0


# =========================
# Main Loop
# =========================

while True:

    ret, frame = cap.read()

    if not ret:
        print("❌ Failed to read camera frame")
        break

    gray = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2GRAY
    )

    detected_faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(80, 80)
    )

    unknown_detected = False

    for (x, y, w, h) in detected_faces:

        face = gray[y:y+h, x:x+w]

        face = cv2.resize(
            face,
            (200, 200)
        )

        label, confidence = recognizer.predict(face)

        # =========================
        # Registered Person
        # =========================

        if confidence < CONFIDENCE_THRESHOLD:

            name = labels.get(
                label,
                "Unknown"
            )

            text = f"{name} ({confidence:.1f})"

            box_color = (0, 255, 0)

        # =========================
        # Unknown Person
        # =========================

        else:

            name = "UNKNOWN"

            text = f"UNKNOWN ({confidence:.1f})"

            box_color = (0, 0, 255)

            unknown_detected = True

            current_time = time.time()

            # Save only every 5 seconds
            if (
                current_time -
                last_unknown_save
                >= UNKNOWN_SAVE_COOLDOWN
            ):

                now = datetime.now()

                timestamp = now.strftime(
                    "%Y%m%d_%H%M%S"
                )

                filename = (
                    f"unknown_{timestamp}.jpg"
                )

                filepath = os.path.join(
                    UNKNOWN_DIR,
                    filename
                )

                # Save face snapshot
                cv2.imwrite(
                    filepath,
                    frame[y:y+h, x:x+w]
                )

                # Save security event
                save_security_event(
                    filepath,
                    confidence
                )

                last_unknown_save = current_time


        # =========================
        # Draw Face Box
        # =========================

        cv2.rectangle(
            frame,
            (x, y),
            (x + w, y + h),
            box_color,
            2
        )

        cv2.putText(
            frame,
            text,
            (x, y - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            box_color,
            2
        )


    # =========================
    # Security Status
    # =========================

    if unknown_detected:

        cv2.putText(
            frame,
            "!!! UNKNOWN PERSON !!!",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 0, 255),
            3
        )

    else:

        cv2.putText(
            frame,
            "SECURITY: OK",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2
        )


    # Show camera
    cv2.imshow(
        "Smart Security System",
        frame
    )


    # Q = exit
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break


cap.release()
cv2.destroyAllWindows()

print("\n👋 Camera stopped.")