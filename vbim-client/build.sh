#!/bin/bash

# Enter the container name and Dockerfile as command line parameters
CONTAINER=$1
DOCKERFILE=$1.docker

# Can explicitly identify the container name and Dockerfile as well
# CONTAINER='vbim'
# DOCKERFILE='vbim.docker'

docker build --network=host $NO_CACHE --rm=true --file ${DOCKERFILE} --tag ${CONTAINER} . && echo "Finished building ${CONTAINER}"
