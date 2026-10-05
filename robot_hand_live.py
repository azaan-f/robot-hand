import cv2
import mediapipe as mp
import math
import time
import serial

from mediapipe.tasks import python
from mediapipe.tasks.python import vision


# ============================================================
# SETTINGS
# ============================================================

ARDUINO_PORT = "COM4"
BAUD_RATE = 115200
MODEL_PATH = "hand_landmarker.task"

# Lower = smoother but slower response
# Higher = faster response but more jitter
SMOOTHING = 0.15



# ============================================================
# FINGER MATH
# ============================================================

def angle(a, b, c):
    """
    Calculates angle ABC in degrees.
    """

    ab = (
        a.x - b.x,
        a.y - b.y
    )

    cb = (
        c.x - b.x,
        c.y - b.y
    )

    dot = (
        ab[0] * cb[0]
        + ab[1] * cb[1]
    )

    mag1 = math.sqrt(
        ab[0] ** 2
        + ab[1] ** 2
    )

    mag2 = math.sqrt(
        cb[0] ** 2
        + cb[1] ** 2
    )

    if mag1 == 0 or mag2 == 0:
        return 180

    value = dot / (mag1 * mag2)

    value = max(
        -1,
        min(1, value)
    )

    return math.degrees(
        math.acos(value)
    )


def bend_percent(degrees):
    """
    Converts finger joint angle into a value from 0.0 to 1.0.

    Roughly:
    straight finger -> 0
    bent finger     -> 1
    """

    STRAIGHT_ANGLE = 175
    BENT_ANGLE = 80

    bend = (
        STRAIGHT_ANGLE - degrees
    ) / (
        STRAIGHT_ANGLE - BENT_ANGLE
    )

    bend = max(
        0,
        min(1, bend)
    )

    return bend


# ============================================================
# SERVO MAPPING
# ============================================================

def map_finger(bend):
    """
    Robot fingers were reversed in our first test.

    Real finger straight -> robot servo 100
    Real finger bent     -> robot servo 80
    """

    return int(
        100 - bend * 20
    )


def map_thumb(bend):
    """
    Thumb currently uses opposite mapping.

    We can calibrate this separately later.
    """

    return int(
        80 + bend * 20
    )


# ============================================================
# CONNECT TO ARDUINO
# ============================================================

print(
    f"Connecting to Arduino on {ARDUINO_PORT}..."
)

arduino = serial.Serial(
    ARDUINO_PORT,
    BAUD_RATE,
    timeout=1
)

# Opening serial usually resets the Arduino,
# so give it time to restart.
time.sleep(2)

print("Arduino connected!")


# ============================================================
# MEDIAPIPE SETUP
# ============================================================

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

detector = (
    vision.HandLandmarker
    .create_from_options(options)
)


# ============================================================
# CAMERA SETUP
# ============================================================

camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("Could not open camera.")
    arduino.close()
    raise SystemExit


# ============================================================
# SMOOTHING VALUES
# ============================================================

# Start all servos in the middle of the safe range.
smooth = [
    90,  # thumb
    90,  # index
    90,  # middle
    90,  # ring
    90   # pinky
]

last_timestamp = 0
last_send = 0


# ============================================================
# MAIN LOOP
# ============================================================

try:

    while True:

        success, frame = camera.read()

        if not success:
            print(
                "Could not read camera."
            )
            break


        # Mirror camera so it behaves naturally.
        frame = cv2.flip(
            frame,
            1
        )


        # OpenCV uses BGR.
        # MediaPipe expects RGB.
        rgb = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )


        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=rgb
        )


        # MediaPipe VIDEO mode requires
        # timestamps that always increase.
        timestamp = int(
            time.monotonic() * 1000
        )

        if timestamp <= last_timestamp:

            timestamp = (
                last_timestamp + 1
            )

        last_timestamp = timestamp


        # Run hand detection.
        result = detector.detect_for_video(
            mp_image,
            timestamp
        )


        # ====================================================
        # IF A HAND IS DETECTED
        # ====================================================

        if result.hand_landmarks:

            lm = (
                result.hand_landmarks[0]
            )


            # -----------------------------------------------
            # CALCULATE FINGER BENDS
            # -----------------------------------------------

            thumb_bend = bend_percent(
                angle(
                    lm[1],
                    lm[2],
                    lm[3]
                )
            )


            index_bend = bend_percent(
                angle(
                    lm[5],
                    lm[6],
                    lm[7]
                )
            )


            middle_bend = bend_percent(
                angle(
                    lm[9],
                    lm[10],
                    lm[11]
                )
            )


            ring_bend = bend_percent(
                angle(
                    lm[13],
                    lm[14],
                    lm[15]
                )
            )


            pinky_bend = bend_percent(
                angle(
                    lm[17],
                    lm[18],
                    lm[19]
                )
            )


            # -----------------------------------------------
            # MAP BENDS TO SERVO TARGETS
            # -----------------------------------------------

            thumb_target = map_thumb(
                thumb_bend
            )

            index_target = map_finger(
                index_bend
            )

            middle_target = map_finger(
                middle_bend
            )

            ring_target = map_finger(
                ring_bend
            )

            pinky_target = map_finger(
                pinky_bend
            )


            targets = [
                thumb_target,
                index_target,
                middle_target,
                ring_target,
                pinky_target
            ]


            # -----------------------------------------------
            # SMOOTH MOVEMENT
            # -----------------------------------------------

            for i in range(5):

                smooth[i] = (
                    smooth[i]
                    + SMOOTHING
                    * (
                        targets[i]
                        - smooth[i]
                    )
                )


            thumb = int(
                smooth[0]
            )

            index = int(
                smooth[1]
            )

            middle = int(
                smooth[2]
            )

            ring = int(
                smooth[3]
            )

            pinky = int(
                smooth[4]
            )


            # -----------------------------------------------
            # SEND VALUES TO ARDUINO
            # -----------------------------------------------

            now = time.monotonic()

            # Around 20 updates per second.
            if (
                now - last_send
                >= 0.05
            ):

                command = (
                    f"{thumb},"
                    f"{index},"
                    f"{middle},"
                    f"{ring},"
                    f"{pinky}\n"
                )

                arduino.write(
                    command.encode()
                )

                last_send = now


            # -----------------------------------------------
            # SHOW SERVO VALUES
            # -----------------------------------------------

            text = (
                f"T:{thumb}  "
                f"I:{index}  "
                f"M:{middle}  "
                f"R:{ring}  "
                f"P:{pinky}"
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


            # -----------------------------------------------
            # SHOW RAW BEND %
            # -----------------------------------------------

            bend_text = (
                f"BEND  "
                f"T:{int(thumb_bend * 100)}%  "
                f"I:{int(index_bend * 100)}%  "
                f"M:{int(middle_bend * 100)}%  "
                f"R:{int(ring_bend * 100)}%  "
                f"P:{int(pinky_bend * 100)}%"
            )


            cv2.putText(
                frame,
                bend_text,
                (20, 75),

                cv2.FONT_HERSHEY_SIMPLEX,

                0.55,

                (0, 255, 255),

                2
            )


        else:

            cv2.putText(
                frame,
                "NO HAND DETECTED",
                (20, 40),

                cv2.FONT_HERSHEY_SIMPLEX,

                0.8,

                (0, 0, 255),

                2
            )


        # ====================================================
        # DISPLAY CAMERA
        # ====================================================

        cv2.imshow(
            "LIVE ROBOT HAND",
            frame
        )


        # Press Q to quit.
        if (
            cv2.waitKey(1)
            & 0xFF
            == ord("q")
        ):
            break


# ============================================================
# CLEANUP
# ============================================================

finally:

    print(
        "Shutting down..."
    )

    camera.release()

    detector.close()

    arduino.close()

    cv2.destroyAllWindows()

    print(
        "Disconnected."
    )