import cv2 as cv
from ultralytics import YOLO
import supervision as sv
import numpy as np
import argparse

def fun1():
    def parse_arguments() -> argparse.Namespace:
        parser = argparse.ArgumentParser(description="YLOv8 live")
        parser.add_argument(
            "-webcam-resolution",
            default=[640, 640],
            nargs=2,
            type=int
        )
         
        args = parser.parse_args()
        return args
    # start, end = sv.Point(x=0, y=300), sv.Point(x=1280, y=300)
    # line_zone = sv.LineZone(start=start, end=end)
    polygon_annotator = sv.PolygonAnnotator()
    tracker = sv.ByteTrack()
    mask_annotator = sv.MaskAnnotator()
    label_annotator = sv.LabelAnnotator(text_position=sv.Position.TOP_LEFT)
    # LABEL_ANNOTATOR = sv.LabelAnnotator(
    # color=COLORS, text_color=sv.Color.from_hex("#000000")
    # )

    label_annotator = sv.LabelAnnotator(text_position=sv.Position.TOP_RIGHT)
    # polygone=np.array([
    # [114, 32],[1134, 100],[1262, 660],[6, 612]
    # ])
    x=15
    polygone=np.array([
    [640-39*x, 360-22*x],[640+39*x, 360-22*x],[640+39*x, 360+22*x],[640-39*x, 360+22*x]
    ])
    zone = sv.PolygonZone(polygon=polygone)


    # zone_annotator=sv.PolygonZoneAnnotator(zone=zone,color=sv.Color.red(),display_in_zone_count=False)


    args = parse_arguments()
    frame_width, frame_height = args.webcam_resolution
# 5
    capture = cv.VideoCapture(0)
    capture.set(cv.CAP_PROP_FRAME_WIDTH, frame_width)
    capture.set(cv.CAP_PROP_FRAME_HEIGHT, frame_height)


# "C:\downloads\last (3).pt"
    model_path="/home/aashish/Downloads/last (3).pt"
    model = YOLO("yolov8n-seg.pt")

    # model = YOLO('yolov8m-seg.pt')




    width, height = 550, 720
    background_color = (252, 252,242 )  # BGR format: (Blue, Green, Red)
    img = np.full((height, width, 3), background_color, dtype=np.uint8)

    # Create a font
    font = cv.FONT_HERSHEY_TRIPLEX

    # Define text parameters
    text = "Detections "
    text1 = "Detected "
    text2="PerArea"

    text_color = (56, 56, 30)  # Red color for text
    text_thickness = 2
    text_position = (25, 100)
    text_position1 = (25, 200)
    text_position2 = (25, 300)

    text_scale = 1
    tr=0


    while True:
        ret, frame = capture.read()
        # cv.imwrite(r"C:\binary\peb.jpg", frame)

        # frame = zone_annotator.annotate(
        #     scene=frame,
        #     # detections=detections,
        #     # labels=labels
        # )
        mask = np.zeros((720, 1280), dtype=np.uint8)
        cv.fillPoly(mask, [polygone], 255)
        # cropped_frame = cv.bitwise_and(frame, frame, mask=mask)


        results = model(frame,agnostic_nms=True)[0]

        detections = sv.Detections.from_ultralytics(results)
        detections = detections[detections.class_id == 0]
        detections = detections[detections.confidence > 0.3]

        # labels = [f"{model.model.names[int(obj[5])]} {obj[4]:.2f}" for obj in detections if obj[4] > 0.3]
        detections1 = tracker.update_with_detections(detections)
        # print(detections1.get_anchors_coordinates(sv.Position.CENTER))
        # print(dir(detections1))
        for i, mask in enumerate(detections1.mask):
            # mask is a boolean matrix → convert to uint8
            mask_uint8 = (mask * 255).astype(np.uint8)

            # find contours (polygon edges)
            contours, _ = cv.findContours(mask_uint8, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)

            if len(contours) > 0:
                polygon = contours[0].reshape(-1, 2)  # Nx2 → (x,y)
                print(f"Mask {i} polygon coordinates:")
                print(polygon)

        # crossed_in, crossed_out = line_zone.trigger(detections1)
        # labels = [f"#{tracker_id}" for tracker_id in detections1.tracker_id]
        labels = [f"#{tracker_id}{model.model.names[class_id]}" for tracker_id, class_id, confidence in zip(detections1.tracker_id, detections1.class_id, detections1.confidence) if confidence > 0.1 and tracker_id is not None]
        # print(len(detections))
        tracker_ids_to_print = [tracker_id for tracker_id, class_id, confidence in zip(detections1.tracker_id, detections1.class_id, detections1.confidence) if confidence > 0.1 and tracker_id is not None]
        # print("trivnfnnfnvifuviufnbviufbiu"+str(tracker_ids_to_print))
        if tracker_ids_to_print:
            tr = max(tracker_ids_to_print)
            # area1=sum(detections.area)
            # print(max_tracker_id)
        else:
            tr=tr
        frame = mask_annotator.annotate(
            scene=frame, 
            detections=detections,
            
        )
        frame = label_annotator.annotate(
            scene=frame,
            detections=detections1,
            labels=labels
        )

        # frame = zone_annotator.annotate(
        #     scene=frame,
        #     # detections=detections1,
        #     # labels=labels
        # )
        # print("ocmosicnodinciosdcnidndi    "+str(detections.area))
        # frame = polygon_annotator.annotate(
        # scene=frame,
        # detections=detections
        # )
        img[:, :, :] = background_color  # Set all pixels to background_color
        area2=(sum(detections.area)*100)/921600
        # Add text with the current number
        cv.putText(img, f"{text}{len(detections)}", text_position, font, text_scale, text_color, text_thickness)
        # cv.putText(img, f"{text1}{tr}", text_position1, font, text_scale, text_color, text_thickness)
        cv.putText(img, f"{text2}{area2}", text_position1, font, text_scale, text_color, text_thickness)

        # frame2=cv.hconcat([frame,img])



        cv.imshow("yolo", frame)

        if cv.waitKey(1) == 27:
            break

    capture.release()
    cv.destroyAllWindows()

fun1()