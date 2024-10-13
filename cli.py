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


# Asyncclick is used for creating async CLI commands
@click.group()
def cli():
    """CLI to manage API keys, logs, and schedule tasks via control_node."""
    pass


@cli.command("schedule-task")
@click.option(
    "--task",
    required=True,
    type=click.Choice(["chat", "text-to-image"], case_sensitive=False),
    help="Task type (e.g., 'chat', 'text-to-image').",
)
@click.option("--model", default="default-model", help="Specify the model to use for this synthetic task.")
@click.option("--volume", default=1, help="The volume of tasks to create.")
async def schedule_task(task, model, volume):
    """Schedule a synthetic task to the task queue (e.g., Redis)."""

    if task == "chat":
        generator_function = generate_chat_synthetic
    elif task == "text-to-image":
        generator_function = generate_text_to_image_synthetic
    else:
        raise ValueError(f"Unknown task type '{task}'")

    async with redis_db as connection:
        console = Console()

        # Generate and push the synthetic tasks to the task scheduler for each volume requested
        for i in range(volume):
            synthetic_data = await generator_function(model=model)
            task_data = {
                "id": str(uuid.uuid4()),  # Unique task id
                "task_type": task,  # Type is either 'chat' or 'text-to-image'
                "task_generated_at": time(),
                "model": model,  # Model you want to use for this task
                "payload": synthetic_data.model_dump(),  # The actual payload is in your model (based on the synthetic function)
            }

            # Push this task to Redis (into the predefined task queue)
            await connection.rpush(rcst.QUERY_QUEUE_KEY, json.dumps(task_data))
            console.print(
                f"[bold green]Task {task_data['id']} has been successfully scheduled for task type '{task}'![/bold green]"
            )

        console.print(f"[bold cyan]Total {volume} task(s) scheduled![/bold cyan]")


@cli.command()
async def list_queued_tasks():
    """List all queued synthetic tasks in Redis."""
    console = Console()
    async with redis_db as connection:
        tasks = await connection.lrange(rcst.wi, 0, -1)

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Task ID", style="yellow", no_wrap=True)
    table.add_column("Task Type")
    table.add_column("Generated At")
    table.add_column("Model")

    for task_raw_data in tasks:
        task_data = json.loads(task_raw_data)
        task_id = task_data.get("id")
        task_type = task_data.get("task_type")
        task_time = task_data.get("task_generated_at")
        model = task_data.get("model")

        # Add the task to the output table
        table.add_row(task_id, task_type, str(task_time), model)

    console.print(table)


@cli.command()
async def clear_queued_tasks():
    """Clear all queued synthetic tasks in Redis."""
    async with redis_db as connection:
        await connection.delete(rcst.QUERY_QUEUE_KEY)

    console = Console()
    console.print("[bold red]All tasks cleared from the queue![/bold red]")


if __name__ == "__main__":
    cli(_anyio_backend="asyncio")
