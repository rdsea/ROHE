FROM rdsea/od_ray_light:1.0

USER root
WORKDIR /home

COPY ./serve.sh /home

EXPOSE 8111 8000 6379 8265 10001 52365

ENTRYPOINT ["/bin/bash", "/home/serve.sh"]
