# For Jetson GPU device 

Set default `runtime` to `nvidia` in `/etc/docker/daemon.json`

```bash
{
  "runtimes": {
    "nvidia": {
      "path": "/usr/bin/nvidia-container-runtime",
      "runtimeArgs": []
    }
  },
  "default-runtime": "nvidia"
}
```
Restart Docker daemon:
```bash
$ sudo systemctl restart docker
```
Build an image for manage gpu as a plugin [(read more)](https://github.com/NVIDIA/k8s-device-plugin) only each GPU node. The main release only support AMD, to make it works on arm64, we need to build with other patches below:

```bash
$ git clone -b 1.0.0-beta6 https://github.com/nvidia/k8s-device-plugin.git
$ cd k8s-device-plugin
$ wget https://labs.windriver.com/downloads/0001-arm64-add-support-for-arm64-architectures.patch
$ wget https://labs.windriver.com/downloads/0002-nvidia-Add-support-for-tegra-boards.patch
$ wget https://labs.windriver.com/downloads/0003-main-Add-support-for-tegra-boards.patch
$ git am 000*.patch
```
Build docker image locally on each GPU node:
```bash
$ sudo docker build -t nvidia/k8s-device-plugin:1.0.0-beta6 -f docker/arm64/Dockerfile.ubuntu16.04 .
```
On master node, apply the plugin:
```bash
$ sudo kubectl apply -f nvidia-device-plugin.yml

```
Show plugin deployment:
```bash
$ sudo kubectl get pods -A
```
If it works correctly, we can log the pods as follow
```bash
$ sudo kubectl logs nvidia-device-plugin-daemonset-<random_code> --namespace=kube-system
```

Or describe node:
```bash
$ sudo kubectl describe node <name_node>
```
Output:
```bash
...
Allocated resources:
  (Total limits may be over 100 percent, i.e., overcommitted.)
  Resource           Requests   Limits
  --------           --------   ------
  cpu                100m (2%)  0 (0%)
  memory             70Mi (1%)  170Mi (4%)
  ephemeral-storage  0 (0%)     0 (0%)
  hugepages-2Mi      0 (0%)     0 (0%)
  nvidia.com/gpu     0          0
...
```