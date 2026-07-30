import os
import tempfile
import subprocess
import cv2
import gradio as gr
from ultralytics import YOLO

from fall_detector import FallDetector


WEIGHTS_PATH = "/Users/tyler/FallSaver/server/weights/yolo26n-pose.onnx"
model = YOLO(WEIGHTS_PATH, task="pose")


def _normalize_video(src_path, dst_path):
    """
    Convert videos such as mov, avi, mkv, and webm to mp4/h264.
    ffmpeg also applies phone rotation metadata.
    """
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", src_path,
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-an",
            dst_path,
        ],
        check=True,
        capture_output=True,
    )


def detect_video(video_file):
    if video_file is None:
        return None

    src_path = video_file.name if hasattr(video_file, "name") else video_file

    work_dir = tempfile.mkdtemp(prefix="fall_detection_")
    norm_path = os.path.join(work_dir, "normalized.mp4")
    raw_path = os.path.join(work_dir, "detected_raw.mp4")
    out_path = os.path.join(work_dir, "detected.mp4")

    try:
        _normalize_video(src_path, norm_path)
    except subprocess.CalledProcessError as e:
        message = e.stderr.decode(errors="ignore")[-500:]
        raise gr.Error(f"Could not convert the input video: {message}")

    cap = cv2.VideoCapture(norm_path)
    if not cap.isOpened():
        raise gr.Error("Could not read the video after normalization.")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(raw_path, fourcc, fps, (width, height))

    fall_window = max(2, int(fps * 1.5))
    fall_detector = FallDetector(
        history_size=fall_window,
        threshold_angle=35,
        threshold_drop=0.35,
    )

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        results = model.track(
            frame,
            persist=True,
            conf=0.10,
            device=0,
            verbose=False,
        )
        result = results[0]
        annotated_frame = result.plot()

        keypoints = result.keypoints.xy
        keypoint_confidence = result.keypoints.conf
        boxes = result.boxes
        ids = boxes.id

        status_text = "OK"
        status_color = (0, 255, 0)

        if ids is not None:
            selected_joints = keypoints[:, [5, 6, 11, 12, 15, 16], :]
            joint_confidence = keypoint_confidence[:, [5, 6, 11, 12, 15, 16]]

            for i, person_id in enumerate(ids):
                person_id = int(person_id.item())
                angle = fall_detector.body_angle(
                    selected_joints[i],
                    joint_confidence[i],
                )

                if angle is None:
                    continue

                x1, y1, x2, _ = boxes.xyxy[i]
                cv2.putText(
                    annotated_frame,
                    f"Angle: {int(angle)}",
                    (int(x2) - 70, int(y1) - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 0, 0),
                    2,
                )

                fall_detector.update_history(
                    person_id,
                    angle,
                    boxes.xywh[i],
                    boxes.conf[i].item(),
                )
                angles, xywh, confidence = fall_detector.get_history(person_id)

                if len(angles) >= fall_window:
                    angle_change, vertical_drop = fall_detector.fall_metrics(
                        angles[-fall_window:],
                        xywh[-fall_window:],
                        fall_window,
                    )

                    cv2.putText(
                        annotated_frame,
                        f"Angle Change: {angle_change:.1f}",
                        (20, 80),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 255, 0),
                        2,
                    )
                    cv2.putText(
                        annotated_frame,
                        f"Vert Drop: {vertical_drop:.2f}",
                        (20, 120),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 255, 0),
                        2,
                    )

                    if fall_detector.detect_fall(
                        angles[-fall_window:],
                        xywh[-fall_window:],
                        confidence,
                        fall_window,
                    ):
                        status_text = "FALL DETECTED!"
                        status_color = (0, 0, 255)

        text_size = cv2.getTextSize(
            f"Status: {status_text}",
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            2,
        )[0]
        text_x = width - text_size[0] - 20

        cv2.putText(
            annotated_frame,
            f"Status: {status_text}",
            (text_x, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            status_color,
            2,
        )
        writer.write(annotated_frame)

    cap.release()
    writer.release()

    try:
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", raw_path,
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                out_path,
            ],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        message = e.stderr.decode(errors="ignore")[-500:]
        raise gr.Error(f"Could not encode the result video: {message}")

    return out_path


with gr.Blocks(title="Fall Detection Demo") as demo:
    gr.Markdown(f"## Fall Detection\nWeights: `{WEIGHTS_PATH}`")

    with gr.Row():
        video_input = gr.File(
            label="Input Video (mp4, mov, avi, mkv, webm...)"
        )
        video_output = gr.Video(label="Fall Detection Result")

    detect_button = gr.Button("Detect Falls", variant="primary")
    detect_button.click(
        detect_video,
        inputs=video_input,
        outputs=video_output,
    )


if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7865,
        share=False,
    )
