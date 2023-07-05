#! /bin/bash

ray start --address 'ray-head-light-service:6379'
tail -f /dev/null