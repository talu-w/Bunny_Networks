from netmiko import ConnectHandler
from rich import print
from my_creds import *

#Genie Parser https://pubhub.devnetcloud.com/media/genie-feature-browser/docs/#/parsers

with ConnectHandler(**my_device) as my_connection:
        my_version = my_connection.send_command(command_string="show interfaces stats", use_genie=True) 
        print(my_version)