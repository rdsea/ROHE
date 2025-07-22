#!/bin/bash
# Mount host ./data to container /data and ./model to /model
docker run -p 5001:5001 --net host rdsea/multi_modal_video_inf:cuda -v $(pwd)/data:/data -v $(pwd)/model:/model