from netmiko import ConnectHandler
from my_creds import *


create_loopback = ["interface loopback 82", "description 82 for the warriors. *Created by Netmiko*" ]
with ConnectHandler(**my_device) as my_connection:
        loopback_results = my_connection.send_config_set(config_commands=create_loopback)
        print(loopback_results)