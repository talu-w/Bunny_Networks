'''This script currently goes through netbox, filter out devices based on unique "tags/tag" objects and then back up the running-config of those devices to a local dir'''

'''
Features in work:
 1.) Save to Netbox
 2.) Pipeline to save to a GitRepo
 3.) Filter based on multiple set parameters
 4.) Back up based on Hostname -> Date -> Config/Interface stats?/Health-Status
'''

import os
from pathlib import Path
from typing import Any

from nornir import InitNornir
from nornir.core.filter import F
from nornir.core.task import Result, Task
from nornir_netmiko.tasks import netmiko_send_command
from nornir_utils.plugins.functions import print_result
from nornir.core.inventory import ConnectionOptions



TARGET_TAG = "nornirtest"  #Tag used on Objects within Netbox.
OUTPUT_DIR = Path("./config_backups") #Save's configs to specified DIR


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
                #This allows connections to legacy SSH-Devices as they take longer to respond.
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

    #Create's the Directory
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(f"\nOutput directory: {OUTPUT_DIR.resolve()}")
    print("\n--- Starting configuration backups ---")

    #Call's upon the save_running_config Function to collect the running-config from the deivces filtered from Netbox
    results = targets.run(
        name="Back up Cisco running configurations",
        task=save_running_config,
        output_dir=OUTPUT_DIR,
    )

    # This is essential while troubleshooting.
    print_result(results)

    print("\n--- Backup summary ---")

    for host_name in targets.inventory.hosts:
        if host_name in results.failed_hosts:
            print(f"[FAILED] {host_name}")
        else:
            expected_file = OUTPUT_DIR / f"{host_name}.txt"
            print(f"[SAVED]  {host_name}: {expected_file.resolve()}")

    if results.failed_hosts:
        print(
            "\nFailed devices:",
            ", ".join(results.failed_hosts),
        )

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


def save_running_config(task: Task, output_dir: Path) -> Result:
    #Retrieve and save Network devices running configuration
    print(
        f"[{task.host.name}] Connecting to "
        f"{task.host.hostname} using platform {task.host.platform!r}"
    )

    #Use's Netmiko-Sub-Module to connect to device
    command_results = task.run(
        name="Get running configuration",
        task=netmiko_send_command,
        command_string="show running-config",
        read_timeout=120,
    )

    #task.run() returns a MultiResult. The Netmiko subtask is its last result.
    command_result = command_results[-1]

    #Failed to retrieve config
    if command_result.failed:
        return Result(
            host=task.host,
            failed=True,
            result=(
                f"Failed to retrieve running configuration: "
                f"{command_result.exception or command_result.result}"
            ),
        )

    configuration = str(command_result.result)
    #If the device provides an empty config or was unable to write for whatever reason.
    if not configuration.strip():
        return Result(
            host=task.host,
            failed=True,
            result="The device returned an empty running configuration or was unable to write. Check to make sure the proper command was passed.",
        )

    filename = output_dir / f"{task.host.name}.txt"
    #Writes the config to a VAR
    try:
        filename.write_text(
            configuration.rstrip() + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        return Result(
            host=task.host,
            failed=True,
            exception=exc,
            result=f"Could not write {filename}: {exc}",
        )
    #Returns that VAR as a value 
    return Result(
        host=task.host,
        changed=False,
        result=f"Saved running configuration to {filename.resolve()}",
    )


if __name__ == "__main__":
    main()