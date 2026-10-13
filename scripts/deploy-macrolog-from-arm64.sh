#!/bin/bash

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 <tag>"
    exit 1
fi

tag=$1

# tag release
echo "[INFO] tagging release ($tag)"
git tag -a "$tag" -m "Release version $tag"
git push origin "$tag"

# build & push docker image
echo "[INFO] building docker image"
docker buildx build --platform linux/amd64 -t docker.io/xadamz23/macro-log:$tag --load .

echo "[INFO] pushing docker image"
docker push xadamz23/macro-log:$tag

# ssh to host and update app
echo "[INFO] ssh'ing to docker-public vm"
ssh -o BatchMode=yes root@docker-public.stizzle.org  "/home/dockerapps/macrolog/update-app.sh $tag"
