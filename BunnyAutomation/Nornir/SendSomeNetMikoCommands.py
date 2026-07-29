from nornir_netmiko.tasks import netmiko_send_command
from nornir import InitNornir
from nornir_utils.plugins.functions import print_result

nr = InitNornir(config_file="config.yaml")

commands = ['show interface brief', 'show run | sec hostname', 'show version']
def send_some_netmiko_command(task):
    for cmd in commands:
      task.run(task=netmiko_send_command, command_string=cmd)
results = nr.run(task=send_some_netmiko_command)
print_result(results)