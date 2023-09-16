#!/bin/bash
export GKE_CLUSTER_NAME=sd-gke
export REDIS_CLUSTER_NAME=sd-redis
export PROJECT_ID=speedy-victory-336109
export REGION=asia-southeast1
export ZONE=asia-southeast1-a
export FILESTORE_NAME=sd-filestore
export DOCKER_REPO_NAME=singapore
export TOPIC_NAME=sd-topic

echo "Deleting k8s resource ..."
gcloud container clusters delete ${GKE_CLUSTER_NAME} --project ${PROJECT_ID} --region ${REGION} --async --quiet

echo "Deleting Pub/Sub resource ..."
gcloud pubsub subscriptions delete ${TOPIC_NAME}-sub --project ${PROJECT_ID}
gcloud pubsub topics delete ${TOPIC_NAME} --project ${PROJECT_ID}

echo "Deleting Redis ..."
gcloud redis instances delete ${REDIS_CLUSTER_NAME} --region ${REGION} --project ${PROJECT_ID} --async --quiet

echo "Deleting Filestore ..."
gcloud filestore instances delete ${FILESTORE_NAME} --project=${PROJECT_ID}  --location=${ZONE} --async --quiet