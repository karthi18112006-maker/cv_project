"""
AI Traffic Speed Radar - CLI Application
"""
import argparse
import sys
from pathlib import Path
from speed_radar.config import RadarConfig
from speed_radar.radar_engine import TrafficSpeedRadar


def parse_args():
    parser = argparse.ArgumentParser(
        description="AI Traffic Speed Radar using YOLOv8 & ByteTrack",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--source", type=str, default="traffic.mp4",
                        help="Path to video file, RTSP stream URL, or webcam index (e.g. 0)")
    parser.add_argument("--model", type=str, default="yolov8n.pt",
                        help="YOLOv8 model weights (yolov8n.pt, yolov8s.pt, yolov8m.pt, etc.)")
    parser.add_argument("--speed-limit", type=float, default=60.0,
                        help="Speed limit (above this speed triggers a violation alert and snapshot)")
    parser.add_argument("--distance", type=float, default=20.0,
                        help="Real-world distance in meters between Radar Gate 1 and Gate 2")
    parser.add_argument("--line1", type=float, default=0.45,
                        help="Normalized vertical position (0.0 to 1.0) of Radar Gate 1")
    parser.add_argument("--line2", type=float, default=0.75,
                        help="Normalized vertical position (0.0 to 1.0) of Radar Gate 2")
    parser.add_argument("--conf", type=float, default=0.35,
                        help="Confidence threshold for YOLOv8 vehicle detection")
    parser.add_argument("--unit", type=str, choices=["km/h", "mph"], default="km/h",
                        help="Speed display unit")
    parser.add_argument("--save-video", type=str, default=None,
                        help="Path to save annotated radar output video (e.g. output/radar_output.mp4)")
    parser.add_argument("--max-frames", type=int, default=None,
                        help="Maximum number of frames to process (useful for testing or batch clips)")
    parser.add_argument("--no-display", action="store_true",
                        help="Run in headless mode without displaying OpenCV GUI window")
    parser.add_argument("--homography", action="store_true",
                        help="Use Homography / Bird's Eye View mode instead of Dual-Line speed trap")

    return parser.parse_args()


def main():
    args = parse_args()

    # Build config
    config = RadarConfig(
        model_name=args.model,
        confidence_thresh=args.conf,
        speed_limit_kmh=args.speed_limit,
        real_distance_meters=args.distance,
        line1_y_ratio=args.line1,
        line2_y_ratio=args.line2,
        speed_unit=args.unit,
        use_homography=args.homography
    )

    print("=" * 60)
    print("           AI TRAFFIC SPEED RADAR (YOLOv8)")
    print("=" * 60)
    print(f" Source Video:       {args.source}")
    print(f" YOLOv8 Model:       {args.model}")
    print(f" Speed Limit:        {args.speed_limit} {args.unit}")
    print(f" Trap Zone Distance: {args.distance} meters")
    print(f" Gate 1 (Entry Y):   {args.line1:.2f} (relative)")
    print(f" Gate 2 (Exit Y):    {args.line2:.2f} (relative)")
    print(f" Display GUI:        {'Disabled' if args.no_display else 'Active'}")
    print(f" Save Output Video:  {args.save_video or 'Disabled'}")
    print("=" * 60)
    print("Press 'q' or 'ESC' on video window to stop monitoring.\n")

    radar = TrafficSpeedRadar(config)

    try:
        radar.run_video(
            source=args.source,
            display=not args.no_display,
            save_path=args.save_video,
            max_frames=args.max_frames
        )
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    except Exception as e:
        print(f"\n[Error] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
