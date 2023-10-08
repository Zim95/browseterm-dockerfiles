#!/bin/bash

docker login -u zim95
docker tag ssh_ubuntu:latest zim95/ssh_ubuntu:latest
docker push zim95/ssh_ubuntu:latest