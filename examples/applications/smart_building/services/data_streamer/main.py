"""Smart Building data streamer.

Streams sensor data for 5 modalities (video, acc_phone, acc_watch, gyro, orientation)
to DataHub continuously. Reads from dataset/ or generates synthetic data.
"""
from common.streamer_service import create_streamer_app

app = create_streamer_app()
