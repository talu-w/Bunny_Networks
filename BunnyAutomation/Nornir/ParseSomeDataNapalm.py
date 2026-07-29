from nornir_napalm.plugins.tasks import napalm_get #Napalm allows you to be vendor agnostic.
from nornir import InitNornir
from nornir_utils.plugins.functions import print_result

#NAPALM Getters documentation https://napalm.readthedocs.io/en/latest/support/
nr = InitNornir(config_file="config.yaml")

'''Napalm is a module that can interact with multi-vendor enviornments.'''

def get_some_napalm(task):
    task.run(napalm_get, getters="get_facts") #Use different gettters from the docs to have it interact across all devices within Nornir

result = nr.run(task=get_some_napalm)
print_result(result)
