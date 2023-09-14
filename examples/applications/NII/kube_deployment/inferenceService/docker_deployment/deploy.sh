#!/bin/bash

# Run the Python script to copy relevant files
python copy_relevant_files.py --conf=config.json

# Build the Docker image
docker build -t vtn13042000/nii_inference_service_intel:1.0.0 .

# Run the Python script to delete relevant files
python delete_relevant_files.py --conf=config.json

# Run docker-compose up
docker-compose up -d

