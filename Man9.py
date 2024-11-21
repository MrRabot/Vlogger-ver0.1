import torch
print("Torch version: ", torch.__version__)
import os
from datetime import datetime
import cv2
from dataclasses import dataclass
from supervision.tools.detections import Detections
from ByteTrack.yolox.tracker.byte_tracker import BYTETracker
from Utils import *
import ultralytics
from line_counter import LineCounter, LineCounterAnnotator
from supervision.tools.detections import Detections, BoxAnnotator
from supervision.draw.color import ColorPalette
import supervision
import threading
from Utils import tracker_polylines

def tracker_in_thread(video_path: str, model: ultralytics.models.yolo.model.YOLO, vh_model: ultralytics.models.yolo.model.YOLO, out_stream: str
                      ,LINE_START: supervision.geometry.dataclasses.Point, LINE_END: supervision.geometry.dataclasses.Point, Update_time: int, thread_no: int, IN_OUT: list, global_events: list
                      ,local_event: list, Flip: bool, Play_speed: int):
    

    #some constants needed
    vehicles = [2, 3, 5, 7]
    CLASS_NAMES_DICT2 = vh_model.model.names
    CLASS_NAMES_DICT = model.model.names

    flag = bool(0)

    #bytetracker args
    @dataclass(frozen=True)
    class BYTETrackerArgs:
        track_thresh: float = 0.25
        track_buffer: int = 30
        match_thresh: float = 0.8
        aspect_ratio_thresh: float = 3.0
        min_box_area: float = 1.0
        mot20: bool = False
    

    #Control events
    run_thread = local_event[0]
    show_vid = local_event[1]
    
    run_process = global_events[0]

    show_label1 = global_events[1]
    show_label2 = global_events[2]
    show_labels = global_events[3]

    track_history = defaultdict(lambda: [])

    if not os.path.isfile(video_path):
        raise Exception("No video found: ", out_stream)

    #using cv2 to read video
    try:
        cap = cv2.VideoCapture(video_path)
        folder_name = f"{out_stream} {datetime.now().strftime('%Y-%m-%d %H-%M-%S')}"
        try:
            os.makedirs(os.path.join("./cache", folder_name))
            os.makedirs(os.path.join("./temp", folder_name))
        except:
            raise Exception("Could not make directories")
    except:
        raise Exception("Cannot Read video")
    
    
    #setting analytics display
    line_counter = LineCounter(start=LINE_START, end=LINE_END)
    box_annotator = BoxAnnotator(color=ColorPalette(), thickness=3, text_thickness=2, text_scale=2, text_padding= -5)
    line_annotator = LineCounterAnnotator(thickness=4, text_thickness=4, text_scale=2)

    #initializing tracker
    tracker = BYTETracker(BYTETrackerArgs)
    
    #Create cycle
    count = 60*12 #*Update_time

    #starting video reading for detections
    while cap.isOpened() and run_process.is_set() and run_thread.is_set():

        rt, frame = cap.read()
        if rt:
            # detections
            results= model(frame)
            # formatting results
            detections = Detections(
                xyxy=results[0].boxes.xyxy.cpu().numpy(),
                confidence=results[0].boxes.conf.cpu().numpy(),
                class_id=results[0].boxes.cls.cpu().numpy().astype(int)
            )
            # passing detection boxes to tracker
            tracks = tracker.update(
                output_results=detections2boxes(detections=detections),
                img_info=frame.shape,
                img_size=frame.shape
            )
            tracker_id = match_detections_with_tracks(detections=detections, tracks=tracks)

            #vehicle detections
            vh_results = vh_model(frame, classes = vehicles, conf =0.5)
            #formatting
            vh_detections = Detections(
                xyxy=vh_results[0].boxes.xyxy.cpu().numpy(),
                confidence=vh_results[0].boxes.conf.cpu().numpy(),
                class_id=vh_results[0].boxes.cls.cpu().numpy().astype(int)
            )

            #assigning tracking id to vehicle
            vh_detections.tracker_id = np.array(tracker_id)
            #assigning tracking id to license plate
            detections.tracker_id = np.array(tracker_id)

            #trigger to save results
            IN_OUT[thread_no] = line_counter.update(detections, vh_detections, frame, out_stream, folder_name, CLASS_NAMES_DICT2, Flip)


            if show_labels.is_set():

                if show_label1.is_set():
                    labels = [
                        f"#{tracker_id} {CLASS_NAMES_DICT[class_id]} {confidence:0.2f}"
                        for _, confidence, class_id, tracker_id
                        in detections
                    ]
                    frame = box_annotator.annotate(frame=frame, detections=detections, labels=labels)
                    frame  = tracker_polylines(detections, frame, track_history)

                if show_label2.is_set():
                    labels = [
                        f"#{tracker_id} {CLASS_NAMES_DICT[class_id]}"
                        for _, confidence, class_id, tracker_id
                        in detections
                    ]

                    labels2 = [
                        f"#{tracker_id} {CLASS_NAMES_DICT2[class_id]}"
                        for _, confidence, class_id, tracker_id
                        in vh_detections
                    ]

                    frame = box_annotator.annotate(frame=frame, detections=detections, labels=labels)
                    frame = box_annotator.annotate(frame=frame, detections=vh_detections, labels=labels2)
                    
                

                line_annotator.annotate(frame=frame, line_counter=line_counter, Flip=Flip)

            
            if show_vid.is_set():
                flag = True
                cv2.imshow(out_stream, frame)
            
            #update cycle code
            count -= 1

            #create folder
            if count < 1:
                count = 60*12
                folder_name = f"{out_stream} {datetime.now().strftime('%Y-%m-%d %H-%M-%S')}"
                try:
                    os.makedirs(os.path.join("./cache", folder_name))
                    os.makedirs(os.path.join("./temp", folder_name))
                except:
                    print("Could not make directories")
            
            key = cv2.waitKey(Play_speed)
            if key == ord('q'):
                break
        else:
            break
    #create folder
    folder_name = f"{out_stream} {datetime.now().strftime('%Y-%m-%d %H-%M-%S')}"
    try:
        os.makedirs(os.path.join("./cache", folder_name))
        os.makedirs(os.path.join("./temp", folder_name))
    except:
        raise Exception("Could not make directories")

    cap.release()
    if show_vid.is_set() or flag:
        cv2.destroyWindow(out_stream)
    

         
   
