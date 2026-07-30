'''Basic Nornir job that goes through Netbox as your inventory including filter parameters'''

from nornir import InitNornir
from rich import print as rprint

nr = InitNornir(config_file="config.yaml") #Initialize Nornir

def randomtest(task):
    rprint(f"Hell, my name is {task.host}") #Print Host/Name from Netbox of object
    rprint(f"My Ip Address/Hostname is {task.host.hostname}") #Print IP or Hostname within field of Object
    rprint(f"My platform is {task.host.platform}") #Print Platform field of object




nr.run(task=randomtest) #Runs the function above

#ios_filter = nr.filter(platform="ios") #Will filter platform from ansible
#ios_filter.run(task=randomtest) #Run the function with the filter applied