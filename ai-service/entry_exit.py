import cv2
from ultralytics import YOLO

# -----------------------------------
# Load YOLO
# -----------------------------------
model = YOLO("yolo11n.pt")

camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("ERROR: Camera could not be opened.")
    exit()


# -----------------------------------
# Counters
# -----------------------------------
entry_count = 0
exit_count = 0
current_inside = 0


# Store movement state for every ID
person_states = {}

print("Stable Entry / Exit System Started")
print("Press Q to exit.")


while True:

    success, frame = camera.read()

    if not success:
        print("ERROR: Could not read camera frame.")
        break


    height, width, _ = frame.shape


    # -----------------------------------
    # Create two virtual lines
    # -----------------------------------

    upper_line = int(height * 0.40)
    lower_line = int(height * 0.60)


    # Upper line
    cv2.line(
        frame,
        (0, upper_line),
        (width, upper_line),
        (0, 255, 255),
        2
    )


    # Lower line
    cv2.line(
        frame,
        (0, lower_line),
        (width, lower_line),
        (255, 255, 0),
        2
    )


    # -----------------------------------
    # YOLO Tracking
    # -----------------------------------

    results = model.track(
        frame,
        persist=True,
        classes=[0],
        conf=0.5,
        tracker="bytetrack.yaml",
        verbose=False
    )


    for result in results:

        boxes = result.boxes

        if boxes is None or boxes.id is None:
            continue


        coordinates = boxes.xyxy.cpu().numpy()
        track_ids = boxes.id.int().cpu().tolist()


        for box, track_id in zip(coordinates, track_ids):

            x1, y1, x2, y2 = map(int, box)

            center_x = int((x1 + x2) / 2)
            center_y = int((y1 + y2) / 2)


            # -----------------------------------
            # Draw person
            # -----------------------------------

            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                (0, 255, 0),
                2
            )

            cv2.circle(
                frame,
                (center_x, center_y),
                6,
                (0, 0, 255),
                -1
            )

            cv2.putText(
                frame,
                f"ID: {track_id}",
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )


            # -----------------------------------
            # Determine person's current zone
            # -----------------------------------

            if center_y < upper_line:

                current_zone = "OUTSIDE"

            elif center_y > lower_line:

                current_zone = "INSIDE"

            else:

                current_zone = "DOOR"


            # -----------------------------------
            # First time seeing this person
            # -----------------------------------

            if track_id not in person_states:

                person_states[track_id] = {
                    "start_zone": current_zone,
                    "last_zone": current_zone
                }


            state = person_states[track_id]

            previous_zone = state["last_zone"]


            # -----------------------------------
            # Detect zone change
            # -----------------------------------

            if current_zone != previous_zone:

                # OUTSIDE -> DOOR
                if (
                    previous_zone == "OUTSIDE"
                    and current_zone == "DOOR"
                ):
                    state["start_zone"] = "OUTSIDE"


                # INSIDE -> DOOR
                elif (
                    previous_zone == "INSIDE"
                    and current_zone == "DOOR"
                ):
                    state["start_zone"] = "INSIDE"


                # --------------------------------
                # ENTRY
                # OUTSIDE -> DOOR -> INSIDE
                # --------------------------------

                elif (
                    current_zone == "INSIDE"
                    and state["start_zone"] == "OUTSIDE"
                ):

                    entry_count += 1
                    current_inside += 1

                    print(
                        f"ENTRY | "
                        f"ID: {track_id} | "
                        f"Inside: {current_inside}"
                    )

                    state["start_zone"] = "INSIDE"


                # --------------------------------
                # EXIT
                # INSIDE -> DOOR -> OUTSIDE
                # --------------------------------

                elif (
                    current_zone == "OUTSIDE"
                    and state["start_zone"] == "INSIDE"
                ):

                    exit_count += 1

                    if current_inside > 0:
                        current_inside -= 1

                    print(
                        f"EXIT | "
                        f"ID: {track_id} | "
                        f"Inside: {current_inside}"
                    )

                    state["start_zone"] = "OUTSIDE"


                state["last_zone"] = current_zone


            # -----------------------------------
            # Display current zone
            # -----------------------------------

            cv2.putText(
                frame,
                current_zone,
                (x1, y2 + 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )


    # -----------------------------------
    # Dashboard
    # -----------------------------------

    cv2.putText(
        frame,
        f"ENTRY: {entry_count}",
        (20, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 255, 0),
        2
    )

    cv2.putText(
        frame,
        f"EXIT: {exit_count}",
        (20, 70),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 0, 255),
        2
    )

    cv2.putText(
        frame,
        f"CURRENT INSIDE: {current_inside}",
        (20, 105),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 0),
        2
    )


    # Zone labels

    cv2.putText(
        frame,
        "OUTSIDE",
        (width - 130, upper_line - 15),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (0, 255, 255),
        2
    )

    cv2.putText(
        frame,
        "DOOR ZONE",
        (width - 150, upper_line + 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 255),
        2
    )

    cv2.putText(
        frame,
        "INSIDE",
        (width - 110, lower_line + 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 0),
        2
    )


    cv2.imshow(
        "Smart Security - Stable Entry Exit",
        frame
    )


    if cv2.waitKey(1) & 0xFF == ord("q"):
        break


camera.release()
cv2.destroyAllWindows()

print("System stopped.")