# Full instructions for setup

Welcome to S19 Mining 🔥


## Contents:

- [Worker server setup](#worker-server-setup)
- [Proxy server setup](#proxy-server-setup)
- [LLM server configs](#model-configs)
- [Recommended compute](./recommended-compute)


# Overview
A miner consists of serveral parts, fitting into two categories:

- Proxy
- Workers

The proxy server is the server which has your hotkey, and spins up the NODE (should probably be on a CPU close to your GPU worker servers). The worker servers are the GPU workers which perform the tasks!

# Worker server setup
Documentation for all the workers is contained here https://github.com/namoray/vision-workers

# Proxy server setup

Get a CPU VM (Digital Ocean Droplet, OVH, Vultr, etc)  - make sure you have an open port if you want to run a organic API server.

## Setup environment


### Clone the repo
```bash
git clone https://github.com/namoray/vision.git
cd vision
```

### Install system dependencies
```bash
NO_LAUNCH=1 sudo -E ./bootstrap.sh
```

### Get hot and coldkeys onto your machine
If you use the btcli to regenerate the hotkey, you will need to install the bittensor package
```bash
pip install bittensor
```

Otherwise, securely move them onto your machine as usual


## Creating the database
Used to store concurrency info

```bash
sudo curl -fsSL -o /usr/local/bin/dbmate https://github.com/amacneil/dbmate/releases/latest/download/dbmate-linux-amd64
sudo chmod +x /usr/local/bin/dbmate

dbmate --url "sqlite:vision_database.db" up
```

## Create the config
```bash
vision create-config
```

If you get the error message `vision not found`, you should make sure that requirements are correctly installed


#### Configure the task_config & task_concurrency_config json's

For each hotkey, there was default task configuration created in the sqlite db.

View this with

```bash
./peer_at_sql_db.sh
```
For a GUI, or

```bash
sudo apt install sqlite3
sqlite3 vision_database.db
```
For no gui


The default values for volumes are 1/2 of the maximum allowed values. These are filled EITHER:

- When you use vision create-config
- run `python set_miner_defaults.py`

**Task config**

Here we defined the capacitity (or volume) for each task, for that miner. This is the maximum amount of 'work' that a hotkey can do in a 1 hour period. To calculate that work, you can use `calculate_volumes_example.py` tool.

**Concurrency groups**

We also define the `concurrency groups`. All the tasks belong to a concurrency group, and you can configure a maximum number of concurrent requests for that group, which is shared between all the tasks in that group

## Start miners

**Autoupdates**

Announcements will still be made ahead of time. If you choose to run autoupdates as a miner, make sure your ./start_miners.sh
script is up to date & working, and I would advise monitoring around update releases regardless.


You're of course free to change or use whatever autoupdater you like!

```bash
pm2 start --name run_miner_auto_update "python run_miner_auto_update.py"
```

**IF that doesn't start the Miner pm2 process, try this instead**

```bash
nohup python run_miner_auto_update.py </dev/null &>miner_autoupdate.log &
```

**No autoupdates**

You can either use the command
```bash
./start_miners.sh
```
