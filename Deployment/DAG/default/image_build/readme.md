# This repo is to build docker images for tasks (Data preprocessing, ML model,...)

- Inside python directory is docker file for a simple image providing python environment
- Inside unbuntu_20_04 directory is some docker files for BTS's task running on ubuntu 20.04 
The images is build based on the ubuntu core groovy cloudimg for arm64, you can find it [here](https://partner-images.canonical.com/core/groovy/current/)

- Build an image:
```bash
$ docker build -t <repo_name>/<image_name>:<tag/version> -f <dockerfile_path> <build_directory>
```
Example:
```bash
$ docker build -t minhtribk12/data_ubuntu:1.0 -f ./docker_data_pros/Dockerfile .
```

- Push an image to Dockerhub:
```bash
docker push <repo_name>/<image_name>:<tag/version>
```

When building new image, you may create some dangling images which have same name/tag with existing one so you may want to remove them:
```bash
docker rmi $(docker images -q --filter "dangling=true")
```

Every preprocessing task can be defined as a Python class that has `data_preprocessing` function. The class then will be import to the main process which is running as a Flask application listening to request via Rest APIs or RabbitMQ message consumer.

The ML task is on re-implementing.