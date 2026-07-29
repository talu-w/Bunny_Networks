from nornir_netmiko.tasks import netmiko_send_config
from nornir import InitNornir
from nornir_utils.plugins.functions import print_result

nr = InitNornir(config_file="config.yaml")

config_tempalte = ['interface loopback 88','description Netmiko Nornir', 'ip address 88.88.88.88 255.255.255.255']
def send_some_netmiko_configs(task):
      task.run(task=netmiko_send_config, config_commands=config_tempalte)
results = nr.run(task=send_some_netmiko_configs)
print_result(results)