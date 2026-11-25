import cv2
from ultralytics import YOLO

# Load YOLO model
model = YOLO("yolo11n.pt")

# Open laptop webcam
camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("ERROR: Camera could not be opened.")
    exit()

print("Tracking Debug Started")
print("Stand clearly in front of the camera.")
print("Press Q to exit.")

while True:

    success, frame = camera.read()

    if not success:
        print("ERROR: Could not read camera.")
        break

    # --------------------------------
    # YOLO + ByteTrack
    # --------------------------------
    results = model.track(
        source=frame,
        persist=True,
        classes=[0],
        conf=0.25,
        iou=0.5,
        tracker="bytetrack.yaml",
        verbose=False
    )

    # Number of detections
    detected = 0

    for result in results:

        boxes = result.boxes

        if boxes is None:
            continue

        detected = len(boxes)

        # --------------------------------
        # Process every detected person
        # --------------------------------
        for i in range(len(boxes)):

            box = boxes[i]

            coordinates = box.xyxy[0].cpu().numpy()

            x1 = int(coordinates[0])
            y1 = int(coordinates[1])
            x2 = int(coordinates[2])
            y2 = int(coordinates[3])

            # Calculate center
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2

            # -----------------------------
            # GREEN PERSON BOX
            # -----------------------------
            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                (0, 255, 0),
                3
            )

            # -----------------------------
            # BIG RED CENTER DOT
            # -----------------------------
            cv2.circle(
                frame,
                (center_x, center_y),
                15,
                (0, 0, 255),
                -1
            )

            # White border
            cv2.circle(
                frame,
                (center_x, center_y),
                17,
                (255, 255, 255),
                2
            )

            # -----------------------------
            # TRACKING ID
            # -----------------------------
            track_id = None

            if box.id is not None:
                track_id = int(box.id.item())

            if track_id is not None:

                label = f"PERSON ID: {track_id}"

            else:

                label = "PERSON - WAITING ID"

            cv2.putText(
                frame,
                label,
                (x1, max(30, y1 - 15)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )

            # Center label
            cv2.putText(
                frame,
                "RED CENTER",
                (center_x + 20, center_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 255),
                2
            )

    # --------------------------------
    # Detection status
    # --------------------------------
    cv2.putText(
        frame,
        f"Detected Persons: {detected}",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 255),
        2
    )

    cv2.imshow(
        "Tracking Debug",
        frame
    )

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break


camera.release()
cv2.destroyAllWindows()

print("Tracking Debug Stopped")