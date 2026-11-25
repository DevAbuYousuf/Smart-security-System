import cv2
from ultralytics import YOLO

# ==========================================
# LOAD YOLO MODEL
# ==========================================

model = YOLO("yolo11n.pt")


# ==========================================
# LOAD FACE DETECTOR
# ==========================================

face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades +
    "haarcascade_frontalface_default.xml"
)

if face_cascade.empty():
    print("Face detector could not be loaded.")
    exit()

print("Face detector loaded successfully.")


# ==========================================
# START CAMERA
# ==========================================

camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("Camera could not be opened.")
    exit()

print("Camera started.")
print("Press Q to exit.")


# ==========================================
# MAIN LOOP
# ==========================================

while True:

    success, frame = camera.read()

    if not success:
        print("Failed to read camera.")
        break


    # ======================================
    # YOLO PERSON DETECTION
    # ======================================

    results = model(
        frame,
        classes=[0],
        conf=0.30,
        imgsz=416,
        verbose=False
    )


    person_count = 0
    face_count = 0


    # ======================================
    # PROCESS PERSONS
    # ======================================

    for result in results:

        if result.boxes is None:
            continue

        for box in result.boxes:

            coords = box.xyxy[0].cpu().numpy()

            x1, y1, x2, y2 = map(int, coords)

            # Keep coordinates inside frame
            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(frame.shape[1], x2)
            y2 = min(frame.shape[0], y2)

            person_count += 1


            # ==================================
            # DRAW PERSON BOX
            # ==================================

            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                (0, 255, 0),
                2
            )

            cv2.putText(
                frame,
                "PERSON",
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2
            )


            # ==================================
            # CROP PERSON
            # ==================================

            person = frame[y1:y2, x1:x2]

            if person.size == 0:
                continue


            # ==================================
            # GRAYSCALE
            # ==================================

            gray = cv2.cvtColor(
                person,
                cv2.COLOR_BGR2GRAY
            )


            # ==================================
            # FACE DETECTION
            # ==================================

            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(40, 40)
            )


            # ==================================
            # DRAW FACES
            # ==================================

            for (fx, fy, fw, fh) in faces:

                face_x1 = x1 + fx
                face_y1 = y1 + fy

                face_x2 = face_x1 + fw
                face_y2 = face_y1 + fh

                face_count += 1


                # Face rectangle
                cv2.rectangle(
                    frame,
                    (face_x1, face_y1),
                    (face_x2, face_y2),
                    (255, 0, 0),
                    2
                )


                # Face label
                cv2.putText(
                    frame,
                    "FACE DETECTED",
                    (face_x1, face_y1 - 8),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 0, 0),
                    2
                )


    # ======================================
    # DISPLAY COUNTS
    # ======================================

    cv2.putText(
        frame,
        f"PERSONS: {person_count}",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 255, 0),
        2
    )

    cv2.putText(
        frame,
        f"FACES: {face_count}",
        (20, 75),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 0, 0),
        2
    )


    # ======================================
    # SHOW CAMERA
    # ======================================

    cv2.imshow(
        "Smart Security - Face Detection",
        frame
    )


    # ======================================
    # PRESS Q TO EXIT
    # ======================================

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break


# ==========================================
# CLEANUP
# ==========================================

camera.release()
cv2.destroyAllWindows()

print("Camera stopped.")