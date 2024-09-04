#!/bin/bash
set -euo pipefail

# run this script using `sudo -E ./bootstrap.sh`, otherwise it won't work
################################################################################

# external vars the user may override
################################################################################
WITH_AUTOUPDATES=${WITH_AUTOUPDATES:-1}
NVIDIA_DRIVER_VERSION=${NVIDIA_DRIVER_VERSION:-535}
NO_LAUNCH=${NO_LAUNCH:-0}


# internal vars
################################################################################
REBOOT_REQUIRED=0
DEBIAN_FRONTEND=noninteractive
export DEBIAN_FRONTEND=noninteractive

function echo_() {
  echo "# $@"
  echo "################################################################################"
}


# check for root and setup exit trap
################################################################################
if [[ $(id -u) -ne 0 ]]; then
  echo_ "Please run this script as root."
  exit 1
fi

function on_exit_ {
  echo_ cleaning up...
  apt-mark unhold openssh-server
}
trap on_exit_ INT TERM EXIT


# setup base files/folders
################################################################################
echo_ setting up base files and folders
touch $HOME/.bashrc
chown $SUDO_USER:$SUDO_USER $HOME/.bashrc
chmod 644 $HOME/.bashrc

mkdir -p $HOME/.local/bin
if ! [[ $(echo $PATH | grep "$HOME/.local/bin") ]]; then
  echo '' >> $HOME/.bashrc
  echo 'export PATH=$HOME/.local/bin:$PATH' >> $HOME/.bashrc
fi
chown -R $SUDO_USER:$SUDO_USER $HOME/.local


# do not upgrade openssh server whilst installing
################################################################################
apt-mark hold openssh-server

# fix anything broken, update stuff, and install base software
################################################################################
echo_ setting up base packages
apt update -qq
apt install -y vim git curl wget cron net-tools dnsutils software-properties-common


# python 3.11
################################################################################
echo_ checking for python3.11
if ! [[ $(which python3.11) ]]; then
  echo_ python3.11 was not found, installing...
  add-apt-repository -y ppa:deadsnakes/ppa
  apt install -y python3.11-full
  python3.11 -m ensurepip
fi

# ensure `python` and `pip` point to the right place
rm /usr/bin/pip || true
echo '#!/bin/bash' >> /usr/bin/pip
echo 'python3.11 -m pip $@' >> /usr/bin/pip
chmod a+x /usr/bin/pip

rm /usr/bin/python || true
ln -s $(which python3.11) /usr/bin/python

# docker
################################################################################
echo_ checking for docker
if ! [[ $(which docker) ]]; then
  echo_ docker was not found, installing...
  apt update -qq
  apt install -y docker.io
  systemctl enable --now docker
fi

groupadd docker || true
usermod -aG docker $SUDO_USER || true


# Nano for config
################################################################################
echo_ checking for nano
if ! [[ $(which nano) ]]; then
  echo_ nano was not found, installing...
  apt-get update
  apt-get install nano
fi

# configure servers to start on boot
################################################################################
if [[ NO_LAUNCH -eq 1 ]]; then
  :
else
  if [[ WITH_AUTOUPDATES -eq 1 ]]; then
    sudo -E ./validator_autoupdater.sh
  else
    docker-compose --env-file .prod.env -f docker-compose.prod.yml up -d
    echo "@reboot $(which docker-compose) --env-file $(pwd)/.prod.env -f $(pwd)/docker-compose.prod.yml up -d" | sudo tee -a /etc/crontab
  fi
fi


# finally, reboot if needed
################################################################################
if [[ REBOOT_REQUIRED -eq 1 ]]; then
  echo_ "bootstrap.sh modified something that requires a reboot. Please SSH back in to this machine after a short while :)"
  shutdown now -r
else
  echo_ "bootstrap.sh is all done :)"
fi