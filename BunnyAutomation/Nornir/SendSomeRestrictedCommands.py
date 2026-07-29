from nornir import InitNornir #Will be used in all Nornir scripts
from nornir_scrapli.tasks import send_command #Send one command
from nornir_scrapli.tasks import send_commands #Send multiple commands
from nornir_scrapli.tasks import send_commands_from_file #Send commands from specified file
from nornir_utils.plugins.functions import print_result

nr = InitNornir(config_file="config.yaml") #Starts up Nornir. Loads the config file specified. For this to work must username provided in SecurityParser.txt

commands = input("\nEnter Commands You Wish To Send: ")
cmds = commands.split(",")

'''Use's the commands referenced in the parser file to limit what show commands are allowed on the device per user.
   Useful when limiting interactions with the network by role'''

def push_restricted_commands(task):
    for cmd in cmds:
      task.run(task=send_command, command=cmd)
results = nr.run(task=push_restricted_commands)
print_result(results)