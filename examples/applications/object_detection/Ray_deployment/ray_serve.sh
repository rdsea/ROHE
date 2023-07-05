#! /bin/bash


# Mount data before runing if using minikube
# minikube mount <path>/object_detection_ray/source:/odmount

# Create namespace for each application
kubectl create namespace od-ray

# Deploy head service
kubectl create -f ray_cluster/ray_head_light.yml


# Check all heads are running
flag=0
condition="No resources found"

while [ $flag -lt 1 ]
do
    kubequery=$(kubectl get pods -n od-ray  --field-selector=status.phase!=Running 2>&1)
    if [[ "$kubequery" == *"$condition"* ]]; then
        echo "All heads are running"
        flag=2
    else
        echo "Waiting"
        echo $kubequery
    fi
    sleep 1
done
echo "Head Deployment Finish"

# Check all worker are running
kubectl create -f ray_cluster/ray_worker.yml

flag=0

while [ $flag -lt 1 ]
do
    kubequery=$(kubectl get pods -n od-ray  --field-selector=status.phase!=Running 2>&1)
    if [[ "$kubequery" == *"$condition"* ]]; then
        echo "All workers are running"
        flag=2
    else
        echo "Waiting"
        echo $kubequery
    fi
    sleep 1
done

echo "Worker Deployment Finish"


# headpod=$(kubectl get pods --no-headers -o custom-columns=":metadata.name" -n od-ray 2>&1 | grep head)
# echo "Head node: "${headpod}
# echo "Copying deployment to ray server"
# kubectl cp ./source od-ray/${headpod}:/home/ray/source
# echo "Copying deployment finish"
# kubectl patch svc raycluster-heterogeneous-head-svc --type merge -p '{"spec":{"ports": [{"port": 8111,"protocol": "TCP","targetPort": 8111,"name":"od","nodePort": 30004}],}}' -n od-ray
# kubectl exec -it -n od-ray ${headpod} -- ./source/serve.sh 
# kubectl port-forward -n od-ray service/raycluster-heterogeneous-head-svc 32641:8265
# kubectl expose service -n od-ray raycluster-heterogeneous-head-svc --port=8111 --target-port=8111 --name=raycluster-heterogeneous-head-svc
# kubectl exec -it -n od-ray raycluster-heterogeneous-head-vv6qr -- /bin/bash
# kubectl describe svc raycluster-heterogeneous-head-svc -n od-ray