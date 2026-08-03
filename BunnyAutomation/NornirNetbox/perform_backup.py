'''This script currently goes through netbox, filter out devices based on unique "tags/tag" objects and then back up the running-config of those devices to a local dir'''

'''
Features in work:
 1.) Save to Netbox
 2.) Pipeline to save to a GitRepo
 3.) Filter based on multiple set parameters
 4.) Back up based on Hostname -> Date -> Config/Interface stats?/Health-Status
'''

import os
from datetime import datetime
from pathlib import Path
from typing import Any

from nornir import InitNornir
from nornir.core.filter import F
from nornir.core.task import Result, Task
from nornir_netmiko.tasks import netmiko_send_command
from nornir_utils.plugins.functions import print_result
from nornir.core.inventory import ConnectionOptions



TARGET_TAG = "nornirtest"  #Tag used on Objects within Netbox.
BACKUP_ROOT = Path("./config_backups")  #Dir path for configuration backups


def main() -> None:

    username = os.getenv("NORNIR_USERNAME") #exports your #USERNAME for logging into Network devices
    password = os.getenv("NORNIR_PASSWORD") #exports your #PASSWORD for logging into Network devices

   #Checks to confirm if VARs are present/set
    if not username or not password: 
        print(
            "ERROR: NORNIR_USERNAME and NORNIR_PASSWORD "
            "must be set in the environment."
        )
        return 1

    #Intializes Nornir
    try:
        nr = InitNornir(config_file="config.yaml") 
    except Exception as exc:
        print(f"ERROR: Could not initialize Nornir/NetBox inventory: {exc}")
        return 1
    
    nr.inventory.defaults.username = username #Set's username as default vaule for logging across all devices
    nr.inventory.defaults.password = password #Set's password as default value for logigng across all devices

    print("\n--- Inventory loaded from NetBox ---")
    print(f"Total devices: {len(nr.inventory.hosts)}")

    #Check's to confirm it can reach Netbox's Inventory
    if not nr.inventory.hosts: 
        print(
            "No devices were loaded. Check the NetBox inventory plugin, "
            "API URL, token, permissions, and inventory configuration."
        )
        return

    # Inspects the tags then proceeds to pass them to the "normalize_tags" task/function.
    for host in nr.inventory.hosts.values():
        raw_tags = host.data.get("tags", [])
        normalized_tags = normalize_tags(raw_tags)

        host.data["tag_slugs"] = normalized_tags

        print(
            f"{host.name}: "
            f"hostname={host.hostname!r}, "
            f"platform={host.platform!r}, "
            f"raw_tags={raw_tags!r}, "
            f"normalized_tags={normalized_tags!r}"
        )

        #Connection options - Configured currently for connecting to legacy SSH/slower devices.
        #Applied to all the objects that are pulled above from nr.inventory.hosts
        host.connection_options["netmiko"] = ConnectionOptions(extras= {"conn_timeout": 30,
                                                                        "banner_timeout": 60,
                                                                        "auth_timeout": 60,
                                                                        "fast_cli": False})

    #Performs a filter against Netbox's Inventory; using the TARGET_TAG to filter devices based on 'tags'
    targets = nr.filter(
        F(tag_slugs__contains=TARGET_TAG.casefold())
    )

    print("\n--- Filter results ---")
    print(f"Target tag: {TARGET_TAG!r}")
    print(f"Matched devices: {len(targets.inventory.hosts)}")
    print(f"Device names: {list(targets.inventory.hosts)}")

    #Provides error output for if no devices are assigned to the specified parameter(Tag)
    if not targets.inventory.hosts:
        print(
            "\nNo devices matched the tag. Review the raw_tags and "
            "normalized_tags shown above."
        )
        return

    # Build the dated backup directory once for the entire backup run.
    # Result: /networkbackups/<year>/<month>/<day>/
    backup_date = datetime.now()

    dated_output_dir = (
        BACKUP_ROOT
        / backup_date.strftime("%Y")
        / backup_date.strftime("%m")
        / backup_date.strftime("%d")
    )

    dated_output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(f"\nOutput directory: {dated_output_dir.resolve()}")
    print("\n--- Starting configuration backups ---")

    # Collect the running configuration and environment output
    # from each device filtered from NetBox.
    results = targets.run(
        name="Back up Cisco running configurations and environment",
        task=save_device_outputs,
        output_dir=dated_output_dir,
        )

    # This is essential while troubleshooting.
    print_result(results)

    print("\n--- Backup summary ---")

    for host_name in targets.inventory.hosts:
        if host_name in results.failed_hosts:
          print(f"[FAILED] {host_name}")
        else:
            config_file = (
                dated_output_dir
                / host_name
                / f"{host_name}.cfg")

            environment_file = (
                dated_output_dir
                / host_name
                / f"{host_name}_environment.txt")

            print(f"[SAVED] {host_name}")
            print(f"        Config:      {config_file.resolve()}")
            print(f"        Environment: {environment_file.resolve()}")


def normalize_tags(tags: list[Any]) -> list[str]:
    
    #Converts NetBox tags into lowercase names/slugs.
    #Can handle:
    #  - strings
    #  - dictionaries
    #  - NetBox/tag objects
    
    normalized: list[str] = []

    for tag in tags:
        if isinstance(tag, str):
            values = [tag]

        elif isinstance(tag, dict):
            values = [
                tag.get("slug"),
                tag.get("name"),
            ]

        else:
            values = [
                getattr(tag, "slug", None),
                getattr(tag, "name", None),
            ]

        for value in values:
            if value:
                normalized.append(str(value).casefold())

    return list(set(normalized))

def save_device_outputs(task: Task, output_dir: Path) -> Result:
    """
    Retrieve and save the running configuration and environment
    information for a single network device.
    """

    print(
        f"[{task.host.name}] Connecting to "
        f"{task.host.hostname} using platform {task.host.platform!r}"
    )

    # Retrieve the running configuration.
    running_config_results = task.run(
        name="Get running configuration",
        task=netmiko_send_command,
        command_string="show running-config",
        read_timeout=120,
    )

    running_config_result = running_config_results[-1]

    if running_config_result.failed:
        return Result(
            host=task.host,
            failed=True,
            result=(
                "Failed to retrieve running configuration: "
                f"{running_config_result.exception or running_config_result.result}"
            ),
        )

    running_config = str(running_config_result.result)

    if not running_config.strip():
        return Result(
            host=task.host,
            failed=True,
            result="The device returned an empty running configuration.",
        )

    # Retrieve the environment information.
    environment_results = task.run(
        name="Get environment information",
        task=netmiko_send_command,
        command_string="show environment all",
        read_timeout=120,
    )

    environment_result = environment_results[-1]

    if environment_result.failed:
        return Result(
            host=task.host,
            failed=True,
            result=(
                "Failed to retrieve environment information: "
                f"{environment_result.exception or environment_result.result}"
            ),
        )

    environment_output = str(environment_result.result)

    if not environment_output.strip():
        return Result(
            host=task.host,
            failed=True,
            result="The device returned empty environment information.",
        )

    # Create the hostname-specific backup directory.
    host_backup_dir = output_dir / task.host.name

    config_filename = (
        host_backup_dir
        / f"{task.host.name}.cfg"
    )

    environment_filename = (
        host_backup_dir
        / f"{task.host.name}_environment.txt"
    )

    try:
        host_backup_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        config_filename.write_text(
            running_config.rstrip() + "\n",
            encoding="utf-8",
        )

        environment_filename.write_text(
            environment_output.rstrip() + "\n",
            encoding="utf-8",
        )

    except OSError as exc:
        return Result(
            host=task.host,
            failed=True,
            exception=exc,
            result=(
                f"Could not write backup files for "
                f"{task.host.name}: {exc}"
            ),
        )

    return Result(
        host=task.host,
        changed=False,
        result=(
            f"Saved running configuration to "
            f"{config_filename.resolve()}\n"
            f"Saved environment information to "
            f"{environment_filename.resolve()}"
        ),
    )

if __name__ == "__main__":
    main()