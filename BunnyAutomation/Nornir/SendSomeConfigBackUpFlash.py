from nornir import InitNornir #Will be used in all Nornir scripts
from nornir_scrapli.tasks import send_interactive #Send one command
from nornir_scrapli.tasks import send_command 
from nornir_utils.plugins.functions import print_result

nr = InitNornir(config_file="config.yaml") #Starts up Nornir. Loads the config file specified

'''The send_interactive command allows nornir to handle prompt responses that are returned by the device. 
   In this example, we are performing a backup of the running-config to the flash as ipvzero.
   Then a rollback is performed that calls to that saved flash. '''

def save_config_to_flash(task):
    cmds = [("copy run flash:ipvzero", "Destination filename"), ("\n",f"{task.host}#")] #The final part of the tuple let's Scrapli know the process has completed and gracefully exit
    task.run(task=send_interactive, interact_events=cmds)

results = nr.run(task=save_config_to_flash)
print_result(results)

def roll_back_config(task):
    task.run(task=send_command, command="conifig replace flash:ipvzero force") #Will perform rollback to saved file
results = nr.run(task=roll_back_config)
print_result(results)
