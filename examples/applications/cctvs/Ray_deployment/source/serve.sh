#! /bin/bash

ray start --head --port 6379
sleep 2
python /home/source/composition.py
tail -f /dev/null