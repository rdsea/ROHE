FROM rdsea/onnx_runtime:cuda_10.2

WORKDIR /video_inference

RUN apt-get update

RUN apt-get install -y ffmpeg libsm6 libxext6 vim

COPY ./video_inference/*.toml ./

RUN pip install --no-cache-dir -e .

COPY ./video_inference ./

EXPOSE 5001

ENTRYPOINT ["tail", "-f", "/dev/null"]
# ENTRYPOINT ["python", "video_inference.py"]