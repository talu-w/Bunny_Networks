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


with manager.connect(**my_device) as m:
    result = m.get_config(source="running", filter=("xpath", "/native/hostname")).xml 
                                                            #"//hostname also works in that XPATH will search through the reply and filter"


print(minidom.parseString(result).toprettyxml())
