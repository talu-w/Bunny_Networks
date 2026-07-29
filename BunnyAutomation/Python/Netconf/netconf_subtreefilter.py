from ncclient import manager
from xml.dom import minidom
from netconf_creds import *

my_device = {
    "host":f'{GLOBAL_URL}',
    "port": f'{NETCONF_PORT}',
    "username": f'{USERNAME}',
    "password":f'{PASSWORD}',
    "hostkey_verify": False
}

subtree_filter = """
  <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
    <interface>
      <name/>
      <description/>
    </interface>
  </interfaces>
"""


with manager.connect(**my_device) as m:
     result = m.get_config(source="running", filter=("subtree", subtree_filter)).xml


print(minidom.parseString(result).toprettyxml())
