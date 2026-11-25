import cv2
from ultralytics import YOLO

# Load YOLO model
model = YOLO("yolo11n.pt")

# Open laptop webcam
camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("ERROR: Camera could not be opened.")
    exit()

print("Person Tracking Started")
print("Press Q to exit.")

while True:
    success, frame = camera.read()

    if not success:
        print("ERROR: Could not read camera frame.")
        break

    # Detect + Track people
    results = model.track(
        frame,
        persist=True,
        classes=[0],
        conf=0.5,
        tracker="bytetrack.yaml",
        verbose=False
    )

    tracked_persons = 0

    for result in results:

        # Draw detection boxes and tracking IDs
        frame = result.plot()

        if result.boxes is not None:
            tracked_persons = len(result.boxes)

    # Display number of currently tracked people
    cv2.putText(
        frame,
        f"Tracked Persons: {tracked_persons}",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 255, 0),
        2
    )

    cv2.imshow(
        "Smart Security - Person Tracking",
        frame
    )

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

camera.release()
cv2.destroyAllWindows()

print("Person Tracking Stopped")