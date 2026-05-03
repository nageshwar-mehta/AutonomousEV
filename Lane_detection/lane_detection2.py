# seg_realsense.py
# Requirements:
# pip install ultralytics supervision opencv-python numpy pyrealsense2 torch

import cv2
import numpy as np
from ultralytics import YOLO
import supervision as sv
import torch
import pyrealsense2 as rs

# ---------- CONFIG ----------
MODEL_PATH = r"last (3) (2).pt"
USE_GPU = torch.cuda.is_available()
SAFE_WIDTH, SAFE_HEIGHT = 640, 480
MIN_CONF = 0.2
# ----------------------------

def overlay_mask_on_frame(frame, mask, color=(0,255,0), alpha=0.35):
    """mask: uint8 (H,W) with 1 where lane exists"""
    colored = frame.copy()
    colored[mask == 1] = (colored[mask == 1] * (1 - alpha) + np.array(color) * alpha).astype(np.uint8)
    return colored

def main():

    # load model
    print("[model] loading:", MODEL_PATH)
    model = YOLO(MODEL_PATH)

    if USE_GPU:
        try:
            model.to("cuda")
            print("[model] using GPU")
        except Exception:
            print("[model] couldn't move to cuda, using CPU")
    else:
        print("[model] using CPU")

    # annotators
    mask_annotator = sv.MaskAnnotator()
    label_annotator = sv.LabelAnnotator(text_position=sv.Position.TOP_LEFT)

    # -------- REALSENSE CAMERA SETUP --------
    pipeline = rs.pipeline()
    config = rs.config()

    config.enable_stream(rs.stream.color, SAFE_WIDTH, SAFE_HEIGHT, rs.format.bgr8, 30)

    pipeline.start(config)

    print("RealSense camera started")
    print("Press ESC to quit.")
    # ---------------------------------------

    while True:

        frames = pipeline.wait_for_frames()
        color_frame = frames.get_color_frame()

        if not color_frame:
            continue

        frame = np.asanyarray(color_frame.get_data())

        h, w = frame.shape[:2]

        # run model
        results = model(frame, agnostic_nms=True)[0]

        # combined lane mask
        combined_mask = np.zeros((h, w), dtype=np.uint8)

        try:
            if hasattr(results, "masks") and results.masks is not None:

                masks_data = results.masks.data

                if isinstance(masks_data, torch.Tensor):
                    masks_np = masks_data.detach().cpu().numpy()
                else:
                    masks_np = np.array(masks_data)

                for m in masks_np:

                    m_bin = (m > 0.5).astype(np.uint8)

                    if m_bin.shape != (h, w):
                        m_bin = cv2.resize(
                            m_bin.astype(np.uint8),
                            (w, h),
                            interpolation=cv2.INTER_NEAREST
                        )

                    combined_mask = np.logical_or(combined_mask, m_bin).astype(np.uint8)

        except Exception:
            combined_mask = np.zeros((h, w), dtype=np.uint8)

        # fallback to boxes
        if combined_mask.sum() == 0:

            boxes = results.boxes if hasattr(results, "boxes") else None

            if boxes is not None and len(boxes) > 0:

                for box in boxes:

                    conf = float(box.conf.cpu().numpy())

                    if conf < MIN_CONF:
                        continue

                    xyxy = box.xyxy.cpu().numpy().astype(int)[0]
                    x1, y1, x2, y2 = xyxy

                    cv2.rectangle(combined_mask, (x1,y1), (x2,y2), color=1, thickness=-1)

        # overlay mask
        if combined_mask.sum() > 0:
            frame_out = overlay_mask_on_frame(frame, combined_mask, color=(0,255,0), alpha=0.4)
        else:
            frame_out = frame

        # labels
        labels = []

        try:

            for box in results.boxes:

                conf = float(box.conf.cpu().numpy())

                if conf < MIN_CONF:
                    continue

                cls = int(box.cls.cpu().numpy())
                name = model.names[cls]

                labels.append(f"{name} {conf:.2f}")

        except Exception:
            pass

        if labels:

            frame_out = sv.BoxAnnotator().annotate(
                scene=frame_out,
                detections=sv.Detections.from_ultralytics(results)
            )

            txt = " | ".join(labels)

            cv2.putText(
                frame_out,
                txt,
                (10,30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0,200,255),
                2
            )

        # right panel
        panel = np.full((h,300,3),(240,240,240),dtype=np.uint8)

        cv2.putText(panel,f"Mask pixels: {int(combined_mask.sum())}",
                    (10,40),cv2.FONT_HERSHEY_SIMPLEX,0.7,(30,30,30),2)

        cv2.putText(panel,f"Model: {MODEL_PATH.split('/')[-1]}",
                    (10,80),cv2.FONT_HERSHEY_SIMPLEX,0.5,(50,50,50),1)

        out = np.hstack([frame_out,panel])

        cv2.imshow("Lane Detection - ESC to quit", out)

        key = cv2.waitKey(1) & 0xFF

        if key == 27:
            break

    pipeline.stop()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()