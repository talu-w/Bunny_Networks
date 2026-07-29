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

back_up_file = "switch_configuration_2.xml"

with open (back_up_file, "r") as r:
      back_upconfig = r.read()

with manager.connect(**my_device) as m:
      push_config = m.edit_config(target="running", config=back_upconfig)

print(push_config)
