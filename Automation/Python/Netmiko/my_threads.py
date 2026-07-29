from netmiko import ConnectHandler
from inventory import DEVICES
from concurrent.futures import ThreadPoolExecutor
from rich import print

def show_some_commands(device):
    with ConnectHandler(
        device_type="cisco_ios",
        host=device["host"],
        username="talu.whitley",
        password="sTwp62R_a_5TOoBE"
        ) as my_connection:
        result = my_connection.send_command(command_string="show ip int brief")
        print(result)

with ThreadPoolExecutor() as executor:
   multiple_connects = executor.map(show_some_commands, DEVICES)
   for connects in multiple_connects:
       print(connects)