# Vision 4.0 Proposal

## Last updated: (June 10th 2024)
Proposal for the introduction of Capacities for Subnet 19 - Vision 4.0

## Overview:
On Subnet 19, miners are incentivized to do lots of different tasks. Currently, requests are evenly distributed amongst miners, by picking a miner at random when making a request. This leaves room for improvement, as it encourages a flat and even distribution.

There are a couple of ways to tackle this problem, to better reward 1 UID per miner.

### Approach 1 - Capacities:
We could allow miners to define their maximum capacities for each task. Capacities are things like Tokens (LLMS), or Steps (Images) - proportional to GPU seconds.

We define weights for each task, which sum up to 1. A miner's score can be calculated by summing all their calculated scores for each task, multiplied by the ‘weight’ of that task.

Pros:
- Miners get rewards proportional to the extent of their setup, with the ‘max volumes’ defined as their only limitation -> a move to 1 uid per miner
- Synthetic and Organic validators all can agree on what a miner is capable of 
- Tasks are truly optional for a miner, as their score is a linear combination of all of their scores for different tasks.
- Miners can optimize their setups for predictable traffic
- Miners can directly allocate bandwidth according to the game theory optimum demonstrated in [DSIS](https://corcel.io/whitepapers/decentralised-subnet-inference-at-scale)
- Organic queries can directly reduce the amount of synthetics needed
- We can check the full capacity a smaller % of the time synthetically, allowing higher bandwidth for the validators that have higher demand


Cons:
- Validators have fixed bandwidth for each task, that they cannot organically exceed
- Volumes can in theory go unlimited, but in practice, validator hardware might limit this

### Approach 2 - ‘Availabilities’

We keep the same concept of task weightings, but instead of communicating capacities, we allow miners to communicate when they are ‘available’ to accept another request, for a specific task. 

Pros:
- Miners can get directly rewarded for every query they perform, and are free to choose that number
- Validators can always pick a uid that is available for organic requests
- Miners can optimize their setups for predictable traffic
- Miners can directly allocate bandwidth according to the game theory optimum demonstrated in [DSIS](https://corcel.io/whitepapers/decentralised-subnet-inference-at-scale)
- Validators could check in bursts, and instead give rewards for concurrencies, to minimise unnecessary checks


Cons:
- Synthetic and organic validators’ vtrust would potentially get out of sync if organic traffic was significantly higher than the synthetic traffic (/bursts)

Overall, I propose we should opt for option 1, as this protects all validators of vtrust over the foreseeable future. Miners have more freedom of rewards, and will give us more control to move to a distribution that more proportionally rewards ‘work’. Miners will still not be limited to one task and can run as much as they like.


### Further changes:
- Removal of Go journey API - we want to be the leading subnet on bittensor for decentralisation. Whilst we have used the dataset to train a new model to fit midjourney, we no longer need more data, and so we should be as decentralised as possible.
- Removal of subnet 6's finetune model - for obvious reasons

## Timeline:
Code release: 5th Jun 2024

PR - initial PR 5th Jun 2024 - Final PR 12th Jun 2024

Proposed delivery: 13th June 1 PM UTC

## Inspirations:
- SN8: Official Proposal documentation
- SN17: Miners asking for tasks when they are free
- SN19: Vision 3.0 code :D
- SN21: Reward tiers (Not used yet, but a potential addition for Vision 4.1)
- SN23: Declared volumes of requests for one task

**With a special thanks to ban44ntje, Tenet, Sirouk, amongst other awesome SN19 miners, for their continued input**



