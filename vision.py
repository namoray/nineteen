import uuid

import aiosqlite
import anyio
import typer
from typing import Optional
from rich.console import Console
from rich.table import Table
from generic.create_config import get_config
from validator.db import sql

cli = typer.Typer(name="Vision CLI")


@cli.command()
def create_config():
    """
    Generates the config file.
    """
    get_config()


@cli.command()
def create_key(
    balance: Optional[float] = None,
    rate_limit_per_minute: Optional[int] = None,
    name: Optional[str] = None,
):
    """
    Create a new API key.

    This command creates a new API key with the given balance, rate limit per minute, and name.

    Arguments:
    balance: The initial balance of the API key.
    rate_limit_per_minute: The rate limit in requests per minute for the API key.
    name: The name for the API key.
    """

    async def run(balance: Optional[float], rate_limit_per_minute: Optional[int], name: Optional[str]):
        if balance is None:
            balance = float(input("Please enter initial balance for the key (1 credit = 1 image): "))

        if rate_limit_per_minute is None:
            rate_limit_per_minute = int(input("Please enter rate limit per minute: "))

        if name is None:
            name = input("Please enter a name for the API key: ")

        api_key = str(uuid.uuid4())
        async with aiosqlite.connect(sql.DATABASE_PATH) as conn:
            await sql.add_api_key(conn, api_key, balance, rate_limit_per_minute, name)

        console = Console()
        table = Table(show_header=True, header_style="bold magenta")

        table.add_column(sql.KEY)
        table.add_column(sql.BALANCE)
        table.add_column(sql.RATE_LIMIT_PER_MINUTE)
        table.add_column(sql.NAME)

        row = (api_key, balance, rate_limit_per_minute, name)
        table.add_row(*map(str, row))

        console.print(table)

    api_key = anyio.run(run, balance, rate_limit_per_minute, name)
    return api_key


@cli.command()
def update_key(key: str, balance: float, rate_limit_per_minute: int, name: str):
    """
    Update an existing API Key.

    This command updates an existing API key identified by the 'key' with the given balance, rate limit per minute, and name.

    Arguments:
    key: The API key to update.
    balance (optional): The new balance of the API key.
    rate_limit_per_minute (optional): The new rate limit in requests per minute for the API key.
    name (optional): The new name for the API key.
    """

    async def run():
        async with aiosqlite.connect(sql.DATABASE_PATH) as conn:
            if balance is not None:
                await sql.update_api_key_balance(conn, key, balance)
            if rate_limit_per_minute is not None:
                await sql.update_api_key_rate_limit(conn, key, rate_limit_per_minute)
            if name is not None:
                await sql.update_api_key_name(conn, key, name)

    anyio.run(run)


@cli.command()
def delete_key(key: str):
    """
    Delete an existing API Key.

    This command deletes an existing API key identified by the 'key'.

    Arguments:
        key: The API key to delete.
    """

    async def run():
        async with aiosqlite.connect(sql.DATABASE_PATH) as conn:
            await sql.delete_api_key(conn, key)

    anyio.run(run)


@cli.command()
def list_keys():
    """
    List all API keys.
    """

    async def run():
        async with aiosqlite.connect(sql.DATABASE_PATH) as conn:
            rows = await sql.get_all_api_keys(conn)
        console = Console()

        table = Table(show_header=True, header_style="bold magenta")
        try:
            _ = rows[0].keys()
        except IndexError:
            console.print("No keys table found - try adding a key")
            return

        columns_need_adding = True

        for row in rows:
            if row:
                if columns_need_adding:
                    for column_name in row.keys():
                        table.add_column(column_name)

                    columns_need_adding = False

                table.add_row(*[str(value) for value in row.values()])

        console.print(table)

    anyio.run(run)


@cli.command()
def show_key_info(key: str):
    """
    Show information about an API key.
    """

    async def run():
        async with aiosqlite.connect(sql.DATABASE_PATH) as conn:
            row = sql.get_api_key_info(conn, key)

        console = Console()
        table = Table(show_header=True, header_style="bold magenta")

        if row:
            for column_name in row.keys():
                table.add_column(column_name)

            table.add_row(*[str(value) for value in row.values()])
            console.print(table)

    anyio.run(run)


@cli.command()
def logs_for_key(key: str):
    """
    Show all logs for an API key.
    """

    async def run():
        console = Console()
        table = Table(show_header=True, header_style="bold magenta")

        async with aiosqlite.connect(sql.DATABASE_PATH) as conn:
            logs = await sql.get_all_logs_for_key(conn, key)

        if logs:
            for column_name in logs[0].keys():
                table.add_column(column_name)

            for log in logs:
                log = dict(log)
                table.add_row(*[str(value) for value in log.values()])

            console.print(table)
        else:
            print(f"No logs found for key: {key}")

    anyio.run(run)


@cli.command()
def logs_summary():
    """
    Summary of all logs.
    """

    async def run():
        async with aiosqlite.connect(sql.DATABASE_PATH) as conn:
            keys = await sql.get_all_api_keys(conn)

        console = Console()

        summary_table = Table(show_header=True, header_style="bold magenta")
        summary_table.add_column("key")
        summary_table.add_column("Total Requests")
        summary_table.add_column("Total Credits Used")

        global_endpoint_dict = {}

        for key in keys:
            key = dict(key)[sql.KEY]
            async with aiosqlite.connect(sql.DATABASE_PATH) as conn:
                logs = await sql.get_all_logs_for_key(conn, key)

            total_requests = len(logs)
            total_credits_used = sum([dict(log).get("cost", 0) for log in logs])

            for log in logs:
                log = dict(log)
                endpoint = log.get(sql.ENDPOINT, "unknown_endpoint")
                global_endpoint_dict[endpoint] = global_endpoint_dict.get(endpoint, 0) + 1

            summary_table.add_row(key, str(total_requests), str(total_credits_used))

        console.print(summary_table)

        breakdown_table = Table(show_header=True, header_style="bold green")
        breakdown_table.add_column("Endpoint")
        breakdown_table.add_column("Count")

        for endpoint, count in global_endpoint_dict.items():
            breakdown_table.add_row(endpoint, str(count))

        console.print("Endpoint Breakdown:")
        console.print(breakdown_table)

    anyio.run(run)


if __name__ == "__main__":
    cli()
