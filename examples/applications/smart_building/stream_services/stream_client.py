# The script is to stream video and sensor data from the MMAct dataset. 
# The script reads the video and sensor data files of certain activities streams the data using ZeroMQ.
# The video and sensor data of each activity are streamed in parallel with the same starting/ending time.

import requests
import cv2
import zmq
import time
import yaml
import logging
import csv
import threading
from concurrent.futures import ThreadPoolExecutor
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from rohe.common.rohe_utils import find_all_files_in_mmact

logging.basicConfig(level=logging.INFO)


# Set default ports for each sensor
VIDEO_PORT = 5555
ACC_PHONE_PORT = 5556
ACC_WATCH_PORT = 5557
GYRO_PORT = 5558
ORIENTATION_PORT = 5559


DEVICE_PATH = ['acc_phone_clip', 'acc_watch_clip', 'gyro_clip', 'orientation_clip']
port_dict = {
    "video": VIDEO_PORT,
    "acc_phone_clip": ACC_PHONE_PORT,
    "acc_watch_clip": ACC_WATCH_PORT,
    "gyro_clip": GYRO_PORT,
    "orientation_clip": ORIENTATION_PORT
}

CONFIG_FILE = 'stream_config.yaml'
DATA_PATH = os.getenv('DATA_PATH')

CSV_DIR = os.path.join(DATA_PATH, 'mmact/trimmed_sensor/')
print(f"CSV directory: {CSV_DIR}")

MP4_DIR = os.path.join(DATA_PATH, 'mmact/trimmed_video/')
print(f"MP4 directory: {MP4_DIR}")

# Number of modality to stream in parallel
MAX_WORKERS = 8

stream_config = {}
registration_data = {}
stop_event = threading.Event()
update_timer = None



csv_file_path_list, csv_file_info_list = find_all_files_in_mmact(CSV_DIR, '.csv')
mp4_file_path_list, mp4_file_info_list = find_all_files_in_mmact(MP4_DIR, '.mp4')

def get_video_info(video_path):
    cap = cv2.VideoCapture(video_path)
    
    # Get the total number of frames
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Get the frame rate
    frame_rate = cap.get(cv2.CAP_PROP_FPS)
    
    # Calculate the length of the video in seconds
    video_length = total_frames / frame_rate
    
    cap.release()
    return video_length, total_frames, frame_rate

def update_frame_rate():
    global stream_config
    global update_timer
    global registration_data
    with open(CONFIG_FILE, 'r') as f:
        config = yaml.safe_load(f)
    # logging.info(f"Updating frame rate config: {config['frame_rate_config']}")
    logging.info(f"Updating frame rate config")
    stream_config = config['frame_rate_config']
    registration_data = config['registration_data']
    # Schedule the next update
    update_timer = threading.Timer(stream_config['update_interval'], update_frame_rate)
    update_timer.start()

def stream_video(video_path, zmq_port):
    global stream_config
    try:
        context = zmq.Context()
        socket = context.socket(zmq.PUB)
        socket.bind(f"tcp://*:{zmq_port}")

        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_rate = cap.get(cv2.CAP_PROP_FPS)
        # frame_rate = stream_config["frame_rate"]
        frame_count = 0
        while cap.isOpened():
            try:
                ret, frame = cap.read()
                if frame is None:
                    continue
                resized_frame = cv2.resize(frame, (320, 240))
                if not ret:
                    break
                _, buffer = cv2.imencode('.jpg', resized_frame)
                socket.send(buffer)
                frame_count += 1
                time.sleep(1 / frame_rate)
                if frame_count == total_frames:
                    break
            except Exception as e:
                logging.error(f"Error while streaming video frame: {e}")
                break
        cap.release()
    except Exception as e:
        logging.error(f"Error while reading video: {e}")
        return "error"
    logging.info(f"Finished streaming video")
    return "success"
    
def send_csv_data(csv_file, zmq_port, video_length):
    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.bind(f"tcp://*:{zmq_port}")

    with open(csv_file, 'r') as f:
        try:
            logging.info(f"Start streaming csv data: {csv_file}")
            reader = csv.reader(f)
            rows = list(reader)
            num_rows = len(rows)
            interval = video_length / num_rows

            for row in rows:
                try:
                    timestamp = row[0]
                    data = row[1:]
                    message = f"{timestamp},{','.join(data)}"
                    socket.send_string(message)
                    time.sleep(interval)
                except Exception as e:
                    logging.error(f"Error while sending csv data: {e}")
        except Exception as e:
            logging.error(f"Error while reading csv data: {e}")
            return "error"
    logging.info(f"Finished streaming csv data")
    return "success"
if __name__ == "__main__":
    update_frame_rate()
    for key in port_dict.keys():
        if key in registration_data:
            print(f"Registration data: {registration_data[key]}")
            response = requests.post("http://localhost:5550/add_stream_handler", json=registration_data[key])
            response_data = response.json()
            port_dict[key] = response_data['port'] 
            print(response_data)
    time.sleep(1)
    update_frame_rate_interval = stream_config['update_interval']

    for mp4_info in mp4_file_info_list:
        try:
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                try:
                    video_path = mp4_info['file_path']
                    video_length, total_frame, frame_rate = get_video_info(video_path)
                    video_process = executor.submit(stream_video, video_path, port_dict["video"])
                except Exception as e:
                    logging.error(f"Error while streaming video: {e}")
                    video_process.terminate()
                try:
                    result_dict = {}
                    for device in DEVICE_PATH:
                        try:
                            csv_file_path = os.path.join(CSV_DIR, device, mp4_info['subject'], mp4_info['scene'], mp4_info['session'], f"{mp4_info['label']}.csv")
                            # result_dict[device] = executor.submit(send_csv_data, csv_file_path, port_dict[device], video_length)
                            result_dict[device] = executor.submit(send_csv_data, csv_file_path, port_dict[device], 20)
                        except Exception as e:
                            logging.error(f"Error while streaming {device} csv: {e}")
                except Exception as e:
                    logging.error(f"Error while streaming csv: {e}")
                logging.info(f"Waiting for all tasks to complete")
                executor.shutdown(wait=True)  # Ensure all tasks are completed before exiting
        except Exception as e:
            logging.error(f"Error while streaming parallel data: {e}")
        logging.info(f"Streaming {mp4_info['label']} data Finished")
        time.sleep(1)
    update_timer.cancel()
    stop_event.set()
    