import cv2
from ultralytics import YOLO

# ==========================================
# YOLO MODEL
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
# PERSON STATES
# ==========================================

person_states = {}


print("================================")
print("Smart Security Entry/Exit System")
print("================================")
print("Press Q to exit.")


while True:

    success, frame = camera.read()

    if not success:
        print("ERROR: Could not read camera.")
        break


    height, width, _ = frame.shape


    # ==========================================
    # TWO VIRTUAL LINES
    # ==========================================

    line_a = int(height * 0.40)
    line_b = int(height * 0.60)


    # LINE A
    cv2.line(
        frame,
        (0, line_a),
        (width, line_a),
        (0, 255, 255),
        3
    )


    # LINE B
    cv2.line(
        frame,
        (0, line_b),
        (width, line_b),
        (255, 255, 0),
        3
    )


    # Labels

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


    for result in results:

        boxes = result.boxes

        if boxes is None:
            continue


        # ==========================================
        # EACH PERSON
        # ==========================================

        for i in range(len(boxes)):

            box = boxes[i]


            # Bounding box
            coordinates = box.xyxy[0].cpu().numpy()

            x1 = int(coordinates[0])
            y1 = int(coordinates[1])
            x2 = int(coordinates[2])
            y2 = int(coordinates[3])


            # Person center
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2


            # ==========================================
            # TRACKING ID
            # ==========================================

            if box.id is None:
                continue

            track_id = int(box.id.item())


            # ==========================================
            # DRAW PERSON BOX
            # ==========================================

            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                (0, 255, 0),
                3
            )


            # ==========================================
            # RED CENTER DOT
            # ==========================================

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


            # ==========================================
            # ID
            # ==========================================

            cv2.putText(
                frame,
                f"PERSON ID: {track_id}",
                (x1, max(30, y1 - 15)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )


            # ==========================================
            # CREATE STATE
            # ==========================================

            if track_id not in person_states:

                if center_y < line_a:

                    initial_zone = "OUTSIDE"

                elif center_y > line_b:

                    initial_zone = "INSIDE"

                else:

                    initial_zone = "DOOR"


                person_states[track_id] = {
                    "previous_y": center_y,
                    "first_line": None,
                    "zone": initial_zone
                }


            state = person_states[track_id]

            previous_y = state["previous_y"]


            # ==========================================
            # ENTRY
            #
            # OUTSIDE
            #    ↓
            # LINE A
            #    ↓
            # LINE B
            #    ↓
            # INSIDE
            # ==========================================

            crossed_a_down = (
                previous_y < line_a
                and center_y >= line_a
            )


            crossed_b_down = (
                previous_y < line_b
                and center_y >= line_b
            )


            if crossed_a_down:

                state["first_line"] = "A"


            if crossed_b_down:

                if state["first_line"] == "A":

                    in_count += 1
                    current_inside += 1

                    print(
                        f"ENTRY | ID={track_id} | "
                        f"IN={in_count} | "
                        f"INSIDE={current_inside}"
                    )

                    # Reset state
                    state["first_line"] = None


            # ==========================================
            # EXIT
            #
            # INSIDE
            #    ↑
            # LINE B
            #    ↑
            # LINE A
            #    ↑
            # OUTSIDE
            # ==========================================

            crossed_b_up = (
                previous_y > line_b
                and center_y <= line_b
            )


            crossed_a_up = (
                previous_y > line_a
                and center_y <= line_a
            )


            if crossed_b_up:

                state["first_line"] = "B"


            if crossed_a_up:

                if state["first_line"] == "B":

                    out_count += 1

                    if current_inside > 0:
                        current_inside -= 1

                    print(
                        f"EXIT | ID={track_id} | "
                        f"OUT={out_count} | "
                        f"INSIDE={current_inside}"
                    )

                    # Reset state
                    state["first_line"] = None


            # Save current position
            state["previous_y"] = center_y


    # ==========================================
    # DASHBOARD
    # ==========================================

    cv2.rectangle(
        frame,
        (10, 10),
        (350, 130),
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
    # SHOW CAMERA
    # ==========================================

    cv2.imshow(
        "Smart Security - Entry Exit",
        frame
    )


    # Q = quit

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break


# ==========================================
# CLOSE
# ==========================================

camera.release()
cv2.destroyAllWindows()

print("System stopped.")