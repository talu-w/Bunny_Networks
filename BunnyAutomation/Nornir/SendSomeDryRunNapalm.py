from nornir import InitNornir
from nornir_napalm.plugins.tasks import napalm_configure
from nornir_utils.plugins.functions import print_result

nr = InitNornir(config_file="config.yaml")

'''Dry run allows you to test a configuration against a device before pushing
   IMPORANT: Napalm is the only tool that can perform this. Using any other such as
   NetMiko will still push the configurations to the device'''

def create_vlan_interface(task):
    task.run(task=napalm_configure, filename="NetVlanInterface.txt", dry_run=True)

results = nr.run(task=create_vlan_interface)
print_result(results)