'''This script currently goes through netbox, filter out devices based on unique "tags/tag" objects and then back up the running-config of those devices to a local dir'''

'''
Features in work:
 1.) Save to Netbox
 2.) Pipeline to save to a GitRepo
 3.) Filter based on multiple set parameters
 4.) Back up based on Hostname -> Date -> Config/Interface stats?/Health-Status
'''

import os
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from nornir import InitNornir
from nornir.core.filter import F
from nornir.core.task import Result, Task
from nornir_netmiko.tasks import netmiko_send_command
from nornir_utils.plugins.functions import print_result
from nornir.core.inventory import ConnectionOptions
try:
    from rich.console import Console
    from rich.markup import escape
    from rich.progress import (
        BarColumn,
        Progress,
        SpinnerColumn,
        TaskID,
        TextColumn,
        TimeElapsedColumn,
    )
except ImportError as exc:
    raise SystemExit(
        "ERROR: This script requires Rich. Install it with: pip install rich"
    ) from exc



TARGET_TAG = "nornirtest"  #Tag used on Objects within Netbox.
BACKUP_ROOT = Path("./config_backups")  #Dir path for configuration backups
PROGRESS_STEPS = 5
console = Console()


def main() -> int:

    username = os.getenv("NORNIR_USERNAME") #exports your #USERNAME for logging into Network devices
    password = os.getenv("NORNIR_PASSWORD") #exports your #PASSWORD for logging into Network devices

   #Checks to confirm if VARs are present/set
    if not username or not password: 
        console.print(
            "ERROR: NORNIR_USERNAME and NORNIR_PASSWORD "
            "must be set in the environment."
        )
        return 1

    #Intializes Nornir
    try:
        nr = InitNornir(config_file="config.yaml") 
    except Exception as exc:
        console.print(
            f"[bold red]ERROR:[/] Could not initialize Nornir/NetBox inventory: {exc}"
        )
        return 1
    
    nr.inventory.defaults.username = username #Set's username as default vaule for logging across all devices
    nr.inventory.defaults.password = password #Set's password as default value for logigng across all devices

    #Check's to confirm it can reach Netbox's Inventory
    if not nr.inventory.hosts: 
        console.print(
            "No devices were loaded. Check the NetBox inventory plugin, "
            "API URL, token, permissions, and inventory configuration."
        )
        return 1

    # Inspects the tags then proceeds to pass them to the "normalize_tags" task/function.
    for host in nr.inventory.hosts.values():
        raw_tags = host.data.get("tags", [])
        normalized_tags = normalize_tags(raw_tags)
        host.data["tag_slugs"] = normalized_tags

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

    console.print("\n[bold]--- Filter results ---[/]")
    console.print(f"Target tag: {TARGET_TAG!r}")
    console.print(f"Matched devices: {len(targets.inventory.hosts)}")
    console.print(f"Device names: {list(targets.inventory.hosts)}")

    #Provides error output for if no devices are assigned to the specified parameter(Tag)
    if not targets.inventory.hosts:
        console.print(
            "\nNo devices matched the tag. Review the raw_tags and "
            "normalized_tags shown above."
        )
        return 0

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

    console.print(f"\nOutput directory: {dated_output_dir.resolve()}")
    console.print("\n[bold]--- Starting configuration backups ---[/]")

    # Collect the running configuration and environment output
    # from each device filtered from NetBox.
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.fields[host]}", justify="right"),
        BarColumn(),
        TextColumn("{task.completed:.0f}/{task.total:.0f}"),
        TextColumn("{task.fields[status]}", markup=True),
        TimeElapsedColumn(),
        console=console,
    )

    with progress:
        progress_tasks = {
            host_name: progress.add_task(
                "backup",
                total=PROGRESS_STEPS,
                host=host_name,
                status="[dim]Queued[/]",
            )
            for host_name in targets.inventory.hosts
        }

        results = targets.run(
            name="Back up Cisco running configurations and environment",
            task=save_device_outputs,
            output_dir=dated_output_dir,
            progress_update=make_progress_updater(progress, progress_tasks),
        )

    # This is essential while troubleshooting.
    print_result(results)

    console.print("\n[bold]--- Backup summary ---[/]")

    for host_name in targets.inventory.hosts:
        if host_name in results.failed_hosts:
          console.print(f"[bold red]FAILED[/] {host_name}")
        else:
            config_file = (
                dated_output_dir
                / host_name
                / f"{host_name}.cfg")

            environment_file = (
                dated_output_dir
                / host_name
                / f"{host_name}_environment.txt")

            console.print(f"[bold green]SAVED[/] {host_name}")
            console.print(f"        Config:      {config_file.resolve()}")
            console.print(f"        Environment: {environment_file.resolve()}")

    failed_count = len(results.failed_hosts)
    successful_count = len(targets.inventory.hosts) - failed_count
    console.print(
        f"\nCompleted: [green]{successful_count} successful[/], "
        f"[red]{failed_count} failed[/]"
    )
    return 1 if failed_count else 0


def make_progress_updater(
    progress: Progress,
    progress_tasks: dict[str, TaskID],
) -> Callable[[str, int, str], None]:
    """Create a thread-safe per-host progress callback for Nornir workers."""

    def update(host_name: str, completed: int, status: str) -> None:
        progress.update(
            progress_tasks[host_name],
            completed=completed,
            status=status,
            refresh=True,
        )

    return update


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

def save_device_outputs(
    task: Task,
    output_dir: Path,
    progress_update: Callable[[str, int, str], None],
) -> Result:
    """
    Retrieve and save the running configuration and environment
    information for a single network device.
    """

    host_name = task.host.name

    def set_progress(completed: int, status: str) -> None:
        progress_update(host_name, completed, status)

    def failure(message: str, exception: Exception | None = None) -> Result:
        set_progress(PROGRESS_STEPS, f"[bold red]Failed:[/] {escape(message)}")
        return Result(
            host=task.host,
            failed=True,
            exception=exception,
            result=message,
        )

    set_progress(0, "[cyan]Connecting[/]")

    # Retrieve the running configuration.
    set_progress(1, "[cyan]Collecting configuration[/]")
    try:
        running_config_results = task.run(
            name="Get running configuration",
            task=netmiko_send_command,
            command_string="show running-config",
            read_timeout=120,
        )
    except Exception as exc:
        return failure(f"Connection/configuration error: {exc}", exc)

    running_config_result = running_config_results[-1]

    if running_config_result.failed:
        return failure(
            (
                "Failed to retrieve running configuration: "
                f"{running_config_result.exception or running_config_result.result}"
            )
        )

    running_config = str(running_config_result.result)

    if not running_config.strip():
        return failure("The device returned an empty running configuration.")

    set_progress(2, "[cyan]Collecting environment[/]")

    # Retrieve the environment information.
    try:
        environment_results = task.run(
            name="Get environment information",
            task=netmiko_send_command,
            command_string="show environment all",
            read_timeout=120,
        )
    except Exception as exc:
        return failure(f"Environment collection error: {exc}", exc)

    environment_result = environment_results[-1]

    if environment_result.failed:
        return failure(
            (
                "Failed to retrieve environment information: "
                f"{environment_result.exception or environment_result.result}"
            )
        )

    environment_output = str(environment_result.result)

    if not environment_output.strip():
        return failure("The device returned empty environment information.")

    set_progress(3, "[cyan]Environment collected[/]")

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
        set_progress(4, "[cyan]Saving files[/]")
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
        return failure(
            (
                f"Could not write backup files for "
                f"{task.host.name}: {exc}"
            ),
            exc,
        )

    set_progress(PROGRESS_STEPS, "[bold green]Complete[/]")

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
    raise SystemExit(main())
