# seg.py
# Requirements: ultralytics, supervision, opencv-python, numpy
# pip install ultralytics supervision opencv-python numpy

import cv2
import numpy as np
from ultralytics import YOLO
import supervision as sv
import torch

# ---------- CONFIG ----------
MODEL_PATH = r"C:\Users\nages\OneDrive\Documents\Autonomous EV\last (3).pt"  # <- put your .pt path here (raw string)
CAM_INDEX = 1            # try 0, change to 1/2 if your camera is on another index
USE_GPU = torch.cuda.is_available()
SAFE_WIDTH, SAFE_HEIGHT = 640, 480
MIN_CONF = 0.2
# ----------------------------

def get_capture(index=0):
    cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)  # CV_DSHOW can help on Windows
    if not cap.isOpened():
        return None
    # set safe resolution (most webcams support 640x480)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, SAFE_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, SAFE_HEIGHT)
    # verify actual size
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"[camera] resolution: {w}x{h}")
    return cap

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

    cap = get_capture(CAM_INDEX)
    if cap is None:
        print("❌ Could not open any camera. Try changing CAM_INDEX or close other apps using the camera.")
        return

    print("Press ESC to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("frame read failed, retrying...")
            continue

        h, w = frame.shape[:2]

        # Nerf: small vertical crop to focus on road (optional)
        #roi = frame[int(h*0.4):h, :]
        #results = model(roi)[0]

        results = model(frame, agnostic_nms=True)[0]

        # 1) If the model outputs masks (segmentation), use them to create a combined lane mask
        combined_mask = np.zeros((h, w), dtype=np.uint8)
        try:
            # results.masks.data might be a torch tensor (N, H, W) or numpy
            if hasattr(results, "masks") and results.masks is not None:
                masks_data = results.masks.data  # could be tensor or list
                # convert masks_data to CPU numpy array
                if isinstance(masks_data, torch.Tensor):
                    masks_np = masks_data.detach().cpu().numpy()
                else:
                    masks_np = np.array(masks_data)  # try to coerce
                # masks_np shape: (N, H, W) or (N, h, w)
                for m in masks_np:
                    # threshold, combine
                    m_bin = (m > 0.5).astype(np.uint8)
                    # ensure same shape as frame (if different, resize)
                    if m_bin.shape != (h, w):
                        m_bin = cv2.resize(m_bin.astype(np.uint8), (w, h), interpolation=cv2.INTER_NEAREST)
                    combined_mask = np.logical_or(combined_mask, m_bin).astype(np.uint8)
        except Exception as e:
            # no masks or unexpected format
            combined_mask = np.zeros((h, w), dtype=np.uint8)

        # 2) If combined_mask is empty, fallback to boxes (detect lanes as boxes if model is detector)
        # we only keep predictions with confidence >= MIN_CONF and optionally class filtering
        if combined_mask.sum() == 0:
            boxes = results.boxes if hasattr(results, "boxes") else None
            if boxes is not None and len(boxes) > 0:
                for box in boxes:
                    conf = float(box.conf.cpu().numpy()) if hasattr(box, "conf") else float(box.conf)
                    if conf < MIN_CONF:
                        continue
                    xyxy = box.xyxy.cpu().numpy().astype(int)[0] if hasattr(box.xyxy, "cpu") else np.array(box.xyxy).astype(int)[0]
                    x1, y1, x2, y2 = xyxy
                    # mark box area in mask
                    cv2.rectangle(combined_mask, (x1, y1), (x2, y2), color=1, thickness=-1)

        # 3) Overlay combined_mask on frame
        if combined_mask.sum() > 0:
            frame_out = overlay_mask_on_frame(frame, combined_mask, color=(0,255,0), alpha=0.4)
        else:
            frame_out = frame

        # 4) Draw predictions (optional): labels from results
        labels = []
        # Try to extract class names and confidences (if model is detector)
        try:
            for i, box in enumerate(results.boxes):
                conf = float(box.conf.cpu().numpy()) if hasattr(box, "conf") else float(box.conf)
                if conf < MIN_CONF: 
                    continue
                cls = int(box.cls.cpu().numpy()) if hasattr(box, "cls") else int(box.cls)
                name = model.names[cls] if hasattr(model, "names") else str(cls)
                labels.append(f"{name} {conf:.2f}")
        except Exception:
            pass

        # annotate labels (if any)
        if labels:
            frame_out = sv.BoxAnnotator().annotate(scene=frame_out, detections=sv.Detections.from_ultralytics(results))
            # also annotate text on side
            txt = " | ".join(labels)
            cv2.putText(frame_out, txt, (10,30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,200,255), 2)

        # small status panel on the right
        panel = np.full((h, 300, 3), (240,240,240), dtype=np.uint8)
        cv2.putText(panel, f"Mask pixels: {int(combined_mask.sum())}", (10,40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (30,30,30), 2)
        cv2.putText(panel, f"Model: {MODEL_PATH.split('/')[-1]}", (10,80), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (50,50,50), 1)
        out = np.hstack([frame_out, panel])

        cv2.imshow("Lane Detection - ESC to quit", out)

        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
