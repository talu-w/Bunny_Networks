from nornir import InitNornir
from rich import print as rprint

nr = InitNornir(config_file="config.yaml")

def randomtest(task):
    rprint(f"Hell, my name is {task.host}")
    rprint(f"My Ip Address/Hostname is {task.host.hostname}")
    rprint(f"My platform is {task.host.platform}")




nr.run(task=randomtest) #Runs the function above

#ios_filter = nr.filter(platform="ios") #Will filter platform from ansible
#ios_filter.run(task=randomtest) #Run the function with the filter applied