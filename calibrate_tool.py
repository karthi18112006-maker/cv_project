"""
Interactive Calibration Tool for AI Traffic Speed Radar.
Allows visual adjustment of Radar Gates (Lines) and Perspective Homography points.
Press:
  '1' - Click to set Gate 1 (Entry)
  '2' - Click to set Gate 2 (Exit)
  'h' - Mode: 4-Point Homography Road Quad
  's' - Save calibration to calibration.json
  'r' - Reset
  'q' or 'ESC' - Quit
"""
import cv2
import json
import argparse
from pathlib import Path
from typing import List, Tuple


class RadarCalibrator:
    def __init__(self, video_path: str):
        self.video_path = video_path
        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open video: {video_path}")

        self.ret, self.frame = self.cap.read()
        if not self.ret:
            raise RuntimeError("Cannot read first frame from video.")

        self.h, self.w = self.frame.shape[:2]
        self.cap.release()

        # Defaults
        self.line1_y = int(0.45 * self.h)
        self.line2_y = int(0.75 * self.h)
        self.distance_meters = 20.0
        self.speed_limit = 60.0

        # Homography 4 points
        self.homography_pts = [
            (int(0.35 * self.w), int(0.45 * self.h)),
            (int(0.65 * self.w), int(0.45 * self.h)),
            (int(0.90 * self.w), int(0.90 * self.h)),
            (int(0.10 * self.w), int(0.90 * self.h))
        ]

        self.mode = "line"  # "line" or "homography"
        self.selected_line = 1
        self.window_name = "AI Speed Radar - Visual Calibration Tool"

    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            if self.mode == "line":
                if self.selected_line == 1:
                    self.line1_y = y
                    print(f"[Calibrator] Set Gate 1 Y = {y} (Ratio: {y / self.h:.3f})")
                elif self.selected_line == 2:
                    self.line2_y = y
                    print(f"[Calibrator] Set Gate 2 Y = {y} (Ratio: {y / self.h:.3f})")
            elif self.mode == "homography":
                # Find closest point
                dists = [((x - px)**2 + (y - py)**2) for px, py in self.homography_pts]
                closest_idx = dists.index(min(dists))
                self.homography_pts[closest_idx] = (x, y)
                print(f"[Calibrator] Updated Homography Point {closest_idx + 1} to ({x}, {y})")

    def run(self):
        cv2.namedWindow(self.window_name)
        cv2.setMouseCallback(self.window_name, self.mouse_callback)

        print("=" * 60)
        print("         AI SPEED RADAR CALIBRATION TOOL")
        print("=" * 60)
        print(" Controls:")
        print("   Key '1' : Switch to Gate 1 (Click on video to place Entry Line)")
        print("   Key '2' : Switch to Gate 2 (Click on video to place Exit Line)")
        print("   Key 'h' : Toggle Homography (BEV) Calibration Mode")
        print("   Key 's' : Save calibration to calibration.json")
        print("   Key 'r' : Reset to defaults")
        print("   Key 'q' : Quit")
        print("=" * 60)

        while True:
            display_img = self.frame.copy()

            if self.mode == "line":
                # Draw lines
                c1 = (0, 255, 255) if self.selected_line == 1 else (255, 180, 50)
                c2 = (0, 255, 255) if self.selected_line == 2 else (220, 80, 220)

                cv2.line(display_img, (0, self.line1_y), (self.w, self.line1_y), c1, 2, cv2.LINE_AA)
                cv2.putText(display_img, f"GATE 1 (Entry) Y={self.line1_y} [Press '1' to edit]",
                            (20, self.line1_y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, c1, 2, cv2.LINE_AA)

                cv2.line(display_img, (0, self.line2_y), (self.w, self.line2_y), c2, 2, cv2.LINE_AA)
                cv2.putText(display_img, f"GATE 2 (Exit) Y={self.line2_y} [Press '2' to edit]",
                            (20, self.line2_y + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, c2, 2, cv2.LINE_AA)

                # Info banner
                info = f"MODE: Dual Gate | Selected: Gate {self.selected_line} | Press 's' to Save"
                cv2.putText(display_img, info, (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2, cv2.LINE_AA)

            elif self.mode == "homography":
                # Draw polygon
                import numpy as np
                pts_arr = np.array(self.homography_pts, np.int32).reshape((-1, 1, 2))
                cv2.polylines(display_img, [pts_arr], True, (0, 255, 255), 2, cv2.LINE_AA)
                for i, (px, py) in enumerate(self.homography_pts):
                    cv2.circle(display_img, (px, py), 8, (0, 0, 255), -1, cv2.LINE_AA)
                    cv2.putText(display_img, f"P{i+1}", (px + 10, py - 5),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2, cv2.LINE_AA)

                info = "MODE: Homography BEV | Click near points to drag | Press 's' to Save"
                cv2.putText(display_img, info, (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2, cv2.LINE_AA)

            cv2.imshow(self.window_name, display_img)
            key = cv2.waitKey(20) & 0xFF

            if key == 27 or key == ord('q'):
                break
            elif key == ord('1'):
                self.mode = "line"
                self.selected_line = 1
                print("[Calibrator] Selected Gate 1 (Entry)")
            elif key == ord('2'):
                self.mode = "line"
                self.selected_line = 2
                print("[Calibrator] Selected Gate 2 (Exit)")
            elif key == ord('h'):
                self.mode = "homography" if self.mode != "homography" else "line"
                print(f"[Calibrator] Switched mode to: {self.mode}")
            elif key == ord('s'):
                self.save_calibration()
            elif key == ord('r'):
                self.line1_y = int(0.45 * self.h)
                self.line2_y = int(0.75 * self.h)
                print("[Calibrator] Reset to defaults.")

        cv2.destroyAllWindows()

    def save_calibration(self, filename: str = "calibration.json"):
        data = {
            "resolution": {"width": self.w, "height": self.h},
            "gate1_y": self.line1_y,
            "gate2_y": self.line2_y,
            "gate1_y_ratio": round(self.line1_y / self.h, 4),
            "gate2_y_ratio": round(self.line2_y / self.h, 4),
            "distance_meters": self.distance_meters,
            "speed_limit_kmh": self.speed_limit,
            "homography_points": self.homography_pts,
            "homography_ratios": [
                [round(px / self.w, 4), round(py / self.h, 4)]
                for px, py in self.homography_pts
            ]
        }
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        print(f"[Calibrator] Successfully saved calibration settings to '{filename}'!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Speed Radar Calibration Tool")
    parser.add_argument("--source", type=str, default="traffic.mp4", help="Video source")
    args = parser.parse_args()

    calibrator = RadarCalibrator(args.source)
    calibrator.run()

