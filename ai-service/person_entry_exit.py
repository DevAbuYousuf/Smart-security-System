import cv2
import time
from ultralytics import YOLO


# ==========================================
# 1. Load YOLO model
# ==========================================

model = YOLO("yolo11n.pt")


# ==========================================
# 2. Open webcam
# ==========================================

camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("ERROR: Camera could not be opened.")
    exit()


print("Stable Entry / Exit Detection Started")
print("Press Q to exit.")


# ==========================================
# 3. Entry / Exit counters
# ==========================================

entry_count = 0
exit_count = 0


# ==========================================
# 4. Store each person's current zone
# ==========================================

person_zones = {}


# ==========================================
# 5. Store previous center Y position
# ==========================================

previous_y = {}


# ==========================================
# 6. Store last event time
# ==========================================

last_event_time = {}


# ==========================================
# 7. People currently inside
# ==========================================

inside_people = set()


# ==========================================
# 8. Door zones
#
# OUTSIDE
#    ↓
# BUFFER
#    ↓
# INSIDE
# ==========================================

OUTSIDE_LINE = 280
INSIDE_LINE = 440


# ==========================================
# 9. Minimum movement required
# ==========================================

MIN_MOVEMENT = 20


# ==========================================
# 10. Event cooldown
# ==========================================

EVENT_COOLDOWN = 2.0


# ==========================================
# 11. Function to determine person's zone
# ==========================================

def get_zone(center_y):

    if center_y < OUTSIDE_LINE:
        return "OUTSIDE"

    elif center_y > INSIDE_LINE:
        return "INSIDE"

    else:
        return "BUFFER"


# ==========================================
# 12. Main camera loop
# ==========================================

while True:

    success, frame = camera.read()

    if not success:
        print("ERROR: Could not read camera frame.")
        break


    # ==========================================
    # 13. Track people
    # ==========================================

    results = model.track(
        frame,
        persist=True,
        classes=[0],
        conf=0.5,
        tracker="bytetrack.yaml",
        verbose=False
    )


    # ==========================================
    # 14. Draw OUTSIDE boundary
    # ==========================================

    cv2.line(
        frame,
        (0, OUTSIDE_LINE),
        (frame.shape[1], OUTSIDE_LINE),
        (255, 0, 0),
        2
    )


    # ==========================================
    # 15. Draw INSIDE boundary
    # ==========================================

    cv2.line(
        frame,
        (0, INSIDE_LINE),
        (frame.shape[1], INSIDE_LINE),
        (0, 255, 0),
        2
    )


    # ==========================================
    # 16. Zone labels
    # ==========================================

    cv2.putText(
        frame,
        "OUTSIDE",
        (20, OUTSIDE_LINE - 15),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 0, 0),
        2
    )


    cv2.putText(
        frame,
        "BUFFER / DOOR ZONE",
        (20, OUTSIDE_LINE + 50),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 255),
        2
    )


    cv2.putText(
        frame,
        "INSIDE",
        (20, INSIDE_LINE + 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 0),
        2
    )


    # ==========================================
    # 17. Process tracking results
    # ==========================================

    for result in results:

        if result.boxes is None:
            continue


        for box in result.boxes:

            # No tracking ID
            if box.id is None:
                continue


            # ==========================================
            # 18. Get tracking ID
            # ==========================================

            track_id = int(box.id[0])


            # ==========================================
            # 19. Get bounding box
            # ==========================================

            x1, y1, x2, y2 = map(
                int,
                box.xyxy[0]
            )


            # ==========================================
            # 20. Calculate center
            # ==========================================

            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2


            # ==========================================
            # 21. Determine current zone
            # ==========================================

            current_zone = get_zone(center_y)


            # ==========================================
            # 22. Draw bounding box
            # ==========================================

            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                (0, 255, 0),
                2
            )


            # ==========================================
            # 23. Draw center point
            # ==========================================

            cv2.circle(
                frame,
                (center_x, center_y),
                6,
                (0, 0, 255),
                -1
            )


            # ==========================================
            # 24. Display ID
            # ==========================================

            cv2.putText(
                frame,
                f"ID: {track_id}",
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )


            # ==========================================
            # 25. Display zone
            # ==========================================

            cv2.putText(
                frame,
                current_zone,
                (x1, y2 + 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )


            # ==========================================
            # 26. First time seeing this person
            # ==========================================

            if track_id not in person_zones:

                person_zones[track_id] = current_zone

                previous_y[track_id] = center_y

                last_event_time[track_id] = 0

                continue


            # ==========================================
            # 27. Previous zone
            # ==========================================

            old_zone = person_zones[track_id]


            # ==========================================
            # 28. Previous Y position
            # ==========================================

            old_y = previous_y[track_id]


            # ==========================================
            # 29. Movement distance
            # ==========================================

            movement = abs(center_y - old_y)


            # ==========================================
            # 30. Current time
            # ==========================================

            current_time = time.time()


            # ==========================================
            # 31. Time since last event
            # ==========================================

            time_since_event = (
                current_time - last_event_time[track_id]
            )


            # ==========================================
            # 32. ENTRY
            #
            # OUTSIDE → BUFFER → INSIDE
            # ==========================================

            if (
                old_zone == "BUFFER"
                and current_zone == "INSIDE"
                and movement >= MIN_MOVEMENT
                and time_since_event >= EVENT_COOLDOWN
            ):

                # Make sure this person is not already inside
                if track_id not in inside_people:

                    entry_count += 1

                    inside_people.add(track_id)

                    last_event_time[track_id] = current_time

                    print(
                        f"ENTRY detected - Person ID: {track_id}"
                    )


            # ==========================================
            # 33. EXIT
            #
            # INSIDE → BUFFER → OUTSIDE
            # ==========================================

            elif (
                old_zone == "BUFFER"
                and current_zone == "OUTSIDE"
                and movement >= MIN_MOVEMENT
                and time_since_event >= EVENT_COOLDOWN
            ):

                # Make sure this person is currently inside
                if track_id in inside_people:

                    exit_count += 1

                    inside_people.remove(track_id)

                    last_event_time[track_id] = current_time

                    print(
                        f"EXIT detected - Person ID: {track_id}"
                    )


            # ==========================================
            # 34. Update zone
            # ==========================================

            person_zones[track_id] = current_zone


            # ==========================================
            # 35. Update position
            # ==========================================

            previous_y[track_id] = center_y


    # ==========================================
    # 36. Current people inside
    # ==========================================

    current_inside = len(inside_people)


    # ==========================================
    # 37. Display ENTRY count
    # ==========================================

    cv2.putText(
        frame,
        f"ENTRY: {entry_count}",
        (20, 50),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 255, 0),
        2
    )


    # ==========================================
    # 38. Display EXIT count
    # ==========================================

    cv2.putText(
        frame,
        f"EXIT: {exit_count}",
        (20, 85),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 255, 255),
        2
    )


    # ==========================================
    # 39. Display current inside
    # ==========================================

    cv2.putText(
        frame,
        f"CURRENT INSIDE: {current_inside}",
        (20, 120),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 255),
        2
    )


    # ==========================================
    # 40. Display inside IDs
    # ==========================================

    inside_ids = ", ".join(
        str(person_id)
        for person_id in sorted(inside_people)
    )


    if inside_ids == "":
        inside_ids = "None"


    cv2.putText(
        frame,
        f"INSIDE IDs: {inside_ids}",
        (20, 155),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2
    )


    # ==========================================
    # 41. Show camera
    # ==========================================

    cv2.imshow(
        "Smart Security - Stable Entry Exit",
        frame
    )


    # ==========================================
    # 42. Press Q to exit
    # ==========================================

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break


# ==========================================
# 43. Release resources
# ==========================================

camera.release()
cv2.destroyAllWindows()


# ==========================================
# 44. Final result
# ==========================================

print()
print("======================================")
print("Security Session Finished")
print("======================================")
print(f"Total Entry: {entry_count}")
print(f"Total Exit: {exit_count}")
print(f"Currently Inside: {len(inside_people)}")
print(f"Inside IDs: {inside_people}")