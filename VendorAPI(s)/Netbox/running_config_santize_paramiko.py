import paramiko
import time
import requests
import json
from hashlib import md5
from getpass import getpass

netbox_url = f'https://yournetboxurlhere.com/api/'
netbox_token = 'Token goes here'
api_circuits = f'{netbox_url}circuits/'
api_core = f'{netbox_url}core/'
api_dcim = f'{netbox_url}dcim/'
api_extra = f'{netbox_url}extra/'
api_ipam = f'{netbox_url}ipam/'
api_users = f'{netbox_url}users/'

#####Session Parameters#####
s = requests.session()
s.headers.update({'Authorization':netbox_token})
s.headers.update({'Content-Type':'application/json'})


def start(username, password, ip_list):
    for ip_address in ip_list:
        ip = ip_address
        running_configuration = get_cisco_outputs(username, password, ip)
        sanitized_config = sanitize_config(running_configuration)
        netbox_switch_id, netbox_switch_name = collect_netbox_info(ip)
        config_id = push_config(sanitized_config, netbox_switch_name)
        attach_config_to_switch(netbox_switch_id, config_id)
        

def send_command(channel, command, delay =2):
    buffer = ''
    channel.send(command + '\n')
    time.sleep(delay)
    while channel.recv_ready():
        buffer += channel.recv(9999).decode('utf-8')
        time.sleep(0.2)
    return buffer

def get_cisco_outputs(ip, username, password):
    class _PkeyChild(paramiko.Pkey):
        def get_fingerprint_improved(self):  
            """
            Declares the use of MD5 is not for Security Purposes
            """
            return md5(self.asbytes(), usedforsecurity=False).digest()
        
    paramiko.Pkey.get_fingerprint = _PkeyChild.get_fingerprint_improved
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ip, username=username, password=password, look_for_keys=False, allow_agent=False)
    
    channel = ssh.invoke_shell()
    time.sleep(1)
    channel.recv(9999)
    
    send_command(channel, "terminal length 0")
    send_command(channel, '') #Will need a return
    config = send_command(channel, 'show run') #applies the command to variable
    
    channel.close()
    ssh.close()
    return sanitize_config

def sanitize_config(config_text):
        bad_words = [''] #Insert words here. Will match with the word found in config and remove the entire line
        sanitized_config = []
        for line in config_text.splitlines():
            if not any(bad_word in line for bad_word in bad_words):
                sanitize_config.append(line)
                newline_config = "\n".join(sanitize_config)
                continue
        return newline_config
    
def collect_netbox_info(ip):
    try:
        ipam_fetch = f'{api_ipam}ip-addresses/?address={ip}'
        collect_ipam = s.get(ipam_fetch)
        ipam_id = collect_ipam.json()['results'][0]['id']
        switch_url = f'{api_dcim}devices/?oob_ip_id={ipam_id}'
        switch_get = s.get(switch_url)
        switch_id = switch_get.json()['results'][0]['id']
        switch_name = switch_get.json()['results'][0]['name']
        return switch_id, switch_name
    except:
        print(f'{ip} has either not been associated with an Object in Netbox or has not been made')
                
def push_config(sanitized_config, switch_name):
    netbox_config_templates = f'{api_extra}config-templates/?name={switch_name}-config'
    netbox_config_templates_check = s.get(netbox_config_templates)
    config_template_url = f"{api_extra}config-templates/"
    config_data = json.dumps(
        {"name":f"{switch_name}-config",
        "description":f"This is a santized config for {switch_name}",
        "template_code": f'{sanitize_config}'}
        )       

    if netbox_config_templates_check.json()['count'] != 0:
        config_template_id = netbox_config_templates_check.json()['results'][0]['id']
        config_patch_url = f"{api_extra}config-templates/{config_template_id}/"
        s.patch(config_patch_url, config_data)
        return config_template_id
    else:
        post = s.post(config_template_url)
        config_template_id = post.json()['id']
        return config_template_id

def attach_config_to_switch(switch_id, config_id):
    data = json.dumps()({'config_template':f'{config_id}'})
    attach_url = f'{api_dcim}devices/{switch_id}/'
    attach_config = s.patch(attach_url, data)
    if attach_config.status_code == 200:print(f'{attach_config.json()['name']} has been updated.')
    else: 
        print(attach_config.status_code)
        print(attach_config.json())

if __name__ == "__main__":
    username = ""
    password = getpass('Please enter password:') #Getpass keeps text hidden
    ip_list = [''] #Enter IP addresses of devices
    start(username, password, ip_list)