from typing import List
from supervision.tools.detections import Detections
from ByteTrack.yolox.tracker.byte_tracker import STrack
from onemetric.cv.utils.iou import box_iou_batch
import numpy as np
import csv
import cv2
from collections import defaultdict

# converts Detections into format that can be consumed by match_detections_with_tracks function
def detections2boxes(detections: Detections) -> np.ndarray:
    return np.hstack((
        detections.xyxy,
        detections.confidence[:, np.newaxis]
    ))


# converts List[STrack] into format that can be consumed by match_detections_with_tracks function
def tracks2boxes(tracks: List[STrack]) -> np.ndarray:
    return np.array([
        track.tlbr
        for track
        in tracks
    ], dtype=float)


# matches our bounding boxes with predictions
def match_detections_with_tracks(
    detections: Detections,
    tracks: List[STrack]
) -> Detections:
    if not np.any(detections.xyxy) or len(tracks) == 0:
        return np.empty((0,))

    tracks_boxes = tracks2boxes(tracks=tracks)
    iou = box_iou_batch(tracks_boxes, detections.xyxy)
    track2detection = np.argmax(iou, axis=1)

    tracker_ids = [None] * len(detections)

    for tracker_index, detection_index in enumerate(track2detection):
        if iou[tracker_index, detection_index] != 0:
            tracker_ids[detection_index] = tracks[tracker_index].track_id

    return tracker_ids


#temp.csv write process data first written and compiled
def write_temp(uid: int,stream_name: str, date: str, time: str, vehicle_class: str, astate: str, folder_name: str):
    filename = f'./temp/{folder_name}/temp.csv'
    with open(filename, mode='a', newline='') as file:
        writer = csv.writer(file)
        data = [uid, stream_name, date, time, vehicle_class, astate]
        writer.writerow(data)
    return None


def tracker_polylines(detections: Detections, frame: np.ndarray, track_history: dict):
    # Draw tracking lines
    if detections.xyxy is None:
        del detections
    else:
        for box, track_id in zip(detections.xyxy, detections.tracker_id):
            x, y, w, h = box
            track = track_history[track_id]
            track.append((float((x+w)/2), float((y+h)/2)))  # x, y center point
            if len(track) > 30:  # retain 90 tracks for 90 frames
                track.pop(0)

            # Draw the tracking lines
            points = np.hstack(track).astype(np.int32).reshape((-1, 1, 2))
            cv2.polylines(frame, [points], isClosed=False, color=(230, 230, 230), thickness=10)
    return frame

def config_writer():

    config_file_path = "config.csv"

    fields = ["Video_Path", "Video_Name", "LINE_START", "LINE_END", "Update_cycle","Flip","Play_speed"]

    rows = [["sample1.mp4", "CAM1", 0, 650, 1920, 650, 2,1,1]]

    with open(config_file_path, mode='w', newline="") as file:
        writer = csv.writer(file)
        writer.writerow(fields)
        writer.writerows(rows)

    return None

def config_reader(config_file_path):

    config_data = []
    try:
        with open(config_file_path, mode='r', newline="") as file:
            data = csv.reader(file)
            flag = bool(True)
            for row in data:
                if flag:
                    flag = False
                    continue
                row_data = []
                for config in row:
                    if config.isdigit():
                        config = int(config)
                        row_data.append(config)
                        #print(config," ",type(config))
                    else:
                        row_data.append(config)
                        #print(config," ",type(config))
                if len(row_data) == 9:
                    config_data.append(row_data)
                else:
                    print("Invalid configurations.")
    except:
        raise Exception("Connot read config file")


    return config_data
