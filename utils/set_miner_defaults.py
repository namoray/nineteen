import glob
import os
from mining.db.db_management import miner_db_manager


def main():
    env_files = glob.glob(".*.env")

    for env_file in env_files:
        with open(env_file, "r") as file:
            content = file.read()

        if "IS_VALIDATOR=True" not in content:
            hotkey = os.path.basename(env_file).replace(".env", "")[1:]
            miner_db_manager.insert_default_task_configs(hotkey)


if __name__ == "__main__":
    main()
