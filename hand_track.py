import cv2
import mediapipe as mp
import os
import urllib.request
import time

from mediapipe.tasks import python
from mediapipe.tasks.python import vision


# -----------------------------
# Download hand tracking model
# -----------------------------

MODEL_PATH = "hand_landmarker.task"

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
)

if not os.path.exists(MODEL_PATH):
    print("Downloading hand tracking model...")
    urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
    print("Model downloaded!")


# -----------------------------
# MediaPipe setup
# -----------------------------

base_options = python.BaseOptions(
    model_asset_path=MODEL_PATH
)

options = vision.HandLandmarkerOptions(
    base_options=base_options,
    running_mode=vision.RunningMode.VIDEO,
    num_hands=1,
    min_hand_detection_confidence=0.7,
    min_hand_presence_confidence=0.7,
    min_tracking_confidence=0.7
)

detector = vision.HandLandmarker.create_from_options(options)


# Connections between the 21 hand points
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),       # Thumb
    (0, 5), (5, 6), (6, 7), (7, 8),       # Index
    (5, 9), (9, 10), (10, 11), (11, 12),  # Middle
    (9, 13), (13, 14), (14, 15), (15, 16),# Ring
    (13, 17), (17, 18), (18, 19), (19, 20),# Pinky
    (0, 17)
]


# -----------------------------
# Webcam
# -----------------------------

camera = cv2.VideoCapture(0)

last_timestamp = 0

while True:

    success, frame = camera.read()

    if not success:
        print("Could not open camera")
        break

    # Mirror image
    frame = cv2.flip(frame, 1)

    # OpenCV uses BGR, MediaPipe wants RGB
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    mp_image = mp.Image(
        image_format=mp.ImageFormat.SRGB,
        data=rgb
    )

    timestamp = int(time.monotonic() * 1000)

    # MediaPipe requires increasing timestamps
    if timestamp <= last_timestamp:
        timestamp = last_timestamp + 1

    last_timestamp = timestamp

    result = detector.detect_for_video(
        mp_image,
        timestamp
    )

    # -----------------------------
    # Draw detected hand
    # -----------------------------

    if result.hand_landmarks:

        landmarks = result.hand_landmarks[0]

        height, width, _ = frame.shape

        points = []

        for landmark in landmarks:

            x = int(landmark.x * width)
            y = int(landmark.y * height)

            points.append((x, y))

        # Draw bones
        for start, end in HAND_CONNECTIONS:
            cv2.line(
                frame,
                points[start],
                points[end],
                (0, 255, 0),
                2
            )

        # Draw joints
        for point in points:
            cv2.circle(
                frame,
                point,
                5,
                (0, 0, 255),
                -1
            )

    cv2.imshow("Robot Hand Tracking", frame)

    # Press Q to quit
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break


camera.release()
detector.close()
cv2.destroyAllWindows()