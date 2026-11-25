import cv2
import time
from ultralytics import YOLO

model = YOLO("yolo11n.pt")

camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("Camera could not be opened.")
    exit()

print("Camera started. Press Q to exit.")

prev_time = time.time()
frame_count = 0
fps = 0

while True:
    success, frame = camera.read()

    if not success:
        print("Failed to read camera frame.")
        break

    results = model.track(
        source=frame,
        persist=True,
        classes=[0],
        conf=0.25,
        iou=0.5,
        imgsz=416,
        tracker="bytetrack.yaml",
        verbose=False
    )

    person_count = 0

    for result in results:
        boxes = result.boxes

        if boxes is None:
            continue

        person_count = len(boxes)

        for i in range(len(boxes)):
            box = boxes[i]

            coords = box.xyxy[0].cpu().numpy()
            x1, y1, x2, y2 = map(int, coords)

            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2

            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                (0, 255, 0),
                3
            )

            cv2.circle(
                frame,
                (center_x, center_y),
                12,
                (0, 0, 255),
                -1
            )

            if box.id is not None:
                track_id = int(box.id.item())
                label = f"ID: {track_id}"
            else:
                label = "ID: Waiting"

            cv2.putText(
                frame,
                label,
                (x1, max(30, y1 - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )

    # FPS calculation
    frame_count += 1
    current_time = time.time()

    if current_time - prev_time >= 1:
        fps = frame_count / (current_time - prev_time)
        frame_count = 0
        prev_time = current_time

    # Display FPS
    cv2.putText(
        frame,
        f"FPS: {fps:.1f}",
        (20, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        (255, 255, 255),
        2
    )

    # Display person count
    cv2.putText(
        frame,
        f"Persons: {person_count}",
        (20, 70),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        (255, 255, 255),
        2
    )

    cv2.imshow("FPS + Tracking Test", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

camera.release()
cv2.destroyAllWindows()