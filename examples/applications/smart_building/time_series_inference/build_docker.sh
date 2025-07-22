#!/bin/bash
# NOTE: Need to be run in the parent directory of the 'inference' directory
# If qemu is not available, host system may not be able to build the docker image for arm64 platform

if [ "$1" == "cpu" ] || [ "$1" == "cuda" ]; then
  TAG=$1
else
  echo "Usage: $0 {cpu|cuda}"
  exit 1
fi

cd ..

echo ""

# Determine the platform based on the tag
if [ "$TAG" == "cpu" ]; then
  PLATFORM="linux/amd64,linux/arm64"
else
  PLATFORM="linux/arm64"
fi

docker build --platform $PLATFORM -t rdsea/multi_modal_time_series_inf:"$TAG" -f ./time_series_inference/Dockerfile .