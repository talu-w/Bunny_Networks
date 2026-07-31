#!/usr/bin/env python3

import os
import sys
from typing import Any

from nornir import InitNornir
from nornir.core.filter import F
from nornir_netmiko.tasks import netmiko_send_command
from nornir_utils.plugins.functions import print_result


def normalize_tag_slugs(tags: list[Any]) -> list[str]:
    """Return normalized tag slugs from NetBox inventory data."""

    normalized: list[str] = []

    for tag in tags:
        if isinstance(tag, str):
            value = tag

        elif isinstance(tag, dict):
            value = tag.get("slug") or tag.get("name")

        else:
            value = (
                getattr(tag, "slug", None)
                or getattr(tag, "name", None)
            )

        if value:
            normalized.append(str(value).casefold())

    return normalized


def main() -> int:
    nr = InitNornir(config_file="config.yaml")

    nr.inventory.defaults.username = ""
    nr.inventory.defaults.password = ""

    # Prepare NetBox tag data for Nornir F filtering.
    for host in nr.inventory.hosts.values():
        host.data["tag_slugs"] = normalize_tag_slugs(
            host.data.get("tags", [])
        )

    # Local Nornir inventory filtering.
    testing_devices = nr.filter(
        F(tag_slugs__contains="nornirtest")
    )

    if not testing_devices.inventory.hosts:
        print("No inventory devices have the NetBox tag 'testing'.")
        return 0

    print("Matched devices:")

    for host in testing_devices.inventory.hosts.values():
        print(
            f"  {host.name}: "
            f"hostname={host.hostname}, "
            f"platform={host.platform}, "
            f"tags={host.data['tag_slugs']}"
        )

    results = testing_devices.run(
        name="Sending command", #
        task=netmiko_send_command, #
        command_string="",  #
    )

    print_result(results)

    return 2 if results.failed_hosts else 0


if __name__ == "__main__":
    sys.exit(main())