make all docker files share the core package so i dont need to rebuild this 8 times
tests
•⁠  ⁠high level in core validator which organises the stuff; axons added recently? if so then particiapnts added recently; Any synthetic queries left? All this stuff should give a lot of good insight
•⁠  ⁠⁠Plan today is turn off synthetics on mogs vali, and turn mine one for a bit

Make organic tasks work properly
setup all sorts to make it super easy to see what is happening, get alerts, etc
Probably refactor signing service slightly, probably refactor the core module to be super lightweight?
refactor everything
easy validator setup and running




What to change when making a new inference subnet?
- Synthetic generation Funcs
- Task config in core
- Mining code - but this needs binning anyway
- weight setting calculations

Thats it?



def set_axons_for_testing(config: Config) -> None:
    config.metagraph = MagicMock()
    config.metagraph.network = "test_network"
    config.metagraph.netuid = 1
    config.metagraph.axons = [
        AxonInfo(
            version=1,
            ip="127.0.0.1",
            port=1,
            ip_type=4,
            hotkey="test-vali",
            coldkey="test-vali-ck",
            axon_uid=0,
            incentive=0,
            netuid=config.metagraph.netuid,
            network=config.metagraph.network,
            stake=50.0,
        ),
        AxonInfo(
            version=1,
            ip="127.0.0.1",
            port=1,
            ip_type=4,
            hotkey="test-hotkey1",
            coldkey="test-coldkey1",
            axon_uid=1,
            incentive=0.004,
            netuid=config.metagraph.netuid,
            network=config.metagraph.network,
            stake=30.0,
        ),
        AxonInfo(
            version=2,
            ip="127.0.0.1",
            port=2,
            ip_type=4,
            hotkey="test-hotkey2",
            coldkey="test-coldkey2",
            axon_uid=2,
            incentive=0.005,
            netuid=config.metagraph.netuid,
            network=config.metagraph.network,
            stake=20.0,
        ),
    ]
    config.metagraph.total_stake = [50, 30, 20]
    config.sync = False