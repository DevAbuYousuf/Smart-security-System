import cv2
from ultralytics import YOLO
import time

# ==========================================
# LOAD MODEL
# ==========================================

model = YOLO("yolo11n.pt")


# ==========================================
# CAMERA
# ==========================================

camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("ERROR: Camera could not be opened.")
    exit()


# ==========================================
# COUNTERS
# ==========================================

in_count = 0
out_count = 0
current_inside = 0


# ==========================================
# TRACKING STATES
# ==========================================

person_states = {}

# Prevent very fast duplicate counting
COUNT_COOLDOWN = 1.5


print("======================================")
print("SMART SECURITY - ENTRY / EXIT V2")
print("======================================")
print("TOP -> BOTTOM = IN")
print("BOTTOM -> TOP = OUT")
print("Press Q to exit.")


while True:

    success, frame = camera.read()

    if not success:
        print("ERROR: Camera frame could not be read.")
        break


    height, width, _ = frame.shape


    # ==========================================
    # DOOR LINE
    # ==========================================

    door_line = height // 2


    cv2.line(
        frame,
        (0, door_line),
        (width, door_line),
        (0, 255, 255),
        4
    )


    cv2.putText(
        frame,
        "DOOR LINE",
        (20, door_line - 15),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 255, 255),
        2
    )


    # ==========================================
    # YOLO TRACKING
    # ==========================================

    results = model.track(
        source=frame,
        persist=True,
        classes=[0],
        conf=0.25,
        tracker="bytetrack.yaml",
        verbose=False
    )


    # ==========================================
    # PROCESS DETECTIONS
    # ==========================================

    for result in results:

        boxes = result.boxes

        if boxes is None:
            continue


        for i in range(len(boxes)):

            box = boxes[i]


            # --------------------------------------
            # Tracking ID
            # --------------------------------------

            if box.id is None:
                continue


            track_id = int(box.id.item())


            # --------------------------------------
            # Bounding box
            # --------------------------------------

            coords = box.xyxy[0].cpu().numpy()

            x1 = int(coords[0])
            y1 = int(coords[1])
            x2 = int(coords[2])
            y2 = int(coords[3])


            # --------------------------------------
            # CENTER POINT
            # --------------------------------------

            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2


            # --------------------------------------
            # DRAW BOX
            # --------------------------------------

            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                (0, 255, 0),
                3
            )


            # --------------------------------------
            # RED CENTER DOT
            # --------------------------------------

            cv2.circle(
                frame,
                (center_x, center_y),
                12,
                (0, 0, 255),
                -1
            )


            cv2.circle(
                frame,
                (center_x, center_y),
                15,
                (255, 255, 255),
                2
            )


            # --------------------------------------
            # SHOW ID
            # --------------------------------------

            cv2.putText(
                frame,
                f"ID: {track_id}",
                (x1, max(30, y1 - 15)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2
            )


            # ======================================
            # CREATE PERSON STATE
            # ======================================

            if track_id not in person_states:

                # Determine starting side

                if center_y < door_line:
                    side = "TOP"
                else:
                    side = "BOTTOM"


                person_states[track_id] = {
                    "previous_y": center_y,
                    "side": side,
                    "last_count_time": 0
                }


            state = person_states[track_id]


            previous_y = state["previous_y"]


            # ======================================
            # DETECT CROSSING
            # ======================================

            crossed_down = (
                previous_y < door_line
                and center_y >= door_line
            )


            crossed_up = (
                previous_y > door_line
                and center_y <= door_line
            )


            current_time = time.time()


            # ======================================
            # TOP -> BOTTOM
            # ======================================

            if crossed_down:

                if (
                    current_time - state["last_count_time"]
                    > COUNT_COOLDOWN
                ):

                    in_count += 1
                    current_inside += 1

                    state["side"] = "BOTTOM"
                    state["last_count_time"] = current_time

                    print(
                        f"ENTRY | "
                        f"ID={track_id} | "
                        f"IN={in_count} | "
                        f"INSIDE={current_inside}"
                    )


            # ======================================
            # BOTTOM -> TOP
            # ======================================

            elif crossed_up:

                if (
                    current_time - state["last_count_time"]
                    > COUNT_COOLDOWN
                ):

                    out_count += 1

                    if current_inside > 0:
                        current_inside -= 1

                    state["side"] = "TOP"
                    state["last_count_time"] = current_time

                    print(
                        f"EXIT | "
                        f"ID={track_id} | "
                        f"OUT={out_count} | "
                        f"INSIDE={current_inside}"
                    )


            # Save current position

            state["previous_y"] = center_y


            # ======================================
            # SHOW POSITION
            # ======================================

            if center_y < door_line:

                position_text = "OUTSIDE"

            else:

                position_text = "INSIDE"


            cv2.putText(
                frame,
                position_text,
                (x1, y2 + 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )


    # ==========================================
    # DASHBOARD
    # ==========================================

    cv2.rectangle(
        frame,
        (10, 10),
        (370, 135),
        (0, 0, 0),
        -1
    )


    cv2.putText(
        frame,
        f"IN: {in_count}",
        (25, 45),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 255, 0),
        2
    )


    cv2.putText(
        frame,
        f"OUT: {out_count}",
        (25, 80),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 0, 255),
        2
    )


    cv2.putText(
        frame,
        f"CURRENT INSIDE: {current_inside}",
        (25, 115),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 0),
        2
    )


    # ==========================================
    # DISPLAY
    # ==========================================

    cv2.imshow(
        "Smart Security - Entry Exit V2",
        frame
    )


    # ==========================================
    # QUIT
    # ==========================================

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break


# ==========================================
# CLEANUP
# ==========================================

camera.release()
cv2.destroyAllWindows()

print("System stopped.")