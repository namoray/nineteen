import json
import asyncio
import uuid
from validator.utils.redis import redis_constants as rcst
from validator.control_node.src.synthetics.synthetic_generation_funcs import (
    generate_chat_synthetic,
    generate_text_to_image_synthetic,
)
from redis.asyncio import Redis  # Redis instance
import asyncclick as click
from time import time
from rich.console import Console
from rich.table import Table

# Importing the config from control_node, including Redis and PSQL instances.
from validator.control_node.src.control_config import load_config

config = load_config()

# Initialize Redis client and connect via environment vars
redis_db = Redis(host="localhost", port=6379)


@click.group()
def cli():
    """CLI to manage API keys, logs, and schedule tasks via control_node."""
    pass


@cli.command("schedule-task")
@click.option(
    "--task",
    required=True,
    type=click.Choice(["chat", "text-to-image"], case_sensitive=False),
    help="The type of task to schedule (e.g., chat, text-to-image).",
)
@click.option("--model", default="default-model", help="Specify the model for the synthetic task.")
@click.option("--volume", default=1, help="Number of tasks to create.")
async def schedule_task(task, model, volume):
    """Schedule a synthetic task for future processing through the control node."""
    async with redis_db as connection:
        console = Console()

        for _ in range(volume):
            task_data = {
                "id": str(uuid.uuid4()),  # Every task needs a unique identifier
                "task_type": task,  # The specified task type (chat, etc.)
                "task_generated_at": time(),
                "model": model,  # Passed as parameter
                "status": "pending",  # Default status for the new task
            }

            # Push this task to the CONTROL_NODE_QUEUE handled by the control node.
            await connection.rpush(rcst.CONTROL_NODE_QUEUE_KEY, json.dumps(task_data))

            console.print(f"[bold green]Task {task_data['id']} has been successfully scheduled![/bold green]")

        console.print(f"[bold cyan]Total {volume} task(s) scheduled![/bold cyan]")


if __name__ == "__main__":
    cli(_anyio_backend="asyncio")
