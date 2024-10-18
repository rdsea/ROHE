# ROHE dataset

- The dataset is collected from 3 applications: Base Transceiver Stations (BTS), KPI forecasting, and closed-circuit television surveillance (CCTVs).
- This repository contains the dataset used in the paper **On Optimizing Resources for Real-time End-to-End Machine Learning in Heterogeneous Edges** submitted to Software: Practice and Experience (SPE) journal.
- The structure of the dataset is as follows:
  - `bts` folder contains the dataset for BTS application.
    - `data_preparation` 
    - `data_transforming_and_feature_engineering`
    - `lstm_based_prediction`
  - `kpi` folder contains the dataset for KPI forecasting application.
    - `analytic_gateway`
    - `data_querying_and_preparation`
    - `network_measurement_forecasting`
  - `cctv` folder contains the dataset for CCTV application.
    - `image_ingestion`
    - `image_sharpening_and_transforming`
    - `object_detection`
- The data is collected from 3 layers, processed and storage in 3 different folders: application layer (`applications_extraced`), process (`resource_proc_metric`), and system (`resource_sys_metric`).
- In `applications_extraced` folder, the data is stored in CSV format with the following columns:
  - `response_time`: response time of each request sent to the service (unit:second).
  - `norm_time`: the timestamp showing the execution time that has been normalized.
- In `resource_proc_metric` folder, the data is stored in CSV format with the following columns:
  - `cpu_usage`: cpu time (unit:millicpu).
  - `memory_usage: memory usage (unit:Mb).
  - `gpu_usage`: gpu usage (unit:percentage).
  - `no_child`: number of child processes.
  - `no_child_active`: number of active child processes.
  - `child_cpu`: cpu time of child processes (unit:millicpu).
  - `child_memory`: memory usage of child processes (unit:Mb).
  - `execution_time`: normalized execution time of the process (unit:second).
- In `resource_sys_metric` folder, the data is stored in different folder for different devices in CSV format with the following columns:
  - `core1`: cpu time of core 1 (unit:percentage).
  - `core2`: cpu time of core 2 (unit:percentage).
  - `core3`: cpu time of core 3 (unit:percentage).
  - `core4`: cpu time of core 4 (unit:percentage).
  - up to `coreN` for N cores.
  - `mem`: memory usage (unit:Mb).
  - `gpu`: gpu usage (unit:percentage).
  - `norm_ex_time`: the timestamp showing the execution time that has been normalized.
- The dataset is collected in multiple runs, each run is stored in a separate folder. Due to limited storage, the repository only contains the dataset for the first run (`run_0`). The dataset for the other runs can be requested by contacting the authors.
- The dataset currently only contains the profiling data. We will upload the experiment data in [Zenodo](zenodo.org) after processed. For more information, please contact the authors.
- Cite the dataset as follows:
```bibtex
@article{rohe,
  title={On Optimizing Resources for Real-time End-to-End Machine Learning in Heterogeneous Edges},
  author={Minh-Tri Nguyen and Hong-Linh Truong},
  journal={Software: Practice and Experience},
  year={2024},
  publisher={Wiley}
}
```

Contact: Minh-Tri Nguyen (tri.m.nguyen@aalto.fi)