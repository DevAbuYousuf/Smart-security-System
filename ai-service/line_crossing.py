import cv2
import time
from ultralytics import YOLO

# ==========================================
# MODEL
# ==========================================

model = YOLO("yolo11n.pt")

# ==========================================
# CAMERA
# ==========================================

camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("Camera could not be opened.")
    exit()

print("Camera started. Press Q to exit.")

# ==========================================
# SETTINGS
# ==========================================

LINE_Y = 300
ZONE_SIZE = 45

COOLDOWN_SECONDS = 1.0
ID_TIMEOUT = 5.0

# ==========================================
# COUNTERS
# ==========================================

total_entry = 0
total_exit = 0
current_inside = 0

# ==========================================
# PERSON STATES
# ==========================================

person_states = {}


# ==========================================
# ZONE FUNCTION
# ==========================================

def get_zone(center_y):

    if center_y < LINE_Y - ZONE_SIZE:
        return "A"

    elif center_y > LINE_Y + ZONE_SIZE:
        return "B"

    else:
        return "MIDDLE"


# ==========================================
# MAIN LOOP
# ==========================================

while True:

    success, frame = camera.read()

    if not success:
        print("Failed to read camera frame.")
        break

    current_time = time.time()

    # ==========================================
    # YOLO TRACKING
    # ==========================================

    results = model.track(
        source=frame,
        persist=True,
        classes=[0],
        conf=0.20,
        iou=0.5,
        imgsz=416,
        tracker="bytetrack.yaml",
        verbose=False
    )

    height, width = frame.shape[:2]

    top_line = LINE_Y - ZONE_SIZE
    bottom_line = LINE_Y + ZONE_SIZE

    # ==========================================
    # DRAW ZONES
    # ==========================================

    cv2.line(
        frame,
        (0, top_line),
        (width, top_line),
        (255, 255, 0),
        2
    )

    cv2.line(
        frame,
        (0, LINE_Y),
        (width, LINE_Y),
        (0, 0, 255),
        3
    )

    cv2.line(
        frame,
        (0, bottom_line),
        (width, bottom_line),
        (255, 255, 0),
        2
    )

    cv2.putText(
        frame,
        "ZONE A",
        (20, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 0),
        2
    )

    cv2.putText(
        frame,
        "MIDDLE",
        (20, LINE_Y + 8),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 255),
        2
    )

    cv2.putText(
        frame,
        "ZONE B",
        (20, height - 25),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 0),
        2
    )

    # ==========================================
    # DETECT EACH PERSON
    # ==========================================

    detected_people = 0

    for result in results:

        boxes = result.boxes

        if boxes is None:
            continue

        for box in boxes:

            if box.id is None:
                continue

            track_id = int(box.id.item())

            detected_people += 1

            coords = box.xyxy[0].cpu().numpy()

            x1, y1, x2, y2 = map(int, coords)

            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2

            current_zone = get_zone(center_y)

            # ==================================
            # DRAW PERSON
            # ==================================

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
                10,
                (0, 0, 255),
                -1
            )

            cv2.putText(
                frame,
                f"ID: {track_id}",
                (x1, max(25, y1 - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )

            cv2.putText(
                frame,
                f"Zone: {current_zone}",
                (x1, min(height - 10, y2 + 25)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )

            # ==================================
            # NEW PERSON
            # ==================================

            if track_id not in person_states:

                person_states[track_id] = {

                    "origin": None,

                    "middle_seen": False,

                    "last_seen": current_time,

                    "last_event": 0
                }

                print(
                    f"NEW PERSON DETECTED | ID: {track_id}"
                )

            state = person_states[track_id]

            state["last_seen"] = current_time

            # ==================================
            # SET STARTING SIDE
            # ==================================

            if state["origin"] is None:

                if current_zone == "A":

                    state["origin"] = "A"

                    print(
                        f"ID {track_id} started in ZONE A"
                    )

                elif current_zone == "B":

                    state["origin"] = "B"

                    print(
                        f"ID {track_id} started in ZONE B"
                    )

                continue

            # ==================================
            # MIDDLE DETECTED
            # ==================================

            if current_zone == "MIDDLE":

                state["middle_seen"] = True

            # ==================================
            # COOLDOWN
            # ==================================

            event_allowed = (
                current_time - state["last_event"]
                >= COOLDOWN_SECONDS
            )

            # ==================================
            # ENTRY
            #
            # B -> MIDDLE -> A
            # ==================================

            if (
                state["origin"] == "B"
                and state["middle_seen"] is True
                and current_zone == "A"
                and event_allowed
            ):

                total_entry += 1
                current_inside += 1

                state["last_event"] = current_time

                # Person is now on A side
                state["origin"] = "A"

                state["middle_seen"] = False

                print("")
                print("==========================")
                print(f"ENTRY - ID: {track_id}")
                print(f"TOTAL ENTRY: {total_entry}")
                print(f"CURRENT INSIDE: {current_inside}")
                print("==========================")
                print("")

            # ==================================
            # EXIT
            #
            # A -> MIDDLE -> B
            # ==================================

            elif (
                state["origin"] == "A"
                and state["middle_seen"] is True
                and current_zone == "B"
                and event_allowed
            ):

                total_exit += 1

                if current_inside > 0:
                    current_inside -= 1

                state["last_event"] = current_time

                # Person is now on B side
                state["origin"] = "B"

                state["middle_seen"] = False

                print("")
                print("==========================")
                print(f"EXIT - ID: {track_id}")
                print(f"TOTAL EXIT: {total_exit}")
                print(f"CURRENT INSIDE: {current_inside}")
                print("==========================")
                print("")

            # ==================================
            # PERSON RETURNED TO ORIGINAL SIDE
            # ==================================

            elif (
                state["middle_seen"]
                and current_zone == state["origin"]
            ):

                state["middle_seen"] = False

    # ==========================================
    # REMOVE OLD TRACKING STATES
    # ==========================================

    expired_ids = []

    for track_id, state in person_states.items():

        if (
            current_time - state["last_seen"]
            > ID_TIMEOUT
        ):
            expired_ids.append(track_id)

    for track_id in expired_ids:

        del person_states[track_id]

    # ==========================================
    # DISPLAY INFORMATION
    # ==========================================

    cv2.putText(
        frame,
        f"CURRENT INSIDE: {current_inside}",
        (20, 80),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 255),
        2
    )

    cv2.putText(
        frame,
        f"TOTAL ENTRY: {total_entry}",
        (20, 115),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 255, 0),
        2
    )

    cv2.putText(
        frame,
        f"TOTAL EXIT: {total_exit}",
        (20, 150),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 0, 255),
        2
    )

    # How many people YOLO currently sees
    cv2.putText(
        frame,
        f"CAMERA SEES: {detected_people}",
        (20, 185),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2
    )

    # ==========================================
    # SHOW
    # ==========================================

    cv2.imshow(
        "Smart Security - Multi Person",
        frame
    )

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break


# ==========================================
# CLEANUP
# ==========================================

camera.release()
cv2.destroyAllWindows()

print("\n========== FINAL RESULT ==========")
print(f"Total Entry: {total_entry}")
print(f"Total Exit: {total_exit}")
print(f"Current Inside: {current_inside}")