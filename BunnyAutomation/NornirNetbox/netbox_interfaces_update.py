#!/usr/bin/env python3

"""
Collect Cisco VLAN, access-port, trunk, and switch-stack interface data.

Commands collected:
    show vlan brief
    show interfaces trunk

Output:
    reports/vlan_trunk_inventory/<hostname>.json
"""

from __future__ import annotations

import json
import logging
import re
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from nornir import InitNornir
from nornir.core.task import Result, Task
from nornir_netmiko.tasks import netmiko_send_command
from nornir_utils.plugins.functions import print_result


REPORT_ROOT = Path("reports/vlan_trunk_inventory")

SHOW_VLAN_COMMAND = "show vlan brief"
SHOW_TRUNK_COMMAND = "show interfaces trunk"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class InterfaceIdentity:
    original_name: str
    interface_type: str
    stack_member: int | None
    slot: int | None
    port: int | None
    subinterface: int | None = None
    logical_interface: bool = False


@dataclass
class AccessInterface:
    interface: str
    interface_type: str
    stack_member: int | None
    slot: int | None
    port: int | None
    vlan_id: int
    vlan_name: str
    vlan_status: str


@dataclass
class TrunkInterface:
    interface: str
    interface_type: str
    stack_member: int | None
    slot: int | None
    port: int | None

    mode: str = ""
    encapsulation: str = ""
    status: str = ""
    native_vlan: int | None = None

    allowed_vlans: list[int] = field(default_factory=list)
    active_vlans: list[int] = field(default_factory=list)
    forwarding_vlans: list[int] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Interface-name parsing
# ---------------------------------------------------------------------------

INTERFACE_TYPE_MAP = {
    "fa": "FastEthernet",
    "fastethernet": "FastEthernet",
    "gi": "GigabitEthernet",
    "gig": "GigabitEthernet",
    "gigabitethernet": "GigabitEthernet",
    "te": "TenGigabitEthernet",
    "ten": "TenGigabitEthernet",
    "tengigabitethernet": "TenGigabitEthernet",
    "tw": "TwoGigabitEthernet",
    "two": "TwoGigabitEthernet",
    "twogigabitethernet": "TwoGigabitEthernet",
    "fo": "FortyGigabitEthernet",
    "fortygigabitethernet": "FortyGigabitEthernet",
    "hu": "HundredGigabitEthernet",
    "hundredgigabitethernet": "HundredGigabitEthernet",
    "eth": "Ethernet",
    "ethernet": "Ethernet",
    "po": "Port-channel",
    "port-channel": "Port-channel",
    "portchannel": "Port-channel",
    "vl": "Vlan",
    "vlan": "Vlan",
    "lo": "Loopback",
    "loopback": "Loopback",
}


def parse_interface_name(interface_name: str) -> InterfaceIdentity:
    """
    Parse Cisco interface names and extract stack-member information.

    Examples:
        Gi1/0/48  -> member=1, slot=0, port=48
        Tw2/0/1   -> member=2, slot=0, port=1
        Te3/1/1   -> member=3, slot=1, port=1
        Gi0/24    -> standalone interface; slot=0, port=24
        Po10      -> logical interface
    """

    cleaned_name = interface_name.strip().replace(" ", "")

    # Physical stack interface:
    # Gi1/0/48
    # Tw2/0/1
    # Te3/1/1
    stack_match = re.match(
        r"^(?P<type>[A-Za-z-]+)"
        r"(?P<member>\d+)/"
        r"(?P<slot>\d+)/"
        r"(?P<port>\d+)"
        r"(?:\.(?P<subinterface>\d+))?$",
        cleaned_name,
    )

    if stack_match:
        interface_prefix = stack_match.group("type").lower()
        interface_type = INTERFACE_TYPE_MAP.get(
            interface_prefix,
            stack_match.group("type"),
        )

        return InterfaceIdentity(
            original_name=cleaned_name,
            interface_type=interface_type,
            stack_member=int(stack_match.group("member")),
            slot=int(stack_match.group("slot")),
            port=int(stack_match.group("port")),
            subinterface=(
                int(stack_match.group("subinterface"))
                if stack_match.group("subinterface")
                else None
            ),
            logical_interface=False,
        )

    # Standalone/modular two-number interface:
    # Gi0/24
    # Te1/1
    standalone_match = re.match(
        r"^(?P<type>[A-Za-z-]+)"
        r"(?P<slot>\d+)/"
        r"(?P<port>\d+)"
        r"(?:\.(?P<subinterface>\d+))?$",
        cleaned_name,
    )

    if standalone_match:
        interface_prefix = standalone_match.group("type").lower()
        interface_type = INTERFACE_TYPE_MAP.get(
            interface_prefix,
            standalone_match.group("type"),
        )

        return InterfaceIdentity(
            original_name=cleaned_name,
            interface_type=interface_type,
            stack_member=None,
            slot=int(standalone_match.group("slot")),
            port=int(standalone_match.group("port")),
            subinterface=(
                int(standalone_match.group("subinterface"))
                if standalone_match.group("subinterface")
                else None
            ),
            logical_interface=False,
        )

    # Logical interfaces:
    # Po1
    # Vlan10
    # Lo0
    logical_match = re.match(
        r"^(?P<type>[A-Za-z-]+)(?P<number>\d+)"
        r"(?:\.(?P<subinterface>\d+))?$",
        cleaned_name,
    )

    if logical_match:
        interface_prefix = logical_match.group("type").lower()
        interface_type = INTERFACE_TYPE_MAP.get(
            interface_prefix,
            logical_match.group("type"),
        )

        return InterfaceIdentity(
            original_name=cleaned_name,
            interface_type=interface_type,
            stack_member=None,
            slot=None,
            port=int(logical_match.group("number")),
            subinterface=(
                int(logical_match.group("subinterface"))
                if logical_match.group("subinterface")
                else None
            ),
            logical_interface=True,
        )

    return InterfaceIdentity(
        original_name=cleaned_name,
        interface_type="Unknown",
        stack_member=None,
        slot=None,
        port=None,
        logical_interface=True,
    )


# ---------------------------------------------------------------------------
# VLAN-list helpers
# ---------------------------------------------------------------------------

def expand_vlan_list(vlan_text: str) -> list[int]:
    """
    Expand Cisco VLAN expressions.

    Examples:
        "1,10,20-22" -> [1, 10, 20, 21, 22]
        "none"       -> []
        "all"        -> [1 ... 4094]
    """

    normalized = vlan_text.strip().lower()

    if not normalized or normalized in {"none", "n/a", "--"}:
        return []

    if normalized == "all":
        return list(range(1, 4095))

    vlan_ids: set[int] = set()

    for item in normalized.replace(" ", "").split(","):
        if not item:
            continue

        if "-" in item:
            start_text, end_text = item.split("-", maxsplit=1)

            if not start_text.isdigit() or not end_text.isdigit():
                continue

            start_vlan = int(start_text)
            end_vlan = int(end_text)

            if start_vlan > end_vlan:
                start_vlan, end_vlan = end_vlan, start_vlan

            vlan_ids.update(range(start_vlan, end_vlan + 1))

        elif item.isdigit():
            vlan_ids.add(int(item))

    return sorted(vlan_ids)


def compress_vlan_list(vlan_ids: Iterable[int]) -> str:
    """
    Compress VLAN IDs for readable console output.

    Example:
        [1, 10, 20, 21, 22] -> "1,10,20-22"
    """

    sorted_vlans = sorted(set(vlan_ids))

    if not sorted_vlans:
        return "none"

    ranges: list[str] = []
    range_start = sorted_vlans[0]
    previous_vlan = sorted_vlans[0]

    for vlan_id in sorted_vlans[1:]:
        if vlan_id == previous_vlan + 1:
            previous_vlan = vlan_id
            continue

        if range_start == previous_vlan:
            ranges.append(str(range_start))
        else:
            ranges.append(f"{range_start}-{previous_vlan}")

        range_start = vlan_id
        previous_vlan = vlan_id

    if range_start == previous_vlan:
        ranges.append(str(range_start))
    else:
        ranges.append(f"{range_start}-{previous_vlan}")

    return ",".join(ranges)


# ---------------------------------------------------------------------------
# show vlan brief parser
# ---------------------------------------------------------------------------

def split_interface_list(interface_text: str) -> list[str]:
    """Split the interface-list section of show vlan brief."""

    return [
        interface.strip()
        for interface in interface_text.split(",")
        if interface.strip()
    ]


def parse_show_vlan_brief(output: str) -> tuple[list[dict[str, Any]], list[AccessInterface]]:
    """
    Parse Cisco IOS/IOS-XE 'show vlan brief'.

    Handles wrapped interface lines by retaining the current VLAN.
    """

    vlans: list[dict[str, Any]] = []
    access_interfaces: list[AccessInterface] = []

    current_vlan: dict[str, Any] | None = None

    vlan_line_pattern = re.compile(
        r"^\s*(?P<vlan_id>\d+)\s+"
        r"(?P<vlan_name>\S+)\s+"
        r"(?P<status>active|act/unsup|suspended|shutdown)"
        r"(?:\s+(?P<ports>.*))?$",
        re.IGNORECASE,
    )

    continuation_pattern = re.compile(
        r"^\s+(?P<ports>"
        r"(?:Fa|Gi|Te|Tw|Fo|Hu|Eth|Po)"
        r"\S+.*)$",
        re.IGNORECASE,
    )

    for raw_line in output.splitlines():
        line = raw_line.rstrip()

        if not line:
            continue

        if line.lower().startswith("vlan"):
            continue

        if set(line.strip()) <= {"-", " "}:
            continue

        vlan_match = vlan_line_pattern.match(line)

        if vlan_match:
            current_vlan = {
                "vlan_id": int(vlan_match.group("vlan_id")),
                "vlan_name": vlan_match.group("vlan_name"),
                "status": vlan_match.group("status"),
                "interfaces": [],
            }

            ports = vlan_match.group("ports") or ""
            current_vlan["interfaces"].extend(split_interface_list(ports))
            vlans.append(current_vlan)
            continue

        continuation_match = continuation_pattern.match(line)

        if continuation_match and current_vlan is not None:
            current_vlan["interfaces"].extend(
                split_interface_list(
                    continuation_match.group("ports")
                )
            )

    for vlan in vlans:
        for interface_name in vlan["interfaces"]:
            identity = parse_interface_name(interface_name)

            access_interfaces.append(
                AccessInterface(
                    interface=identity.original_name,
                    interface_type=identity.interface_type,
                    stack_member=identity.stack_member,
                    slot=identity.slot,
                    port=identity.port,
                    vlan_id=vlan["vlan_id"],
                    vlan_name=vlan["vlan_name"],
                    vlan_status=vlan["status"],
                )
            )

    return vlans, access_interfaces


# ---------------------------------------------------------------------------
# show interfaces trunk parser
# ---------------------------------------------------------------------------

TRUNK_SECTION_HEADERS = {
    "allowed": "vlans allowed on trunk",
    "active": "vlans allowed and active in management domain",
    "forwarding": "vlans in spanning tree forwarding state and not pruned",
}


def parse_show_interfaces_trunk(output: str) -> list[TrunkInterface]:
    """Parse Cisco IOS/IOS-XE 'show interfaces trunk' output."""

    trunk_map: dict[str, TrunkInterface] = {}
    current_section: str | None = None

    operational_trunk_pattern = re.compile(
        r"^\s*(?P<interface>\S+)\s+"
        r"(?P<mode>\S+)\s+"
        r"(?P<encapsulation>\S+)\s+"
        r"(?P<status>\S+)\s+"
        r"(?P<native_vlan>\d+|-)\s*$"
    )

    vlan_membership_pattern = re.compile(
        r"^\s*(?P<interface>\S+)\s+"
        r"(?P<vlans>(?:none|all|[\d,\-\s]+))\s*$",
        re.IGNORECASE,
    )

    for raw_line in output.splitlines():
        line = raw_line.rstrip()
        lowered_line = line.strip().lower()

        if not lowered_line:
            continue

        if lowered_line.startswith("port") and "native vlan" in lowered_line:
            current_section = "operational"
            continue

        matched_section = False

        for section_name, section_header in TRUNK_SECTION_HEADERS.items():
            if section_header in lowered_line:
                current_section = section_name
                matched_section = True
                break

        if matched_section:
            continue

        if set(line.strip()) <= {"-", " "}:
            continue

        if current_section == "operational":
            match = operational_trunk_pattern.match(line)

            if not match:
                continue

            interface_name = match.group("interface")
            identity = parse_interface_name(interface_name)

            native_vlan_text = match.group("native_vlan")

            trunk_map[interface_name] = TrunkInterface(
                interface=identity.original_name,
                interface_type=identity.interface_type,
                stack_member=identity.stack_member,
                slot=identity.slot,
                port=identity.port,
                mode=match.group("mode"),
                encapsulation=match.group("encapsulation"),
                status=match.group("status"),
                native_vlan=(
                    int(native_vlan_text)
                    if native_vlan_text.isdigit()
                    else None
                ),
            )

            continue

        if current_section in {"allowed", "active", "forwarding"}:
            match = vlan_membership_pattern.match(line)

            if not match:
                continue

            interface_name = match.group("interface")
            vlan_ids = expand_vlan_list(match.group("vlans"))

            if interface_name not in trunk_map:
                identity = parse_interface_name(interface_name)

                trunk_map[interface_name] = TrunkInterface(
                    interface=identity.original_name,
                    interface_type=identity.interface_type,
                    stack_member=identity.stack_member,
                    slot=identity.slot,
                    port=identity.port,
                )

            trunk = trunk_map[interface_name]

            if current_section == "allowed":
                trunk.allowed_vlans = vlan_ids
            elif current_section == "active":
                trunk.active_vlans = vlan_ids
            elif current_section == "forwarding":
                trunk.forwarding_vlans = vlan_ids

    return list(trunk_map.values())


# ---------------------------------------------------------------------------
# Stack-member organization
# ---------------------------------------------------------------------------

def interface_sort_key(interface_name: str) -> tuple[int, int, int, str]:
    identity = parse_interface_name(interface_name)

    member = identity.stack_member if identity.stack_member is not None else 9999
    slot = identity.slot if identity.slot is not None else 9999
    port = identity.port if identity.port is not None else 9999

    return member, slot, port, interface_name


def organize_by_stack_member(
    access_interfaces: list[AccessInterface],
    trunk_interfaces: list[TrunkInterface],
) -> dict[str, dict[str, list[dict[str, Any]]]]:
    """
    Group access and trunk interfaces by stack member.

    Physical three-number names are grouped as:
        stack_member_1
        stack_member_2
        stack_member_3

    Two-number standalone interfaces are grouped under:
        standalone

    Port-channels and other logical interfaces are grouped under:
        logical
    """

    grouped: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
        lambda: {
            "access_interfaces": [],
            "trunk_interfaces": [],
        }
    )

    def group_name(
        stack_member: int | None,
        interface_type: str,
    ) -> str:
        if stack_member is not None:
            return f"stack_member_{stack_member}"

        if interface_type in {"Port-channel", "Vlan", "Loopback", "Unknown"}:
            return "logical"

        return "standalone"

    for interface in access_interfaces:
        key = group_name(
            interface.stack_member,
            interface.interface_type,
        )

        grouped[key]["access_interfaces"].append(asdict(interface))

    for interface in trunk_interfaces:
        key = group_name(
            interface.stack_member,
            interface.interface_type,
        )

        grouped[key]["trunk_interfaces"].append(asdict(interface))

    for member_data in grouped.values():
        member_data["access_interfaces"].sort(
            key=lambda item: interface_sort_key(item["interface"])
        )
        member_data["trunk_interfaces"].sort(
            key=lambda item: interface_sort_key(item["interface"])
        )

    return dict(
        sorted(
            grouped.items(),
            key=lambda item: stack_group_sort_key(item[0]),
        )
    )


def stack_group_sort_key(group_name: str) -> tuple[int, int]:
    if group_name.startswith("stack_member_"):
        member_number = int(group_name.rsplit("_", maxsplit=1)[1])
        return 0, member_number

    if group_name == "standalone":
        return 1, 0

    return 2, 0


# ---------------------------------------------------------------------------
# Nornir task
# ---------------------------------------------------------------------------

def collect_vlan_and_trunk_data(task: Task) -> Result:
    """Collect and parse VLAN/trunk data from one device."""

    vlan_result = task.run(
        task=netmiko_send_command,
        name="Collecting VLAN information",
        command_string=SHOW_VLAN_COMMAND,
        read_timeout=60,
    )

    trunk_result = task.run(
        task=netmiko_send_command,
        name="Collecting trunk information",
        command_string=SHOW_TRUNK_COMMAND,
        read_timeout=60,
    )

    vlan_output = str(vlan_result.result)
    trunk_output = str(trunk_result.result)

    vlans, access_interfaces = parse_show_vlan_brief(vlan_output)
    trunk_interfaces = parse_show_interfaces_trunk(trunk_output)

    stack_members = organize_by_stack_member(
        access_interfaces=access_interfaces,
        trunk_interfaces=trunk_interfaces,
    )

    detected_members = sorted(
        {
            interface.stack_member
            for interface in access_interfaces + trunk_interfaces
            if interface.stack_member is not None
        }
    )

    report = {
        "hostname": task.host.name,
        "management_address": task.host.hostname,
        "platform": task.host.platform,
        "collected_at": datetime.now().astimezone().isoformat(),
        "commands": {
            "vlan": SHOW_VLAN_COMMAND,
            "trunk": SHOW_TRUNK_COMMAND,
        },
        "summary": {
            "vlan_count": len(vlans),
            "access_interface_count": len(access_interfaces),
            "trunk_interface_count": len(trunk_interfaces),
            "detected_stack_members": detected_members,
            "detected_stack_member_count": len(detected_members),
        },
        "vlans": vlans,
        "access_interfaces": [
            asdict(interface)
            for interface in sorted(
                access_interfaces,
                key=lambda item: interface_sort_key(item.interface),
            )
        ],
        "trunk_interfaces": [
            asdict(interface)
            for interface in sorted(
                trunk_interfaces,
                key=lambda item: interface_sort_key(item.interface),
            )
        ],
        "stack_members": stack_members,
    }

    report_file = save_report(
        hostname=task.host.name,
        report=report,
    )

    report["report_file"] = str(report_file)

    return Result(
        host=task.host,
        result=report,
        changed=False,
    )


# ---------------------------------------------------------------------------
# Report output
# ---------------------------------------------------------------------------

def save_report(hostname: str, report: dict[str, Any]) -> Path:
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)

    safe_hostname = re.sub(
        r"[^A-Za-z0-9_.-]",
        "_",
        hostname,
    )

    report_file = REPORT_ROOT / f"{safe_hostname}.json"

    report_file.write_text(
        json.dumps(report, indent=4),
        encoding="utf-8",
    )

    return report_file


def print_device_summary(hostname: str, report: dict[str, Any]) -> None:
    summary = report["summary"]

    print()
    print("=" * 90)
    print(f"DEVICE: {hostname}")
    print("=" * 90)

    detected_members = summary["detected_stack_members"]

    if detected_members:
        print(
            "Detected stack members: "
            + ", ".join(str(member) for member in detected_members)
        )
    else:
        print("Detected stack members: none; device appears standalone")

    print(f"Configured VLANs: {summary['vlan_count']}")
    print(f"Access interfaces: {summary['access_interface_count']}")
    print(f"Operational trunks: {summary['trunk_interface_count']}")
    print(f"JSON report: {report['report_file']}")

    for member_name, member_data in report["stack_members"].items():
        print()
        print(f"[{member_name}]")

        access_interfaces = member_data["access_interfaces"]
        trunk_interfaces = member_data["trunk_interfaces"]

        if access_interfaces:
            print("  Access interfaces:")

            for interface in access_interfaces:
                print(
                    f"    {interface['interface']:<12} "
                    f"VLAN {interface['vlan_id']:<4} "
                    f"{interface['vlan_name']}"
                )

        if trunk_interfaces:
            print("  Trunk interfaces:")

            for interface in trunk_interfaces:
                print(
                    f"    {interface['interface']:<12} "
                    f"native={interface['native_vlan']} "
                    f"allowed={compress_vlan_list(interface['allowed_vlans'])} "
                    f"active={compress_vlan_list(interface['active_vlans'])} "
                    f"forwarding="
                    f"{compress_vlan_list(interface['forwarding_vlans'])}"
                )

        if not access_interfaces and not trunk_interfaces:
            print("  No interfaces discovered")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    nr = InitNornir(config_file="config.yaml")

    try:
        # Apply your existing NetBox/Nornir filter here if needed.
        #
        # Examples:
        #
        # switches = nr.filter(platform="ios")
        #
        # Or use the same tag-filtering method already present in your
        # current NetBox-backed scripts.
        switches = nr

        results = switches.run(
            task=collect_vlan_and_trunk_data,
            name="Collecting VLAN and switch-stack information",
        )

        for hostname, multi_result in results.items():
            if multi_result.failed:
                print()
                print(f"[FAILED] {hostname}")
                print_result(multi_result)
                continue

            # The parent task is normally the first result.
            report = multi_result[0].result

            if not isinstance(report, dict):
                print(f"[FAILED] No structured report returned for {hostname}")
                continue

            print_device_summary(hostname, report)

    finally:
        nr.close_connections()


if __name__ == "__main__":
    main()