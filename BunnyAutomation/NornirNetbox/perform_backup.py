#!/usr/bin/env python3

from pathlib import Path
from typing import Any

from nornir import InitNornir
from nornir.core.filter import F
from nornir.core.task import Result, Task
from nornir_netmiko.tasks import netmiko_send_command
from nornir_utils.plugins.functions import print_result


TARGET_TAG = "nornirtest"
OUTPUT_DIR = Path("./config_backups")


def normalize_tags(tags: list[Any]) -> list[str]:
    """
    Convert NetBox tags into lowercase names/slugs.

    Handles:
      - strings
      - dictionaries
      - NetBox/tag objects
    """
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
    """Retrieve and save one Cisco device's running configuration."""

    print(
        f"[{task.host.name}] Connecting to "
        f"{task.host.hostname} using platform {task.host.platform!r}"
    )

    command_results = task.run(
        name="Get running configuration",
        task=netmiko_send_command,
        command_string="show running-config",
        read_timeout=120,
    )

    # task.run() returns a MultiResult. The Netmiko subtask is its last result.
    command_result = command_results[-1]

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

    if not configuration.strip():
        return Result(
            host=task.host,
            failed=True,
            result="The device returned an empty running configuration.",
        )

    filename = output_dir / f"{task.host.name}.txt"

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

    return Result(
        host=task.host,
        changed=False,
        result=f"Saved running configuration to {filename.resolve()}",
    )


def main() -> None:
    nr = InitNornir(config_file="config.yaml")
    nr.inventory.defaults.username = ""
    nr.inventory.defaults.password = ""

    print("\n--- Inventory loaded from NetBox ---")
    print(f"Total devices: {len(nr.inventory.hosts)}")

    if not nr.inventory.hosts:
        print(
            "No devices were loaded. Check the NetBox inventory plugin, "
            "API URL, token, permissions, and inventory configuration."
        )
        return

    # Inspect and normalize tags.
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

    targets = nr.filter(
        F(tag_slugs__contains=TARGET_TAG.casefold())
    )

    print("\n--- Filter results ---")
    print(f"Target tag: {TARGET_TAG!r}")
    print(f"Matched devices: {len(targets.inventory.hosts)}")
    print(f"Device names: {list(targets.inventory.hosts)}")

    if not targets.inventory.hosts:
        print(
            "\nNo devices matched the tag. Review the raw_tags and "
            "normalized_tags shown above."
        )
        return

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(f"\nOutput directory: {OUTPUT_DIR.resolve()}")
    print("\n--- Starting configuration backups ---")

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


if __name__ == "__main__":
    main()