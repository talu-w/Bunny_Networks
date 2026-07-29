import textfsm # https://github.com/networktocode/ntc-templates/tree/master/ntc_templates/templates - Template location

from netmiko import ConnectHandler
from rich import print
import json
from my_creds import *


with ConnectHandler(**my_device) as my_connection:
        interfaces = my_connection.send_command(command_string="show interfaces", use_textfsm=True)        
        print(interfaces) #Use rich for parsing
        for interface in interfaces:
                print(interface['mac_address']) #Loop for grabbing MACs off interfaces
        
        # print(json.dumps(interfaces, indent=4)) #Use json.dump indent for parsing