from dotenv import load_dotenv

from validator.db.src.sql.api import add_api_key, delete_api_key, update_api_key_balance, update_api_key_name, update_api_key_rate_limit_per_minute

load_dotenv(".vali.env")
import asyncclick as click
from rich.console import Console
from rich.table import Table
from validator.control_node.src.control_config import load_config
import uuid
from validator.utils.database import database_constants as dcst

config = load_config()


@click.group()
def cli():
    """A simple CLI tool with multiple commands."""
    pass


@cli.command()
@click.option("--count", default=1, help="Number of greetings.")
@click.option(
    "--rate-limit-per-minute", prompt="Rate limit per minute", help="The rate limit per minute for the API key.", default=100
)
@click.option("--name", prompt="Name of the key for identification", help="The name for the API key.", default="No-Name")
async def create_key(count, rate_limit_per_minute, name):
    """Simple program that greets NAME for a total of COUNT times."""
    await config.psql_db.connect()
    balance = 100000000
    print("For now, the balance is set to 100,000,000 [will be improved soon]")


    api_key = str(uuid.uuid4())
    print(api_key, balance, rate_limit_per_minute, name)
    async with await config.psql_db.connection() as connection:
        await add_api_key(connection, api_key, balance, rate_limit_per_minute, name)

    console = Console()
    table = Table(show_header=True, header_style="bold magenta")

    table.add_column(dcst.KEY)
    table.add_column(dcst.BALANCE)
    table.add_column(dcst.RATE_LIMIT_PER_MINUTE)
    table.add_column(dcst.NAME)

    row = (api_key, balance, rate_limit_per_minute, name)
    table.add_row(*map(str, row))

    console.print(table)

@cli.command()
@click.option("--api-key", prompt="API Key", help="The API key to update.", required=True)
@click.option("--balance", prompt="Balance", help="The balance to update.", default=-1, type=int)
@click.option("--rate-limit-per-minute", prompt="Rate limit per minute", help="The rate limit per minute to update.", default=-1, type=int)
@click.option("--name", prompt="Name", help="The name to update.", default="")
async def update_key(api_key, balance, rate_limit_per_minute, name):
    await config.psql_db.connect()
    async with await config.psql_db.connection() as connection:
        if balance >= 0:
            await update_api_key_balance(connection, api_key, balance)
        if rate_limit_per_minute >= 0:
            await update_api_key_rate_limit_per_minute(connection, api_key, rate_limit_per_minute)
        if name:
            await update_api_key_name(connection, api_key, name)

@cli.command()
@click.option("--api-key", prompt="API Key", help="The API key to delete.", required=True)
async def delete_key(api_key):
    await config.psql_db.connect()
    async with await config.psql_db.connection() as connection:
        await delete_api_key(connection, api_key)

if __name__ == "__main__":
    cli(_anyio_backend="asyncio")
