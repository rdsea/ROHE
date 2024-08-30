#!/bin/bash
# This script is for preparing environment for installing Kubernetes in a physical node

sudo apt install net-tools
sudo apt install openssh-server
sudo apt install vim

# install docker 
sudo apt-get update
sudo apt-get install \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

echo \
  "deb [arch=arm64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io
# sudo apt install docker.io

ssh-keygen -t rsa -b 4096 -f ~/.ssh/rpi -P ""
eval `ssh-agent -s`
ssh-add ~/.ssh/rpi

