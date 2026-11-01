# AI Traffic Speed Radar ⚡ (YOLOv8 & Computer Vision)

A real-time AI-powered Traffic Speed Radar and Surveillance System built with **YOLOv8**, **ByteTrack**, and **Python**.

This system detects multiple vehicle classes (cars, trucks, buses, motorcycles), tracks persistent vehicle IDs across frames, estimates vehicle speed using calibrated physical distance, flags over-speeding infractions, automatically captures high-resolution violation snapshots with forensic watermarks, logs data to CSV reports, and renders a heads-up display (HUD).

---

## 🌟 Key Features

- **Real-Time Detection & Classification**: Powered by YOLOv8 (`yolov8n`, `yolov8s`, `yolov8m`, etc.), recognizing `cars`, `motorcycles`, `buses`, and `trucks`.
- **Multi-Object Tracking (MOT)**: Uses **ByteTrack** for identity preservation and trajectory history, with an automatic fallback to an internal Euclidean **CentroidTracker** when C-libraries are unavailable.
- **Precision Speed Estimation**:
  - **Dual-Gate Speed Trap**: Calibrated virtual tripwires with sub-frame linear interpolation to eliminate frame quantization errors.
  - **Bird's Eye View (BEV) Homography**: Perspective transformation mode for continuous road metric coordinate mapping.
  - **Bidirectional Support**: Accurately measures both approaching (incoming) and receding (outgoing) traffic.
- **Automated Violation Management**:
  - Flags vehicles exceeding configured speed limits.
  - Automatically crops and saves high-resolution vehicle violation snapshots with forensic timestamps and speed tags in `output/violations/`.
  - Comprehensive CSV logs with timestamp, track ID, vehicle class, speed, limit, direction, and status in `output/logs/traffic_speed_log.csv`.
- **Futuristic Radar HUD Overlay**:
  - Sci-fi reticle bounding boxes with dynamic color codes (Green = Normal, Red = Violation, Cyan = Calculating).
  - Trajectory trail tails visualizing past vehicle paths.
  - Floating speed & class badges above each vehicle.
  - Semi-transparent analytics dashboard: Live FPS, Monitored Vehicles, Violations, Average Speed, Top Speed.
- **Professional Windows Desktop Surveillance Workstation**:
  - Full-featured **CustomTkinter** dark-mode desktop application ([`gui_app.py`](file:///c:/Users/karthikeyan.K/cv_project/gui_app.py)) with Windows Fluent styling.
  - **Native Windows Menu Bar**: File, Surveillance, View, Tools, and Help with standard accelerator shortcuts (`Ctrl+O`, `Ctrl+S`, `F5`, `F11`, `Space`).
  - **Top Action Ribbon**: Quick triggers for Start, Pause, Snapshot capture, and live source switching.
  - **Tabbed Interface**:
    - **Live Radar Monitor**: Responsive video viewport with 5 real-time metric cards and live sidebar sliders.
    - **Violations & Evidence Gallery**: Integrated Windows `ttk.Treeview` audit log table with interactive row selection and instant forensic snapshot preview.
    - **Calibration & Settings**: Granular configuration of YOLOv8 model (`yolov8n`/`s`/`m`), confidence thresholds, vehicle class filters, and overlay toggles.
  - **Windows Multi-Pane Status Bar**: Live system status, CUDA GPU device status, video resolution, and session counters.
- **Visual Calibration Utility**:
  - Interactive tool (`calibrate_tool.py`) allowing users to click and set radar gates or 4-corner road homography polygons on any camera feed.

---

## 📐 Mathematical Formulation

### 1. Dual-Gate Speed Trap Physics
The fundamental speed formula:
$$v = \frac{D}{\Delta t} = \frac{D \cdot \text{FPS}}{\Delta f} \times 3.6 \quad (\text{km/h})$$

where:
- $D$ is the real-world distance between Gate 1 and Gate 2 in meters.
- $\text{FPS}$ is the video camera frame rate.
- $\Delta f = |f_{\text{exit}} - f_{\text{entry}}|$ is the number of elapsed frames.

### 2. Sub-Frame Fractional Linear Interpolation
To prevent frame-rate quantization inaccuracies (especially with fast vehicles spanning few frames), the exact gate crossing frame is computed via linear interpolation between consecutive points $(x_{prev}, y_{prev})$ at frame $f-1$ and $(x_{curr}, y_{curr})$ at frame $f$:

$$f_{\text{cross}} = (f - 1) + \frac{|y_{\text{gate}} - y_{prev}|}{|y_{curr} - y_{prev}|}$$

### 3. Perspective Transform (Homography)
In homography mode, road pixel coordinates $(u, v)$ are mapped to real-world metric coordinates $(X, Y)$ on the road plane via a $3 \times 3$ projective matrix $H$:

$$\begin{bmatrix} X' \\ Y' \\ W' \end{bmatrix} = H \begin{bmatrix} u \\ v \\ 1 \end{bmatrix}, \quad X = \frac{X'}{W'}, \quad Y = \frac{Y'}{W'}$$

Instantaneous velocity is then computed between consecutive time steps and smoothed using an Exponential Moving Average (EMA).

---

## 📂 Project Structure

```
cv_project/
├── speed_radar/
│   ├── __init__.py
│   ├── config.py             # Default parameters, speeds, thresholds, line ratios
│   ├── detector.py           # YOLOv8 vehicle detection + ByteTrack / Centroid tracker
│   ├── tracker_utils.py      # Trajectory trails, centroids, motion direction
│   ├── speed_estimator.py    # Dual-line speed trap & BEV homography speed estimation
│   ├── visualizer.py         # Futuristic radar HUD overlay, bounding boxes, speed badges
│   └── violation_manager.py  # Snapshot auto-capture, CSV logging, metrics
├── main.py                   # CLI entrypoint with full argument flags
├── gui_app.py                # Modern CustomTkinter Desktop GUI application
├── calibrate_tool.py         # Visual calibration tool to place radar lines/polygons
├── requirements.txt          # Python dependencies
├── traffic.mp4               # Sample HD traffic footage
└── README.md                 # Complete documentation
```

---

## 🚀 Quick Start

### 1. Installation

Ensure Python 3.10+ is installed. Then install the dependencies:

```bash
pip install -r requirements.txt
```

### 2. Launch the Desktop GUI Application

For an interactive control center with real-time video monitoring, sliders, and violation review:

```bash
python gui_app.py
```

### 3. Run via Command Line (CLI)

Run on the bundled sample traffic video:

```bash
python main.py --source traffic.mp4 --speed-limit 50 --distance 20.0
```

Run on a Live Webcam (Camera index 0):

```bash
python main.py --source 0 --speed-limit 40
```

Run Headless & Save Output Video:

```bash
python main.py --source traffic.mp4 --save-video output/radar_result.mp4 --no-display
```

---

## 🛠️ CLI Arguments Reference

| Argument | Type | Default | Description |
|---|---|---|---|
| `--source` | `str` | `traffic.mp4` | Video file path, RTSP stream URL, or camera index (`0`) |
| `--model` | `str` | `yolov8n.pt` | YOLOv8 model (`yolov8n.pt`, `yolov8s.pt`, `yolov8m.pt`) |
| `--speed-limit` | `float` | `60.0` | Speed limit in km/h or mph |
| `--distance` | `float` | `20.0` | Real-world distance in meters between Gate 1 & Gate 2 |
| `--line1` | `float` | `0.30` | Normalized vertical position (0.0 - 1.0) of Gate 1 |
| `--line2` | `float` | `0.52` | Normalized vertical position (0.0 - 1.0) of Gate 2 |
| `--conf` | `float` | `0.35` | YOLOv8 detection confidence threshold |
| `--unit` | `str` | `km/h` | Speed unit (`km/h` or `mph`) |
| `--save-video` | `str` | `None` | Path to save annotated radar output video |
| `--max-frames` | `int` | `None` | Maximum frames to process (useful for batch testing) |
| `--no-display` | `flag` | `False` | Run in headless mode without opening GUI window |
| `--homography` | `flag` | `False` | Enable 4-point Bird's Eye View perspective mode |

---

## 🎯 Camera Calibration Guide

For accurate real-world speeds on any custom roadway or CCTV camera:

1. Launch the Visual Calibrator:
   ```bash
   python calibrate_tool.py --source your_traffic_video.mp4
   ```
2. Press **`1`** and left-click on the video where **Radar Gate 1** should be placed.
3. Press **`2`** and left-click on the video where **Radar Gate 2** should be placed.
4. Press **`h`** if you prefer 4-Point Homography Road Quad mode.
5. Press **`s`** to save calibration settings into `calibration.json`.
6. Measure the physical distance between the two selected markers on the physical road (e.g. using road markings, lane dashes, or laser rangefinder) and pass it via `--distance <meters>`.

---

## 📊 Outputs & Reports

1. **Violation Snapshots**: Saved automatically under `output/violations/`
   - Named: `violation_id<ID>_<speed>kmh_<timestamp>.jpg`
   - Annotated with high-contrast alert banner, vehicle class, ID, and measured speed.
2. **CSV Log File**: Saved in `output/logs/traffic_speed_log.csv`
   - Fields: `Timestamp`, `Vehicle_ID`, `Class`, `Speed`, `Speed_Limit`, `Unit`, `Direction`, `Status`, `Confidence`, `Snapshot_Path`.
3. **Annotated Video**: Output video with full HUD dashboard and vehicle tracking trails when `--save-video` is specified.

