from ncclient import manager
from xml.dom import minidom as dom
from netconf_creds import *

my_device = {
    "host":f'{GLOBAL_URL}',
    "port": f'{NETCONF_PORT}',
    "username": f'{USERNAME}',
    "password":f'{PASSWORD}',
    "hostkey_verify": False
}

with manager.connect(**my_device) as m:
    running_config = m.get_config(source="running").xml

print(dom.parseString(running_config).toprettyxml())