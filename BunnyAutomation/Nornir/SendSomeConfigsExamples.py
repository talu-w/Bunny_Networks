from nornir import InitNornir #Will be used in all Nornir scripts
from nornir_scrapli.tasks import send_config #Send's one config line
from nornir_scrapli.tasks import send_configs #Send multiple configs
from nornir_scrapli.tasks import send_configs_from_file #Send multiple configs from file
from nornir_utils.plugins.functions import print_result

nr = InitNornir(config_file="config.yaml") #Starts up Nornir. Loads the config file specified

config_template = ['interface loopback 82','description "For the warriors"','ip address 82.82.82.82 255.255.255.255']

# def send_some_config(task):
#     task.run(task=send_config, config="interface loopback 84")
# results = nr.run(task=send_some_config)
# print_result(results)

# def send_some_configs(task):
#     task.run(task=send_configs, configs=config_template)
# results = nr.run(task=send_some_configs)
# print_result(results)

def send_some_configs_from_file(task):
    task.run(task=send_configs_from_file, file="MyConfigurationTemplate.txt", dry_run = False) #If dry_run set to True, will only login to devices and confirm it has Config access. Default is False
results = nr.run(task=send_some_configs_from_file)
print_result(results)
