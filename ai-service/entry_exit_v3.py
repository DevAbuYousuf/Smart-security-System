import cv2
from ultralytics import YOLO
import time


# =====================================================
# YOLO
# =====================================================

model = YOLO("yolo11n.pt")


# =====================================================
# CAMERA
# =====================================================

camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("ERROR: Camera could not be opened.")
    exit()


# =====================================================
# COUNTERS
# =====================================================

in_count = 0
out_count = 0
current_inside = 0


# =====================================================
# PERSON STATES
# =====================================================

person_states = {}


# How far the person must move away from the
# door zone before we consider the crossing complete.
ZONE_MARGIN = 70


print()
print("========================================")
print(" SMART SECURITY - ENTRY / EXIT V3")
print("========================================")
print()
print("TOP -> DOOR -> BOTTOM = ENTRY")
print("BOTTOM -> DOOR -> TOP = EXIT")
print()
print("Press Q to exit.")
print()


while True:

    success, frame = camera.read()

    if not success:
        print("ERROR: Could not read camera.")
        break


    height, width, _ = frame.shape


    # =================================================
    # CENTER LINE
    # =================================================

    center_line = height // 2


    # =================================================
    # THREE ZONES
    # =================================================

    top_limit = center_line - ZONE_MARGIN
    bottom_limit = center_line + ZONE_MARGIN


    # =================================================
    # DRAW ZONE LINES
    # =================================================

    # Top boundary
    cv2.line(
        frame,
        (0, top_limit),
        (width, top_limit),
        (0, 255, 255),
        3
    )


    # Bottom boundary
    cv2.line(
        frame,
        (0, bottom_limit),
        (width, bottom_limit),
        (255, 255, 0),
        3
    )


    # =================================================
    # ZONE LABELS
    # =================================================

    cv2.putText(
        frame,
        "OUTSIDE",
        (20, top_limit - 15),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 255, 255),
        2
    )


    cv2.putText(
        frame,
        "DOOR ZONE",
        (20, center_line + 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2
    )


    cv2.putText(
        frame,
        "INSIDE",
        (20, bottom_limit + 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 0),
        2
    )


    # =================================================
    # YOLO TRACKING
    # =================================================

    results = model.track(
        source=frame,
        persist=True,
        classes=[0],
        conf=0.30,
        tracker="bytetrack.yaml",
        verbose=False
    )


    # =================================================
    # PROCESS PEOPLE
    # =================================================

    for result in results:

        boxes = result.boxes

        if boxes is None:
            continue


        for i in range(len(boxes)):

            box = boxes[i]


            # -----------------------------------------
            # Need tracking ID
            # -----------------------------------------

            if box.id is None:
                continue


            track_id = int(box.id.item())


            # -----------------------------------------
            # Bounding box
            # -----------------------------------------

            coordinates = box.xyxy[0].cpu().numpy()

            x1 = int(coordinates[0])
            y1 = int(coordinates[1])
            x2 = int(coordinates[2])
            y2 = int(coordinates[3])


            # -----------------------------------------
            # Person center
            # -----------------------------------------

            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2


            # -----------------------------------------
            # Determine zone
            # -----------------------------------------

            if center_y < top_limit:

                zone = "TOP"


            elif center_y > bottom_limit:

                zone = "BOTTOM"


            else:

                zone = "MIDDLE"


            # =================================================
            # DRAW PERSON
            # =================================================

            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                (0, 255, 0),
                3
            )


            # Red center point

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


            # ID

            cv2.putText(
                frame,
                f"ID: {track_id}",
                (x1, max(30, y1 - 15)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2
            )


            # Zone

            cv2.putText(
                frame,
                zone,
                (x1, y2 + 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2
            )


            # =================================================
            # CREATE STATE FOR NEW PERSON
            # =================================================

            if track_id not in person_states:

                person_states[track_id] = {
                    "last_zone": zone,
                    "candidate": None,
                    "last_event": 0
                }

                continue


            state = person_states[track_id]

            last_zone = state["last_zone"]


            # =================================================
            # TOP -> MIDDLE
            # Potential ENTRY
            # =================================================

            if (
                last_zone == "TOP"
                and zone == "MIDDLE"
            ):

                state["candidate"] = "ENTRY"


                print(
                    f"ID {track_id}: "
                    f"TOP -> DOOR"
                )


            # =================================================
            # MIDDLE -> BOTTOM
            # Confirm ENTRY
            # =================================================

            elif (
                last_zone == "MIDDLE"
                and zone == "BOTTOM"
                and state["candidate"] == "ENTRY"
            ):

                current_time = time.time()


                # Prevent duplicate event
                if current_time - state["last_event"] > 2:

                    in_count += 1

                    current_inside += 1

                    state["last_event"] = current_time


                    print(
                        f"ENTRY CONFIRMED | "
                        f"ID: {track_id} | "
                        f"IN: {in_count} | "
                        f"INSIDE: {current_inside}"
                    )


                state["candidate"] = None


            # =================================================
            # BOTTOM -> MIDDLE
            # Potential EXIT
            # =================================================

            elif (
                last_zone == "BOTTOM"
                and zone == "MIDDLE"
            ):

                state["candidate"] = "EXIT"


                print(
                    f"ID {track_id}: "
                    f"INSIDE -> DOOR"
                )


            # =================================================
            # MIDDLE -> TOP
            # Confirm EXIT
            # =================================================

            elif (
                last_zone == "MIDDLE"
                and zone == "TOP"
                and state["candidate"] == "EXIT"
            ):

                current_time = time.time()


                # Prevent duplicate event
                if current_time - state["last_event"] > 2:

                    out_count += 1


                    if current_inside > 0:
                        current_inside -= 1


                    state["last_event"] = current_time


                    print(
                        f"EXIT CONFIRMED | "
                        f"ID: {track_id} | "
                        f"OUT: {out_count} | "
                        f"INSIDE: {current_inside}"
                    )


                state["candidate"] = None


            # =================================================
            # CANCEL WRONG DIRECTION
            # =================================================

            elif (
                state["candidate"] == "ENTRY"
                and zone == "TOP"
            ):

                state["candidate"] = None


            elif (
                state["candidate"] == "EXIT"
                and zone == "BOTTOM"
            ):

                state["candidate"] = None


            # =================================================
            # SAVE ZONE
            # =================================================

            state["last_zone"] = zone


    # =====================================================
    # DASHBOARD
    # =====================================================

    cv2.rectangle(
        frame,
        (10, 10),
        (390, 145),
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


    # =====================================================
    # SHOW
    # =====================================================

    cv2.imshow(
        "Smart Security - Entry Exit V3",
        frame
    )


    # Q = Quit

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break


# =====================================================
# CLEANUP
# =====================================================

camera.release()

cv2.destroyAllWindows()

print()
print("System stopped.")
print()