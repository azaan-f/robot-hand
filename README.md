# Webcam-Controlled Robot Hand

Control a robotic hand with your own hand movements. This project uses a webcam and MediaPipe to estimate finger bends, then sends smoothed servo targets to an Arduino over USB serial.

Prototype made with an Arduino Uno, breadboard, jumper wires, and a five-finger robotic hand. It brings computer vision and physical motion together in a simple Python workflow.

- **One hand, five finger targets:** thumb, index, middle, ring, and pinky.
- **Camera-only demos:** visualize hand landmarks and check finger bend percentages before connecting hardware.
- **Smoothed movement:** reduce sudden changes in servo targets.
- **Live feedback:** see servo values and bend percentages on the mirrored camera preview.
- **USB serial control:** send newline-terminated commands at up to approximately 20 updates per second.

> **Project status:** The Python tracking and serial sender are included. The Arduino firmware and exact servo wiring/pin assignments are not included in this repo

## How it works

```text
Webcam → MediaPipe hand landmarks → Finger bend estimates
       → Servo mapping → Smoothing → USB serial → Arduino → Robotic hand
```

OpenCV captures and mirrors each frame. MediaPipe detects 21 hand landmarks, and the code measures one joint angle per finger using the landmarks' 2D coordinates. An angle of approximately 175° maps to a straight finger; approximately 80° maps to a fully bent finger. Values outside that interval are clamped.

The live controller converts these bend estimates into servo targets, applies exponential smoothing, and transmits five integers in a fixed order. This is an estimate of finger curl, rather than a reconstruction of every finger joint or wrist motion.

## Hardware

The supplied build photos show the following components:

| Component | Role |
| --- | --- |
| Hiwonder uHand robotic hand | Five-finger mechanical assembly with servos |
| Arduino Uno | Receives serial commands and controls the servos through compatible firmware |
| Computer with a webcam | Runs Python and hand tracking |
| USB cable | Connects the computer to the Arduino |
| Breadboard and jumper wires | Connect the prototype electronics |
| Four-AA battery holder and AA batteries | Power components shown during assembly |
| Arduino starter kit and wire stripper | Prototyping supplies and assembly tools |

The photos document the prototype, but do not establish a complete wiring diagram or electrical specification. Use the voltage and current requirements for your exact servos and hand kit when choosing the servo supply. Connect the servo supply ground and Arduino ground together for a shared signal reference; do not assume the Arduino's USB/5 V rail can power all five servos.

## Repository guide

| File | Purpose |
| --- | --- |
| [`hand_track.py`](hand_track.py) | Webcam preview with hand landmark lines and joints. Downloads the model if it is missing. No Arduino required. |
| [`finger_values.py`](finger_values.py) | Camera-only test displaying five finger bend values from 0 to 100. |
| [`robot_hand_live.py`](robot_hand_live.py) | Main controller: finger bend estimation, servo mapping, smoothing, and serial output. |
| [`hand_landmarker.task`](hand_landmarker.task) | MediaPipe model used by the scripts. |
| [`robot_hand_live copy.py`](robot_hand_live%20copy.py) | Currently contains comma-separated numeric character codes rather than usable controller source. Use `robot_hand_live.py` to run the project. |

## Getting started

### 1. Install the Python dependencies

Open a terminal in the project folder. On Windows, you can create an isolated environment and install the packages without activating it:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install opencv-python mediapipe pyserial
```

The `serial` import comes from **pyserial**. The other imports are part of Python's standard library. Dependency versions are not pinned in this repository.

The commands below use the Windows environment created above. On other systems, use your environment's Python executable and set the appropriate serial device path in the controller.

### 2. Check the webcam and tracking model

```powershell
.\.venv\Scripts\python.exe hand_track.py
```

Hold one hand in front of the camera. The preview should show green connections and red landmark dots. Press **q** while the preview window is focused to quit.

`hand_track.py` downloads `hand_landmarker.task` from the model URL defined in the script if the file is absent. That first download requires an internet connection. The other scripts expect the model to exist already.

Run all scripts from the project folder: the model path is relative to the current working directory.

### 3. Check the finger bend estimates

```powershell
.\.venv\Scripts\python.exe finger_values.py
```

Open and curl your fingers while watching the preview:

| Label | Finger | Displayed value |
| --- | --- | --- |
| `T` | Thumb | 0–100 |
| `I` | Index | 0–100 |
| `M` | Middle | 0–100 |
| `R` | Ring | 0–100 |
| `P` | Pinky | 0–100 |

Here, **0 means approximately straight** and **100 means approximately fully bent**. Keep the hand visible and well lit. Because the calculation uses 2D landmark coordinates, rotating the hand can change the measured bend.

### 4. Prepare the Arduino

Before running the live controller, upload firmware that:

1. Opens serial communication at **115200 baud**.
2. Reads a complete line ending in `\n`.
3. Parses five comma-separated integer servo targets.
4. Applies them in **thumb, index, middle, ring, pinky** order to the corresponding servo channels.

Use the actual pin assignments and motion limits for your build. A sketch is not supplied here, so the Python script alone will not drive an unprogrammed Arduino.

### 5. Set the serial port and run

In `robot_hand_live.py`, update the settings to match your Arduino:

```python
ARDUINO_PORT = "COM4"  # Replace with your board's port
BAUD_RATE = 115200
MODEL_PATH = "hand_landmarker.task"
SMOOTHING = 0.15
```

Find the board's port in the Arduino IDE or Windows Device Manager. Close the Arduino Serial Monitor and any other program using that port, then run:

```powershell
.\.venv\Scripts\python.exe robot_hand_live.py
```

The script opens the serial connection, waits two seconds for the Arduino to restart, and starts the camera preview. The overlay shows the smoothed servo targets and the raw bend percentages. Press **q** to release the camera, close the detector and serial connection, and exit.

## Serial protocol

Each command is a UTF-8 encoded line containing five integers:

```text
thumb,index,middle,ring,pinky\n
```

For example, a command with all targets at 90 is:

```text
90,90,90,90,90
```

The displayed example represents one line; the transmitted command includes a trailing newline. Commands are sent no more frequently than every **0.05 seconds**, and only while a hand is detected. Actual throughput depends on camera capture and inference speed.

When tracking is lost, the preview displays `NO HAND DETECTED` and Python stops sending targets. The script does not send a neutral-position or stop command on tracking loss or exit; the Arduino firmware determines what the servos do afterward.

## Calibration and tuning

The current mapping in `robot_hand_live.py` uses a narrow **80–100** target range:

| Finger | Straight target | Fully bent target |
| --- | --- | --- |
| Thumb | 80 | 100 |
| Index, middle, ring, pinky | 100 | 80 |

These are software targets from the current prototype, not universal mechanical limits. The thumb uses the opposite direction from the other fingers. Adjust `map_thumb()` and `map_finger()` to match your servo orientation and verified travel limits.

Other useful settings:

| Setting | Current value | Effect |
| --- | --- | --- |
| `SMOOTHING` | `0.15` | Lower values smooth more and respond more slowly; higher values follow targets faster. Keep it greater than 0 and at most 1. |
| `STRAIGHT_ANGLE` / `BENT_ANGLE` | `175` / `80` | Reference angles in `bend_percent()` for converting joint angles to bend estimates. |
| Camera index | `0` | Change `cv2.VideoCapture(0)` if you need a different camera. |
| Detection, presence, and tracking thresholds | `0.7` each | Confidence thresholds in the main controller and landmark preview. |

The smoothing state starts at 90 for each finger. Those initial values are not sent until a hand is detected and the first update is calculated.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| Camera cannot open or frames cannot be read | Close other camera apps, check camera permissions, and verify the camera index. |
| Model cannot be loaded | Run from the project folder and confirm `hand_landmarker.task` exists. Run `hand_track.py` to download it if needed. |
| Serial port cannot open | Verify `ARDUINO_PORT`, reconnect USB, and close the Serial Monitor or other serial clients. |
| `No module named cv2`, `mediapipe`, or `serial` | Install dependencies with the same Python executable used to launch the script. |
| Preview works but the robot does not move | Check Arduino firmware, baud rate, finger order, signal wiring, shared ground, and servo power. |
| Fingers move in the wrong direction | Calibrate `map_finger()` and `map_thumb()` for your assembly. |
| Movement is jittery or bend values seem inaccurate | Improve lighting, keep the hand visible, reduce hand rotation, and tune smoothing and angle references. |

## Built with

Python · OpenCV · MediaPipe Tasks · pyserial · Arduino Uno · Hiwonder uHand
