FROM python@sha256:129e3d1bee00d9e915d49ded6a1103f567c9fb715c8e5fdc1113a6e71d12d3f9

WORKDIR /proc-server
COPY ./requirements.txt .
RUN apt update
RUN apt install -y wget vim gcc python3-dev
RUN pip install -r requirements.txt
RUN pip3 install qoa4ml==0.0.59
COPY . .

EXPOSE 5000
# USER nobody
# ENTRYPOINT ["tail", "-f", "/dev/null"]
CMD ["gunicorn", "-k", "eventlet", "-b", "0.0.0.0:5000", "preprocessor:app"]
