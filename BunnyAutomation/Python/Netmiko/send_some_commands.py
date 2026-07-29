from netmiko import ConnectHandler
from my_creds import *
#The "send_command" will send a command to a network device Netmiko can connect too.
#Will only do show commands



my_commands = ["Show int status", "Show run | sec hostname", "show ip route", "show run interface loopback83"]
with ConnectHandler(**my_device) as my_connection:
    for command in my_commands:
        running_config = my_connection.send_command(command_string=command)
        print(running_config)