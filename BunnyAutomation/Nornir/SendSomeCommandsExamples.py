from nornir import InitNornir #Will be used in all Nornir scripts
from nornir_scrapli.tasks import send_command #Send one command
from nornir_scrapli.tasks import send_commands #Send multiple commands
from nornir_scrapli.tasks import send_commands_from_file #Send commands from specified file
from nornir_utils.plugins.functions import print_result

nr = InitNornir(config_file="config.yaml") #Starts up Nornir. Loads the config file specified

command_list = ["show run interface vlan103", "show version", "show interface brief"]

'''Will loop through list while using the show_command since it only sends one command at at ime'''
# def show_command(task): 
#     for cmd in command_list:
#         task.run(task=send_command, command=cmd)
# results = nr.run(task=show_command)
# print_result(results)

'''Use's show_commands to send a full list instead of having to loop through it one at a time'''
# def show_commands(task): #Uses the show_commands to take the full list
#         task.run(task=send_commands, commands=command_list)
# results = nr.run(task=show_commands)
# print_result(results)

'''Pulls the commands from a speified file. Can be useful to have non expeirenced automation engineers interact with the network'''
def show_command_from_file(task):
        task.run(task=send_commands_from_file, file="MyShowCommands.txt")
results = nr.run(task=show_command_from_file)
print_result(results)