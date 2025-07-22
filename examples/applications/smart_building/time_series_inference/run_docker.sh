#!/bin/bash
# Mount host ./data to container /data and ./model to /model
docker run -p 5001:5001 --net host rdsea/multi_modal_time_series_inf:cpu -v $(pwd)/data:/data -v $(pwd)/model:/model