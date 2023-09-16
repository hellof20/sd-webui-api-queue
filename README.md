# sd-webui-api-queue

## Setup 
```
export GKE_CLUSTER_NAME=sd-cluster
export REDIS_CLUSTER_NAME=sdcluster
export PROJECT_ID=speedy-victory-336109
export REGION=asia-southeast1
export ZONE=asia-southeast1-a
export VPC_NETWORK=myvpc
export FILESTORE_NAME=sdfilestore
export FILESHARE_NAME=sd
export DOCKER_REPO_NAME=singapore
export TOPIC_NAME=sd-input
export SD_API_SERVER_IMAGE="asia-southeast1-docker.pkg.dev/speedy-victory-336109/singapore/gcp-sd-api:v4"
export SD_WORKER_IMAGE="asia-southeast1-docker.pkg.dev/speedy-victory-336109/singapore/gcp-sd-worker:v5"
export SD_WEBUI_IMAGE="asia-southeast1-docker.pkg.dev/speedy-victory-336109/singapore/sd-webui:inference"
```

## Enable services
```
gcloud services enable compute.googleapis.com artifactregistry.googleapis.com container.googleapis.com file.googleapis.com
```

## Create public gke cluster
```
gcloud container clusters create ${GKE_CLUSTER_NAME} \
    --project ${PROJECT_ID} \
    --network ${VPC_NETWORK} \
    --release-channel "None" \
    --image-type "UBUNTU_CONTAINERD" \
    --num-nodes 1 \
    --enable-autoscaling --total-min-nodes "1" --total-max-nodes "2" --location-policy "BALANCED" \
    --machine-type "g2-standard-4" \
    --accelerator type=nvidia-l4,count=1 \
    --addons HorizontalPodAutoscaling,HttpLoadBalancing,GcePersistentDiskCsiDriver,GcpFilestoreCsiDriver \
    --enable-image-streaming \
    --scopes "https://www.googleapis.com/auth/cloud-platform" \
    --region ${REGION} \
    --node-locations ${ZONE}
```

## Grant default service account pub/sub read and write permissions.

## Install nvidia driver
https://cloud.google.com/kubernetes-engine/docs/how-to/gpus?hl=zh-cn#ubuntu
```
kubectl apply -f https://raw.githubusercontent.com/GoogleCloudPlatform/container-engine-accelerators/master/nvidia-driver-installer/ubuntu/daemonset-preloaded-R525.yaml
```

## Docker repo
```
gcloud artifacts repositories create ${DOCKER_REPO_NAME} --repository-format=docker --location=${REGION}
```

## Build docker image
```
gcloud auth configure-docker ${REGION}-docker.pkg.dev
docker build -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/${DOCKER_REPO_NAME}/gcp-sd-api:v1 -f docker/Dockerfile.server .
docker build -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/${DOCKER_REPO_NAME}/gcp-sd-worker:v2 -f docker/Dockerfile.worker .
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/${DOCKER_REPO_NAME}/gcp-sd-api:v1
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/${DOCKER_REPO_NAME}/gcp-sd-worker:v1
```

## Pub/Sub
```
gcloud pubsub topics create ${TOPIC_NAME} --project ${PROJECT_ID}
gcloud pubsub subscriptions create ${TOPIC_NAME}-sub --topic=${TOPIC_NAME} --project ${PROJECT_ID}
```

## Redis
```
gcloud redis instances create ${REDIS_CLUSTER_NAME} \
    --project=${PROJECT_ID}  \
    --tier=basic \
    --size=1 \
    --region=${REGION} \
    --redis-version=redis_6_x \
    --network=${VPC_NETWORK} \
    --zone=${ZONE} \
    --connect-mode=DIRECT_PEERING
```

## Filestore
```
gcloud filestore instances create ${FILESTORE_NAME} \
    --project=${PROJECT_ID}  \
    --zone=${ZONE} \
    --tier=BASIC_HDD \
    --file-share=name=${FILESHARE_NAME},capacity=1TB \
    --network=name=${VPC_NETWORK}
```

## Deploy
```
export log_level="debug"
export topic_name="projects/${PROJECT_ID}/topics/${TOPIC_NAME}"
export subscription_id="${TOPIC_NAME}-sub"
export subscription="projects/${PROJECT_ID}/subscriptions/${TOPIC_NAME}-sub"
export redis_host=$(gcloud redis instances describe ${REDIS_CLUSTER_NAME} --project=${PROJECT_ID} --region=${REGION} --format json|jq -r .host)
export filestore_ip=$(gcloud filestore instances describe ${FILESTORE_NAME} --project=${PROJECT_ID} --zone=${ZONE} --format json |jq -r .networks[].ipAddresses[])

kubectl create configmap worker-config \
    --from-literal=SUBSCRIPTION=${subscription} \
    --from-literal=REDIS_HOST=${redis_host} \
    --from-literal=LOG_LEVEL=${log_level}

kubectl create configmap api-server-config \
    --from-literal=TOPIC_NAME=${topic_name} \
    --from-literal=REDIS_HOST=${redis_host} \
    --from-literal=LOG_LEVEL=${log_level}

envsubst < kubernetes/sd-api-server.yaml | kubectl apply -f -
envsubst < kubernetes/sd-webui.yaml | kubectl apply -f -

```

## Auto scaling with pub/sub topic message num
```
kubectl apply -f https://raw.githubusercontent.com/GoogleCloudPlatform/k8s-stackdriver/master/custom-metrics-stackdriver-adapter/deploy/production/adapter_new_resource_model.yaml
envsubst < kubernetes/hpa.yaml | kubectl apply -f -
```

## Clean
```
kubectl delete -f kubernetes/sd-api-server.yaml
kubectl delete -f kubernetes/sd-webui.yaml
kubectl delete configmap worker-config
kubectl delete configmap api-server-config
kubectl delete -f kubernetes/hpa.yaml
```
