from nornir import InitNornir #Will be used in all Nornir scripts
from nornir_scrapli.tasks import send_configs_from_file #Send multiple configs from file
from nornir_utils.plugins.functions import print_result
from tqdm import tqdm #Used for creating Progress bar

nr = InitNornir(config_file="config.yaml") #Starts up Nornir. Loads the config file specified

'''Create progress bars with "tqdm"
   In "config.yaml", update "num_workers" to 1 to witness
   More devices, add higher number'''

def send_some_configs_from_file(task, progress_bar):
    task.run(task=send_configs_from_file, file="MyConfigurationTemplate.txt", dry_run = False) #If dry_run set to True, will only login to devices and confirm it has Config access. Default is False
    progress_bar.update()

with tqdm(total=len(nr.inventory.hosts)) as progress_bar:
    results = nr.run(task=send_some_configs_from_file, progress_bar=progress_bar)
print_result(results)
