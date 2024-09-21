# Features to be included in the Vision 5.0 release:

- Make sure reward data and contender history is capped
- Post to sn19.ai + with the created_at time pointing to the time of the query, not time of insertion
- Speed scoring to be based off medians - and potentially using the distribution of miners instead of a fixed distribution
- Add in DUIS
- Redis password
- Redis commander password
- Consolidate docker compose files (that might help with the above)
- api keys for entry node
- Change text synthetics to pull from a larger text orientated dataset
- Change autoupdate to use pm2

## Fiber stuff:
- Header for nonce & encrypted nonce? or sign nonce with private key?
- Fix the ssl errors from substrate interface which have onyl just started appearing :(

## Workers stuff:
- image server upgrades

## testS:
- get em working son

## Shortly after Vision 5.0 release
- Specialist miners. Miners will be in 3 categories for launch: Small LLM's, Medium LLM's, Image generation - and can only run one type of miner on a uid