import secrets
import string
import re
import argparse
from typing import  Callable, Any


def generate_secure_password(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits + string.punctuation
    return "".join(secrets.choice(alphabet) for _ in range(length))


def validate_input(prompt: str, validator: Callable[[str], bool]) -> str:
    while True:
        value = input(prompt)
        if validator(value):
            return value
        print("Invalid input. Please try again.")


def yes_no_validator(value: str) -> bool:
    return value.lower() in ["y", "n", "yes", "no"]


def non_empty_validator(value: str) -> bool:
    return bool(value.strip())


def number_validator(value: str) -> bool:
    return value.isdigit()


def float_validator(value: str) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate configuration file")
    parser.add_argument("--dev", action="store_true", help="Use development configuration")
    return parser.parse_args()


def generate_config(dev: bool = False) -> dict[str, Any]:
    config: dict[str, Any] = {}

    # Auto-generate database credentials
    config["POSTGRES_USER"] = "user"
    config["POSTGRES_PASSWORD"] = generate_secure_password()
    config["POSTGRES_DB"] = "19_db"
    config["POSTGRES_PORT"] = "5432"
    config["POSTGRES_HOST"] = "postgresql"

    # User inputs
    config["NETUID"] = validate_input("Enter NETUID: ", number_validator)
    config["WALLET_NAME"] = validate_input("Enter wallet name: ", non_empty_validator)
    config["HOTKEY_NAME"] = validate_input("Enter hotkey name: ", non_empty_validator)
    config["SUBTENSOR_NETWORK"] = validate_input("Enter subtensor network: ", non_empty_validator)
    config["GPU_SERVER_ADDRESS"] = validate_input(
        "Enter GPU server address: ", lambda x: re.match(r"^https?://.+", x) is not None
    )

    if dev:
        config["ENV"] = "dev"
        config["REFRESH_NODES"] = (
            "true" if validate_input("Refresh nodes? (y/n): ", yes_no_validator).lower().startswith("y") else "false"
        )
        config["CAPACITY_TO_SCORE_MULTIPLIER"] = float(validate_input("Enter capacity to score multiplier: ", float_validator))
        config["LOCALHOST"] = (
            "true" if validate_input("Use localhost? (y/n): ", yes_no_validator).lower().startswith("y") else "false"
        )
        config["REPLACE_WITH_DOCKER_LOCALHOST"] = (
            "true"
            if validate_input("Replace with Docker localhost? (y/n): ", yes_no_validator).lower().startswith("y")
            else "false"
        )
    else:
        config["ENV"] = "prod"
        config["REFRESH_NODES"] = "true"
        config["CAPACITY_TO_SCORE_MULTIPLIER"] = 1
        config["LOCALHOST"] = "false"
        config["REPLACE_WITH_DOCKER_LOCALHOST"] = "true"

    return config


def write_config_to_file(config: dict[str, Any], env: str) -> None:
    filename = f".{env}.env"
    with open(filename, "w") as f:
        for key, value in config.items():
            f.write(f"{key}={value}\n")


if __name__ == "__main__":
    args = parse_args()
    print("Welcome to the configuration generator!")
    env = "dev" if args.dev else "prod"
    config = generate_config(dev=args.dev)
    write_config_to_file(config, env)
    print(f"Configuration has been written to .{env}.env")
    print("Please make sure to keep your database credentials secure.")
