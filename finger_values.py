import cv2
import mediapipe as mp
import math
import time

from mediapipe.tasks import python
from mediapipe.tasks.python import vision

MODEL_PATH = "hand_landmarker.task"


def angle(a, b, c):
    """Angle ABC in degrees."""
    ab = (a.x - b.x, a.y - b.y)
    cb = (c.x - b.x, c.y - b.y)

    dot = ab[0] * cb[0] + ab[1] * cb[1]

    mag1 = math.sqrt(ab[0] ** 2 + ab[1] ** 2)
    mag2 = math.sqrt(cb[0] ** 2 + cb[1] ** 2)

    if mag1 == 0 or mag2 == 0:
        return 180

    value = dot / (mag1 * mag2)
    value = max(-1, min(1, value))

    return math.degrees(math.acos(value))


def bend_percent(degrees):
    # Rough calibration:
    # ~175° = straight
    # ~80° = strongly bent
    bend = (175 - degrees) / (175 - 80)
    bend = max(0, min(1, bend))
    return int(bend * 100)


base_options = python.BaseOptions(
    model_asset_path=MODEL_PATH
)

options = vision.HandLandmarkerOptions(
    base_options=base_options,
    running_mode=vision.RunningMode.VIDEO,
    num_hands=1
)

detector = vision.HandLandmarker.create_from_options(options)

camera = cv2.VideoCapture(0)

last_timestamp = 0

while True:
    success, frame = camera.read()

    if not success:
        break

    frame = cv2.flip(frame, 1)

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    mp_image = mp.Image(
        image_format=mp.ImageFormat.SRGB,
        data=rgb
    )

    timestamp = int(time.monotonic() * 1000)

    if timestamp <= last_timestamp:
        timestamp = last_timestamp + 1

    last_timestamp = timestamp

    result = detector.detect_for_video(
        mp_image,
        timestamp
    )

    if result.hand_landmarks:
        lm = result.hand_landmarks[0]

        # Thumb
        thumb_angle = angle(lm[1], lm[2], lm[3])

        # Other four fingers
        index_angle = angle(lm[5], lm[6], lm[7])
        middle_angle = angle(lm[9], lm[10], lm[11])
        ring_angle = angle(lm[13], lm[14], lm[15])
        pinky_angle = angle(lm[17], lm[18], lm[19])

        thumb = bend_percent(thumb_angle)
        index = bend_percent(index_angle)
        middle = bend_percent(middle_angle)
        ring = bend_percent(ring_angle)
        pinky = bend_percent(pinky_angle)

        text = (
            f"T:{thumb:3d}  "
            f"I:{index:3d}  "
            f"M:{middle:3d}  "
            f"R:{ring:3d}  "
            f"P:{pinky:3d}"
        )

        cv2.putText(
            frame,
            text,
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2
        )

    cv2.imshow("Finger Bend Test", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

camera.release()
detector.close()
cv2.destroyAllWindows()