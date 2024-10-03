from dotenv import load_dotenv

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
@click.option("--name", prompt="Name of the key for identification", help="The name for the API key.")
async def create_key(count, rate_limit_per_minute, name):
    """Simple program that greets NAME for a total of COUNT times."""
    await config.psql_db.connect()
    balance = 100000000
    print("For now, the balance is set to 100,000,000 [will be improved soon]")

    api_key = str(uuid.uuid4())
    async with await config.psql_db.connection() as connection:
        await connection.execute(
            "INSERT INTO api_keys (api_key, balance, rate_limit_per_minute, name) VALUES (?, ?, ?, ?)",
            (api_key, balance, rate_limit_per_minute, name)
        )

    console = Console()
    table = Table(show_header=True, header_style="bold magenta")

    table.add_column(dcst.KEY)
    table.add_column(dcst.BALANCE)
    table.add_column(dcst.RATE_LIMIT_PER_MINUTE)
    table.add_column(dcst.NAME)

    row = (api_key, balance, rate_limit_per_minute, name)
    table.add_row(*map(str, row))

    console.print(table)


if __name__ == "__main__":
    cli(_anyio_backend="asyncio")
