from ncclient import manager
from xml.dom import minidom

my_device = {
    "host":"devnetsandboxiosxec8k.cisco.com",
    "port": 830,
    "username":"talu.whitley",
    "password":"2lR_fqA-X79bt",
    "hostkey_verify": False
}

router_ospf_config = """
        <config xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
                <native xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-native">
                        <router operation="merge">
                                <router-ospf xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-ospf">
                                        <ospf>
                                                <process-id>
                                                        <id>1</id>
                                                        <network>
                                                                <ip>192.168.40.0</ip>
                                                                <wildcard>0.0.0.255</wildcard>
                                                                <area>0</area>
                                                        </network>
                                                        <network>
                                                                <ip>192.168.50.0</ip>
                                                                <wildcard>0.0.0.255</wildcard>
                                                                <area>0</area>
                                                        </network>
                                                        <router-id>1.1.1.1</router-id>
                                                </process-id>
                                        </ospf>
                                </router-ospf>
                        </router>
                </native>
        </config>
"""

with manager.connect(**my_device) as m:
    result = m.edit_config(target="running", config=router_ospf_config)


print(result)
