from nornir import InitNornir
from nornir_scrapli.tasks import send_command
from nornir_utils.plugins.functions import print_result
import ipdb

nr = InitNornir(config_file="config.yaml")

'''Use's the Genie Parser. Tends to have wider coverage and more verbosity
   Created by Cisco and can be used with main line vendors'''

def parse_text(task):
    version_results = task.run(task=send_command, command="show ip interface") #"command=" Must use a valid ntc-template
    task.host["facts"] = version_results.scrapli_response.genie_parse_output() #https://pubhub.devnetcloud.com/media/genie-feature-browser/docs/#/parsers - Parsers location

results = nr.run(task=parse_text)
#print_result(results)
ipdb.set_trace()