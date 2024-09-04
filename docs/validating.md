# Full instructions for setup

Welcome to S19 Validating 🔥


## Contents:

- [Orchestrator setup](#orchestrator-setup)
- [Proxy server setup](#proxy-server-setup)
- [Managing organic access](#managing-organic-access)
- [Recommended compute](./recommended-compute)


# Overview

Validating on 19 is special.

Not only do you validate, check miners are behaving, set some weights and get some tao - you also get to sell your access to these miners 🤩


A Validator consists of two parts:

- Proxy API server
- Orchestrator server

The proxy server is the server which has your hotkey,  spins up the NODE, allows you to sell your bandwidth, etc. 

The Orchestrator performs the checking tasks, to make sure the miners are behaving 🫡

# Orchestrator setup

## Starting the Orchestrator server

Currently, a bare metal GPU is necessary for validating the GPU models. Please see here for the full instructions!(https://github.com/namoray/vision-workers/blob/main/validator_orchestrator/README.md)

Once this is done, make a note of the IP address of that machine, and the port the orchestrator is running on (the default is 6920, if you didn't change anything)


# Proxy server setup

Get a CPU VM (Digital Ocean Droplet, OVH, Vultr, etc)  - make sure you have an open port if you want to run a organic API server.

## Setup steps

Note: if you're using a provider such as vast, make sure you expose the necessary ports first, e.g.: https://docs.runpod.io/docs/expose-ports#:~:text=If%20your%20pod%20supports%20a,address%20to%20access%20your%20service. Follow the "Symmetrical port mapping" step :) 

**Note: Runpod CPU's don't seem to be the best**

### Clone the repo
```bash
git clone https://github.com/namoray/vision.git
cd vision
```

### Install system dependencies

If you are in a container, run these:

```bash
### Install pm2 & jq
apt update && apt upgrade -y
apt install nodejs npm -y
npm i -g pm2
apt-get install -y jq

### Install nano so you can edit the config easily
apt-get update
apt-get install nano
```
If you are on a bare metal machine (e.g. Vast) where you require `sudo`, use the following:
```bash
### Install pm2 & jq
sudo apt update && apt upgrade -y
sudo apt install nodejs npm -y
sudo npm i -g pm2
sudo apt-get install -y jq

### Install nano so you can edit the config easily
sudo apt-get update
sudo apt-get install nano
``` 

### Install python dependencies
Make sure you have installed the correct python version (python 3.10). If you don't, try this:

```bash
sudo apt update && sudo apt install -y software-properties-common && \
sudo add-apt-repository ppa:deadsnakes/ppa && sudo apt install -y python3.10 \
python3.10-venv && python3.10 -m venv venv && source venv/bin/activate && echo "source venv/bin/activate">>~/.bashrc
```

```bash
### Install the local python environment
pip install --upgrade pip
pip install -e .
```

If for some reason that doesn't work, you may need to use `pip3`;
```bash
### Install the local python environment
pip3 install --upgrade pip
pip3 install -e .
```


### Get hot and coldkeys onto your machine
I trust we can do this at this point ;D

### Create config!

Follow the below step
```bash
vision create-config
```

### Creating the database
Used to store scoring logs

Container:
```bash
curl -fsSL -o /usr/local/bin/dbmate https://github.com/amacneil/dbmate/releases/latest/download/dbmate-linux-amd64
chmod +x /usr/local/bin/dbmate

dbmate --url "sqlite:vision_database.db" up
```

VM / BM:
```bash
sudo curl -fsSL -o /usr/local/bin/dbmate https://github.com/amacneil/dbmate/releases/latest/download/dbmate-linux-amd64
sudo chmod +x /usr/local/bin/dbmate

dbmate --url "sqlite:vision_database.db" up
```




#### Starting the proxy server

### With autoupdates

**Autoupdates**

You're of course free to change or use whatever autoupdater you like!

```bash
pm2 start --name run_validator_auto_update "python run_validator_auto_update.py"
```

**IF that doesn't start the Miner pm2 process, try this instead**

```bash
nohup python run_validator_auto_update.py </dev/null &>miner_autoupdate.log &
```

### Without auto updates
```bash
./launch_validators.sh
```


# Managing organic access

**Note this is optional - only if you want to sell your bandwidth**

Using the vision-cli is the easiest way to manage access to your api server and sell access to anyone you like

```bash
vision --help
```

Shows all the commands and should give self-explanatory instructions.

You can also do

```bash
vision some-command --help
```

To get more info about that command!

### Some Examples

Create a key:

```bash
vision create-key 10 60 test
```
Creates a test key with a balance of 10 (which corresponds to 10 images), a rate limit of 60 requests per minute = 1/s, and a name 'test'.

**Recommend values:**
- Balance: Depends on how much you want to sell! Each credit is an image (so a balance of 1000 will allow 1000 images to be generated)
- Rate limit: I would recommend a rate limit of ~5/minute for casual users trying out the API, and around ~60/minute for production users
- Name: Just for you to remember who is using that key :)

Now you can do:
```bash
vision list-keys
```
To see the API key. Give / sell this access to whoever you want to have access to your API server to query the network organically - these requests will be scored too, miners must still behave!!

## Allowing people to access your server
For them to use your server, you will need to communicate:

- Your server address (IP_ADDRESS:PORT)
- Their API key
- Use server_address/redoc or server_address/docs for automatic documentation on how to use it!
