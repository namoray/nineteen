import argparse
import asyncio
from fiber.chain import chain_utils
from fiber.validator import handshake
import httpx
from fiber.logging_utils import get_logger

logger = get_logger(__name__)

async def main(wallet_name: str, hotkey_name: str, server_address: str = None, miner_uid: int = None):
    keypair = chain_utils.load_hotkey_keypair(wallet_name, hotkey_name)
    httpx_client = httpx.AsyncClient()
    logger.debug(f"Performing handshake with server at {server_address}")
    await handshake.perform_handshake(keypair=keypair, httpx_client=httpx_client, server_address=server_address)
    logger.debug("Handshake complete")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Miner configuration")
    parser.add_argument("--wallet.name", type=str, help="Name of the wallet", required=True)
    parser.add_argument("--wallet.hotkey", type=str, help="Name of the hotkey", required=True)
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument("--miner-uid", type=int, help="UID of the miner")
    parser.add_argument("--server-address", type=str, help="Address of the server")

    args = parser.parse_args()

    wallet_name = getattr(args, 'wallet.name')
    hotkey_name = getattr(args, 'wallet.hotkey')
    miner_uid = args.miner_uid
    server_address = args.server_address

    asyncio.run(main(wallet_name, hotkey_name, server_address, miner_uid))
