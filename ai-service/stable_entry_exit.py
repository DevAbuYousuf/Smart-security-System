import cv2
from ultralytics import YOLO

model = YOLO("yolo11n.pt")

camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("ERROR: Camera could not be opened.")
    exit()

print("Debug Camera Started")
print("Press Q to exit.")

while True:

    success, frame = camera.read()

    if not success:
        print("ERROR: Camera frame could not be read.")
        break

    height, width, _ = frame.shape

    # Two virtual lines
    line_a = int(height * 0.40)
    line_b = int(height * 0.60)

    cv2.line(
        frame,
        (0, line_a),
        (width, line_a),
        (0, 255, 255),
        3
    )

    cv2.line(
        frame,
        (0, line_b),
        (width, line_b),
        (255, 255, 0),
        3
    )

    cv2.putText(
        frame,
        "LINE A",
        (20, line_a - 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 255),
        2
    )

    cv2.putText(
        frame,
        "LINE B",
        (20, line_b - 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 0),
        2
    )

    # Person tracking
    results = model.track(
        frame,
        persist=True,
        classes=[0],
        conf=0.3,
        tracker="bytetrack.yaml",
        verbose=False
    )

    for result in results:

        if result.boxes is None:
            continue

        boxes = result.boxes

        for box in boxes:

            x1, y1, x2, y2 = map(
                int,
                box.xyxy[0].cpu().tolist()
            )

            # Person center
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2

            # Green bounding box
            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                (0, 255, 0),
                3
            )

            # LARGE RED DOT
            cv2.circle(
                frame,
                (center_x, center_y),
                12,
                (0, 0, 255),
                -1
            )

            # White border around dot
            cv2.circle(
                frame,
                (center_x, center_y),
                14,
                (255, 255, 255),
                2
            )

            # CENTER label
            cv2.putText(
                frame,
                "CENTER",
                (center_x + 18, center_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 255),
                2
            )

            # Show tracking ID if available
            if box.id is not None:

                track_id = int(box.id.item())

                cv2.putText(
                    frame,
                    f"ID: {track_id}",
                    (x1, max(30, y1 - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2
                )

    cv2.imshow(
        "Smart Security - Dot Test",
        frame
    )

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

camera.release()
cv2.destroyAllWindows()