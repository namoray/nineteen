import argparse
import pathlib
import bittensor as bt


def check_config(config: "bt.Config") -> None:
    bt.axon.check_config(config)
    bt.logging.check_config(config)

    config.miner.full_path = (
        pathlib.Path(config.logging.logging_dir)
        .joinpath(config.wallet.get("name", bt.defaults.wallet.name))
        .joinpath(config.wallet.get("hotkey", bt.defaults.wallet.hotkey))
        .joinpath(config.miner.name)
        .expanduser()
        .absolute()
    )
    config.miner.full_path.mkdir(parents=True, exist_ok=True)


def get_miner_cli_config() -> "bt.Config":
    from config.miner_config import config as miner_config

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--axon.port",
        type=int,
        default=miner_config.axon_port,
        help="Port to run the axon on.",
    )

    parser.add_argument("--axon.external_ip", type=str, default=miner_config.axon_external_ip)

    parser.add_argument("--debug_miner", action="store_true", default=miner_config.debug_miner)

    parser.add_argument(
        "--subtensor.network",
        default=miner_config.subtensor_network,
        help="Bittensor network to connect to.",
    )

    parser.add_argument(
        "--subtensor.chain_endpoint",
        default=miner_config.subtensor_chainendpoint,
        help="Chain endpoint to connect to.",
    )

    parser.add_argument(
        "--netuid",
        type=int,
        default=19 if miner_config.subtensor_network != "test" else 176,
        help="The chain subnet uid.",
    )

    parser.add_argument("--wallet.name", type=str, default=miner_config.wallet_name)
    parser.add_argument("--wallet.hotkey", type=str, default=miner_config.hotkey_name)

    bt.subtensor.add_args(parser)
    bt.logging.add_args(parser)
    bt.wallet.add_args(parser)
    bt.axon.add_args(parser)

    config = bt.config(parser)

    config.full_path = (
        pathlib.Path(config.logging.logging_dir)
        .joinpath(config.wallet.name)
        .joinpath(config.wallet.hotkey)
        .joinpath("netuid{}".format(config.netuid))
        .joinpath("miner")
    )

    config.full_path.mkdir(parents=True, exist_ok=True)
    return config


def get_validator_cli_config() -> "bt.Config":
    from config.validator_config import config as validator_config

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--subtensor.network",
        default=validator_config.subtensor_network,
        help="Bittensor network to connect to.",
    )

    parser.add_argument(
        "--subtensor.chain_endpoint",
        default=validator_config.subtensor_chainendpoint,
        help="Chain endpoint to connect to.",
    )

    parser.add_argument(
        "--netuid",
        type=int,
        default=19 if validator_config.subtensor_network != "test" else 176,
        help="The chain subnet uid.",
    )

    parser.add_argument(
        "--wallet.name",
        type=str,
        default=validator_config.wallet_name,
    )
    parser.add_argument(
        "--wallet.hotkey",
        type=str,
        default=validator_config.hotkey_name,
    )

    bt.subtensor.add_args(parser)
    bt.logging.add_args(parser)
    bt.wallet.add_args(parser)
    bt.axon.add_args(parser)

    config = bt.config(parser)

    config.full_path = (
        pathlib.Path(config.logging.logging_dir)
        .joinpath(config.wallet.name)
        .joinpath(config.wallet.hotkey)
        .joinpath("netuid{}".format(config.netuid))
        .joinpath("validator")
    )

    config.full_path.mkdir(parents=True, exist_ok=True)
    return config

def prepare_validator_config_and_logging() -> bt.config:
    base_config = get_validator_cli_config()

    bt.logging(config=base_config, logging_dir=base_config.full_path)
    return base_config