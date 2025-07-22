FROM rdsea/onnx_runtime:cuda_10.2

WORKDIR /time_series_inference

RUN apt-get update

RUN apt-get install -y ffmpeg libsm6 libxext6 vim

RUN pip install --upgrade pip

COPY ./time_series_inference/*.toml ./

RUN pip install --no-cache-dir -e .

COPY ./time_series_inference ./

EXPOSE 5001

ENTRYPOINT ["tail", "-f", "/dev/null"]
# ENTRYPOINT ["python", "time_series_inference.py"]