#!/bin/bash
set -e

# Required parameters
export PROJECT_ID=speedy-victory-336109
export VPC_NETWORK=myvpc
export REGION=asia-southeast1
export ZONE=asia-southeast1-a
export GKE_CLUSTER_NAME=my-gke
export REDIS_CLUSTER_NAME=sd-redis
export FILESTORE_NAME=sd-filestore
export FILESHARE_NAME=sd
export MODEL_NAME=v1-5-pruned-emaonly
export SD_WEBUI_IMAGE="asia-southeast1-docker.pkg.dev/speedy-victory-336109/singapore/sd-webui:inference"

# Optional parameters
export LOG_LEVEL="debug"
export SD_SERVER_IMAGE="hellof20/sd-server:v2"
export SD_WORKER_IMAGE="hellof20/sd-worker:v2"

echo "Enable services ... "
gcloud services enable compute.googleapis.com \
    artifactregistry.googleapis.com \
    containerfilesystem.googleapis.com \
    container.googleapis.com \
    file.googleapis.com \
    redis.googleapis.com \
    --project ${PROJECT_ID}

echo "Create public gke cluster ..."
gcloud container clusters create ${GKE_CLUSTER_NAME} \
    --project ${PROJECT_ID} \
    --network ${VPC_NETWORK} \
    --release-channel "None" \
    --num-nodes 1 \
    --enable-autoscaling --total-min-nodes "1" --total-max-nodes "10" --location-policy "BALANCED" \
    --machine-type "g2-standard-4" \
    --accelerator type=nvidia-l4,count=1 \
    --addons HorizontalPodAutoscaling,HttpLoadBalancing,GcePersistentDiskCsiDriver,GcpFilestoreCsiDriver \
    --enable-image-streaming \
    --scopes "https://www.googleapis.com/auth/cloud-platform" \
    --region ${REGION} \
    --node-locations ${ZONE} \
    --async

echo "Create Redis instance ..."
gcloud redis instances create ${REDIS_CLUSTER_NAME} \
    --project=${PROJECT_ID}  \
    --tier=basic \
    --size=1 \
    --region=${REGION} \
    --redis-version=redis_6_x \
    --network=${VPC_NETWORK} \
    --zone=${ZONE} \
    --connect-mode=DIRECT_PEERING \
    --async

echo " Create Filestore instance ..."
gcloud filestore instances create ${FILESTORE_NAME} \
    --project=${PROJECT_ID}  \
    --zone=${ZONE} \
    --tier=BASIC_HDD \
    --file-share=name=${FILESHARE_NAME},capacity=1TB \
    --network=name=${VPC_NETWORK} \
    --async

echo "Create Pub/Sub topic and subscription ..."
gcloud pubsub topics create ${MODEL_NAME} --project ${PROJECT_ID}
gcloud pubsub subscriptions create ${MODEL_NAME} --topic=${MODEL_NAME} --project ${PROJECT_ID} 

waitTime=0
ready="ok"
until [[ $(gcloud container clusters describe ${GKE_CLUSTER_NAME} --region ${REGION} --project ${PROJECT_ID} --format json | jq -r .status) == "RUNNING" ]] && 
    [[ $(gcloud redis instances describe ${REDIS_CLUSTER_NAME} --region ${REGION} --project ${PROJECT_ID} --format json| jq -r .state) == "READY" ]] &&
    [[ $(gcloud filestore instances describe ${FILESTORE_NAME} --location ${ZONE} --project ${PROJECT_ID} --format json| jq -r .state) == "READY" ]]; do
    sleep 10;
    waitTime=$(expr ${waitTime} + 10);
    echo "waited ${waitTime} secconds for GKE/Redis/Filestore to be ready ...";
    if [ ${waitTime} -gt 600 ]; then
        ready="failed";
        echo "Wait too long, deploy failed.";
        exit 1;
    fi
done

# if [ ${ready} == "ok" ];then
#     echo "Ready!"
# fi

echo "Get GKE Cluster Credential ..."
gcloud container clusters get-credentials ${GKE_CLUSTER_NAME} \
    --region ${REGION} \
    --project ${PROJECT_ID}

# Grant default service account pub/sub read and write permissions.
echo "Install L4 GPU driver ..."
# https://cloud.google.com/kubernetes-engine/docs/how-to/gpus?hl=zh-cn#ubuntu
# kubectl apply -f https://raw.githubusercontent.com/GoogleCloudPlatform/container-engine-accelerators/master/nvidia-driver-installer/ubuntu/daemonset-preloaded-R525.yaml
kubectl apply -f https://raw.githubusercontent.com/GoogleCloudPlatform/container-engine-accelerators/master/nvidia-driver-installer/cos/daemonset-preloaded-latest.yaml

echo "Deply sd-server and sd-worker to GKE ..."
export redis_host=$(gcloud redis instances describe ${REDIS_CLUSTER_NAME} --project=${PROJECT_ID} --region=${REGION} --format json|jq -r .host)
export filestore_ip=$(gcloud filestore instances describe ${FILESTORE_NAME} --project=${PROJECT_ID} --zone=${ZONE} --format json |jq -r .networks[].ipAddresses[])

kubectl create configmap sd-worker-config \
    --from-literal=MODEL_NAME=${MODEL_NAME} \
    --from-literal=PROJECT_ID=${PROJECT_ID} \
    --from-literal=REDIS_HOST=${redis_host} \
    --from-literal=LOG_LEVEL=${LOG_LEVEL}

kubectl create configmap sd-server-config \
    --from-literal=PROJECT_ID=${PROJECT_ID} \
    --from-literal=REDIS_HOST=${redis_host} \
    --from-literal=LOG_LEVEL=${LOG_LEVEL}

envsubst < kubernetes/sd-server.yaml | kubectl apply -f -
envsubst < kubernetes/sd-worker.yaml | kubectl apply -f -


# echo "Deploy autoscaling depend on pub/sub topic messages num ..."
# kubectl apply -f https://raw.githubusercontent.com/GoogleCloudPlatform/k8s-stackdriver/master/custom-metrics-stackdriver-adapter/deploy/production/adapter_new_resource_model.yaml
# envsubst < kubernetes/hpa.yaml | kubectl apply -f -


# kubectl get APIService
# kubectl -n custom-metrics edit deploy custom-metrics-stackdriver-adapter 修改cpu和memory
# image streaming


# export MODEL_NAME=cuteyukimixAdorable_specialchapter
# export PROJECT_ID=speedy-victory-336109
# export SD_WEBUI_IMAGE="asia-southeast1-docker.pkg.dev/speedy-victory-336109/singapore/sd-webui:inference"
# export SD_WORKER_IMAGE="hellof20/sd-worker:v2"
# export redis_host=$(gcloud redis instances describe ${REDIS_CLUSTER_NAME} --project=${PROJECT_ID} --region=${REGION} --format json|jq -r .host)
# export filestore_ip=$(gcloud filestore instances describe ${FILESTORE_NAME} --project=${PROJECT_ID} --zone=${ZONE} --format json |jq -r .networks[].ipAddresses[])

# kubectl create configmap sd-worker-config2 \
#     --from-literal=MODEL_NAME=${MODEL_NAME} \
#     --from-literal=PROJECT_ID=${PROJECT_ID} \
#     --from-literal=REDIS_HOST=${redis_host} \
#     --from-literal=LOG_LEVEL=${LOG_LEVEL}

# envsubst < kubernetes/sd-worker-2.yaml | kubectl apply -f -