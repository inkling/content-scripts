#!/usr/bin/env bash
set -e

echo "== Checking prerequisites."

# Check prerequisites.
if [[ ! `command -v docker` ]]; then
  echo "Docker is required to run scripts."
  echo "Please install Docker from https://docs.docker.com/get-docker/ and then try again."
  exit 1
fi

DIR=`printf "%q\n" "$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"`

echo $DIR

installDir=${DIR:-remote-toolkit}'/inkling-rsync'
echo "== INSTALL DIR"
echo $installDir


echo "== Cloning repo..."
git clone git://github.com/inkling/content-scripts.git $installDir
echo "== Finish cloning repo."


if [[ $? == 0 ]]; then
  echo "== Docker compose..."
  echo "== Please run:"
  echo "[ docker exec -it inkling-rsync bash ]"
  echo "== to execute the container and start your machine tool:"
  docker-compose -f "$installDir/toolkit-compose.yml" up -d
else
  echo "* Error cloning git repo locally, unable to continue."
fi




