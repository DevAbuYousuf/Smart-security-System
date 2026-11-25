
import cv2
import os
import json
import numpy as np
import requests
import shutil
from datetime import datetime

# -------------------------------
# CONFIGURATION
# -------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

KNOWN_FACES_DIR = os.path.join(BASE_DIR, "known_faces")
MODEL_FILE = os.path.join(BASE_DIR, "face_model.yml")
LABELS_FILE = os.path.join(BASE_DIR, "labels.json")

API_URL = "http://localhost:5000/api/faces/labels"

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")

# -------------------------------
# LOAD ACTIVE PERSONS FROM API
# -------------------------------

def get_active_persons():

    try:
        response = requests.get(API_URL, timeout=10)
        response.raise_for_status()

        result = response.json()

        if not result.get("success"):
            raise Exception("API returned unsuccessful response")

        labels = result.get("data", {})

        if not isinstance(labels, dict) or not labels:
            raise Exception("No active persons found in database")

        persons = {}

        for label, name in labels.items():

            label = int(label)

            if label < 0 or label in persons:
                raise ValueError("Invalid or duplicate face label")

            if not isinstance(name, str) or not name.strip():
                raise ValueError("Invalid person name in API response")

            persons[label] = name.strip()

        print("✅ Active persons loaded from MongoDB")
        print(json.dumps(
            {str(k): v for k, v in persons.items()},
            indent=4
        ))

        return persons

    except (requests.RequestException, ValueError, TypeError, Exception) as error:
        print("❌ Could not load active persons:", error)
        return None


# -------------------------------
# LOAD FACE CASCADE
# -------------------------------

face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades +
    "haarcascade_frontalface_default.xml"
)

if face_cascade.empty():
    print("❌ Haar Cascade load failed!")
    raise SystemExit(1)


# -------------------------------
# MAIN TRAINING FUNCTION
# -------------------------------

def train_faces():

    if not os.path.isdir(KNOWN_FACES_DIR):
        print("❌ known_faces folder not found!")
        return

    active_persons = get_active_persons()

    if active_persons is None:
        return

    faces = []
    labels = []

    print("\n🔍 Searching training images...\n")

    # Match each active person's name with folder name
    for label, person_name in active_persons.items():

        person_folder = os.path.join(
            KNOWN_FACES_DIR,
            person_name
        )

        if not os.path.isdir(person_folder):
            print(f"⚠️ Folder missing for: {person_name}")
            continue

        print(f"👤 Person: {person_name}")
        image_count = 0

        for image_name in os.listdir(person_folder):

            if not image_name.lower().endswith(IMAGE_EXTENSIONS):
                continue

            image_path = os.path.join(
                person_folder,
                image_name
            )

            image = cv2.imread(image_path)

            if image is None:
                print(f"⚠️ Could not read: {image_name}")
                continue

            gray = cv2.cvtColor(
                image,
                cv2.COLOR_BGR2GRAY
            )

            detected_faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(80, 80)
            )

            if len(detected_faces) == 0:
                print(f"⚠️ No face found: {image_name}")
                continue

            # Select largest detected face
            x, y, w, h = max(
                detected_faces,
                key=lambda face: face[2] * face[3]
            )

            face = gray[y:y+h, x:x+w]

            face = cv2.resize(
                face,
                (200, 200)
            )

            faces.append(face)
            labels.append(label)

            image_count += 1

            print(f"   ✅ {image_name}")

        print(f"   Training images: {image_count}\n")

    # -------------------------------
    # VALIDATE TRAINING DATA
    # -------------------------------

    if len(faces) == 0:
        print("❌ No training faces found.")
        print("Check active persons and their image folders.")
        print("Existing model has NOT been changed.")
        return

    trained_labels = set(labels)

    if trained_labels != set(active_persons.keys()):
        missing = set(active_persons.keys()) - trained_labels

        print("❌ Some active persons have no usable training images:")
        for label in missing:
            print(f"   {label}: {active_persons[label]}")

        print("Existing model has NOT been changed.")
        return

    # -------------------------------
    # TRAIN LBPH MODEL
    # -------------------------------

    print("🧠 Training LBPH model...")

    recognizer = cv2.face.LBPHFaceRecognizer_create()

    recognizer.train(
        faces,
        np.array(labels, dtype=np.int32)
    )

    # Save to temporary file first
    temp_model = MODEL_FILE + ".tmp"
    temp_labels = LABELS_FILE + ".tmp"

    recognizer.write(temp_model)

    label_data = {
        str(label): name
        for label, name in active_persons.items()
    }

    with open(temp_labels, "w", encoding="utf-8") as file:
        json.dump(
            label_data,
            file,
            indent=4,
            ensure_ascii=False
        )

    # -------------------------------
    # BACKUP EXISTING FILES
    # -------------------------------

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if os.path.exists(MODEL_FILE):
        backup_model = MODEL_FILE + f".{timestamp}.bak"
        shutil.copy2(MODEL_FILE, backup_model)
        print("📦 Previous model backup:", backup_model)

    if os.path.exists(LABELS_FILE):
        backup_labels = LABELS_FILE + f".{timestamp}.bak"
        shutil.copy2(LABELS_FILE, backup_labels)
        print("📦 Previous labels backup:", backup_labels)

    # -------------------------------
    # REPLACE OLD FILES
    # -------------------------------

    os.replace(temp_model, MODEL_FILE)
    os.replace(temp_labels, LABELS_FILE)

    print("\n✅ Training completed successfully!")
    print("📁 Model saved:", MODEL_FILE)
    print("📁 Labels saved:", LABELS_FILE)

    print("\n🏷️ Trained Labels:")

    for label, name in active_persons.items():
        print(f"   {label} = {name}")

    print("\n📸 Total training faces:", len(faces))


if __name__ == "__main__":
    train_faces()
