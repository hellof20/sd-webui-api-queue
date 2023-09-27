#!/bin/bash

export PROJECT_ID=speedy-victory-336109
export VPC_NETWORK=myvpc
export GKE_CLUSTER_NAME=my-gke
export REDIS_CLUSTER_NAME=sd-redis
export REGION=asia-southeast1
export ZONE=asia-southeast1-a
export FILESTORE_NAME=sd-filestore
export DOCKER_REPO_NAME=singapore
export TOPIC_NAME=sd-topic
export SD_WEBUI_IMAGE="asia-southeast1-docker.pkg.dev/speedy-victory-336109/singapore/sd-webui:inference"
export SD_SERVER_IMAGE="hellof20/sd-server:v1"
export SD_WORKER_IMAGE="hellof20/sd-worker:v1"

echo "Deleting k8s resource ..."
gcloud container clusters delete ${GKE_CLUSTER_NAME} --project ${PROJECT_ID} --region ${REGION} --async --quiet > /dev/null

echo "Deleting Pub/Sub resource ..."
gcloud pubsub subscriptions delete ${TOPIC_NAME}-sub --project ${PROJECT_ID} > /dev/null
gcloud pubsub topics delete ${TOPIC_NAME} --project ${PROJECT_ID} > /dev/null

echo "Deleting Redis ..."
gcloud redis instances delete ${REDIS_CLUSTER_NAME} --region ${REGION} --project ${PROJECT_ID} --async --quiet > /dev/null

echo "Deleting Filestore ..."
gcloud filestore instances delete ${FILESTORE_NAME} --project=${PROJECT_ID}  --location=${ZONE} --async --quiet > /dev/null

echo "Completed, the resource is being deleted asynchronously."