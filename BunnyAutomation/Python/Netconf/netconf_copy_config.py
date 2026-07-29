###Will pull Netconf Configuration Data and save it to a specified DIR. 
###Replaces specific parameters in order to allow the config to be merged with other devices

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
      pretty_config = dom.parseString(running_config).toprettyxml()
      config_xml = pretty_config.replace("<data", "<config xmlns='urn:ietf:params:xml:ns:netconf:base:1.0'", 1).replace("</data>", "</config>", 1)
      with open ("switch_configuration_2.xml", "w") as w:
            for line in config_xml.split("\n",2)[2].rsplit("\n",2)[0]:
                      w.write(line)
