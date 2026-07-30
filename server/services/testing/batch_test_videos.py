import argparse
from pathlib import Path

import cv2
from ultralytics import YOLO

from fall_detector import FallDetector


SUPPORTED_VIDEO_TYPES = {
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".webm",
}

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_MODEL_PATH = "/Users/tyler/FallSaver/server/weights/yolo26n-pose.onnx"
DEFAULT_VIDEO_FOLDER = "/Users/tyler/FallSaver/FallDetection/data/shorten_fall_video"
DEFAULT_SUMMARY_PATH = "/Users/tyler/FallSaver/FallDetection/test_results/fall_results.txt"
DEFAULT_DETAILS_FOLDER = "/Users/tyler/FallSaver/FallDetection/test_results"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run fall detection on every video in a folder."
    )
    parser.add_argument(
        "folder",
        nargs="?",
        help="Folder containing the videos to test.",
        default=DEFAULT_VIDEO_FOLDER
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL_PATH,
        help="Path to the YOLO pose model.",
    )
    parser.add_argument(
        "--log",
        default=DEFAULT_SUMMARY_PATH,
        help="Path to the summary log.",
    )
    parser.add_argument(
        "--details-folder",
        help=(
            "Folder for individual video logs. "
            "Defaults to a fall_details folder inside the video folder."
        ),
        default=DEFAULT_DETAILS_FOLDER 
    )
    parser.add_argument(
        "--device",
        default="cpu",
        help='Inference device, such as "cpu", "mps", or "0" for GPU.',
    )
    return parser.parse_args()


def append_fall_detail(
    detail_path,
    person_id,
    angle_change,
    vertical_drop,
    case,
):
    """Append one detected fall to a video's detail file."""
    with detail_path.open("a", encoding="utf-8") as detail_file:
        detail_file.write(
            f"FALLLLLLL (ID: {person_id})\n"
            f"    Angle Change: {angle_change}, "
            f"Vert Drop: {vertical_drop}, "
            f"Case: {case}\n\n"
        )


def append_summary(log_path, video_name, fall_detected):
    """Append one video result to the summary log."""
    result = "✓" if fall_detected else "x"

    with log_path.open("a", encoding="utf-8") as log_file:
        log_file.write(f'"{video_name}": {result}\n')


def video_has_fall(
    video_path,
    detail_path,
    model,
    device,
):
    """Process one complete video and record every detected fall."""
    # Always create the detail file. It remains empty if no fall is detected.
    detail_path.write_text("", encoding="utf-8")

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"Could not open: {video_path.name}")
        return False

    video_fps = cap.get(cv2.CAP_PROP_FPS) or 25
    fall_window = max(2, int(video_fps * 1.5))
    cooldown_frames = max(1, int(video_fps * 2))

    fall_detector = FallDetector(
        history_size=fall_window,
        threshold_angle=40,
        threshold_drop=0.28,
    )

    frame_number = 0
    first_frame = True
    fall_detected = False
    last_fall_frame = {}

    while True:
        success, frame = cap.read()
        if not success:
            break

        frame_number += 1

        results = model.track(
            frame,
            persist=not first_frame,
            conf=0.1,
            device=device,
            verbose=False,
        )
        first_frame = False

        result = results[0]
        boxes = result.boxes

        if (
            boxes is None
            or boxes.id is None
            or result.keypoints is None
            or result.keypoints.conf is None
        ):
            continue

        ids = boxes.id
        selected_joints = result.keypoints.xy[
            :, [5, 6, 11, 12, 15, 16], :
        ]
        selected_confidence = result.keypoints.conf[
            :, [5, 6, 11, 12, 15, 16]
        ]

        for index, tracked_id in enumerate(ids):
            person_id = int(tracked_id.item())

            angle = fall_detector.body_angle(
                selected_joints[index],
                selected_confidence[index],
            )

            if angle is None:
                continue

            fall_detector.update_history(
                person_id,
                angle,
                boxes.xywh[index],
                boxes.conf[index].item(),
            )

            angles, xywh, confidence = fall_detector.get_history(
                person_id
            )

            # Match the current test_video.py behavior.
            if len(angles) < fall_window / 4.5:
                continue

            recent_angles = angles[-fall_window:]
            recent_xywh = xywh[-fall_window:]

            angle_change, vertical_drop, case = (
                fall_detector.fall_metrics(
                    recent_angles,
                    recent_xywh,
                    fall_window,
                )
            )

            is_fall = fall_detector.detect_fall(
                recent_angles,
                recent_xywh,
                confidence,
                fall_window,
            )

            can_record = (
                frame_number
                - last_fall_frame.get(
                    person_id,
                    -cooldown_frames,
                )
                >= cooldown_frames
            )

            if is_fall and can_record:
                fall_detected = True
                last_fall_frame[person_id] = frame_number

                append_fall_detail(
                    detail_path,
                    person_id,
                    angle_change,
                    vertical_drop,
                    case,
                )

                timestamp = frame_number / video_fps
                print(
                    f"  Fall detected at {timestamp:.2f}s "
                    f"(ID: {person_id})"
                )

    cap.release()
    return fall_detected


def main():
    args = parse_args()

    video_folder = Path(args.folder)
    model_path = Path(args.model)
    summary_path = Path(args.log)

    if not video_folder.is_dir():
        raise NotADirectoryError(
            f"Video folder not found: {video_folder}"
        )

    if not model_path.is_file():
        raise FileNotFoundError(f"Model not found: {model_path}")

    if args.details_folder:
        details_folder = Path(args.details_folder)
    else:
        details_folder = video_folder / "fall_details"

    summary_path.parent.mkdir(parents=True, exist_ok=True)

    # Empty the summary log before starting
    summary_path.write_text("", encoding="utf-8")
    
    details_folder.mkdir(parents=True, exist_ok=True)

    video_paths = sorted(
        path
        for path in video_folder.iterdir()
        if (
            path.is_file()
            and path.suffix.lower() in SUPPORTED_VIDEO_TYPES
        )
    )

    if not video_paths:
        print(f"No supported videos found in: {video_folder}")
        return

    model = YOLO(str(model_path), task="pose")

    print(f"Found {len(video_paths)} video(s).")
    print(f"Summary log: {summary_path}")
    print(f"Detail logs: {details_folder}")

    for index, video_path in enumerate(video_paths, start=1):
        print(
            f"[{index}/{len(video_paths)}] "
            f"Testing {video_path.name}..."
        )

        detail_path = details_folder / f"{video_path.stem}.txt"

        fall_detected = video_has_fall(
            video_path,
            detail_path,
            model,
            args.device,
        )

        append_summary(
            summary_path,
            video_path.name,
            fall_detected,
        )

        result = "✓" if fall_detected else "x"
        print(f'"{video_path.name}": {result}')


if __name__ == "__main__":
    main()
