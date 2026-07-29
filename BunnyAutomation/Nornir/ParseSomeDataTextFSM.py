from nornir import InitNornir
from nornir_scrapli.tasks import send_command
from nornir_utils.plugins.functions import print_result

nr = InitNornir(config_file="config.yaml")

def parse_text(task):
    version_results = task.run(task=send_command, command="show version") #"command=" Must use a valid ntc-template
    structrued_output = version_results.scrapli_response.textfsm_parse_output() #https://github.com/networktocode/ntc-templates/tree/master/ntc_templates/templates - Template location
    print(structrued_output)

results = nr.run(task=parse_text)
#print_result(results)