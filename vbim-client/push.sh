#!/bin/bash

# Enter the container name and Dockerhub repository as command line parameters
CONTAINER=$1
CONTAINERTAG=$2

# Can explicitly identify the container name and Dockerhub repository as well
# CONTAINER='vbim'
# CONTAINERTAG='cmidoglu/vbim-demo'

docker login
docker tag ${CONTAINER} ${CONTAINERTAG} && docker push ${CONTAINERTAG} && echo "Finished uploading ${CONTAINERTAG}"
