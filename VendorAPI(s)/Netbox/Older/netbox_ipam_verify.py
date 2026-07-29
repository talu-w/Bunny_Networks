import requests
import requests
import subprocess
import json
import ipaddress

########### Credientals #################

with open("/Your/Path/Here/api_key.txt") as api_file:
    api_key - api_file.readlines()[0].strip() #Uses PWD to retrieve token. Must be file txt
	
#api_key = 'Token ' #Input token manually here

#######################

############## API / HEADER Info ###############

nbox_api = f'https://nbox.url.here.com/api'

header = {
     'Content-Type': 'application/json',
	 'Authorization': api_key }


##################################################
##################### Pings Function ############# 


def ping_device(ip):
    try:
        output = subprocess.check_output(["ping", "-c", "1", ip], universal_newlines=True)
        if "1 packets transmitted, 1 received" in output:
            return True # IP is in use (responded to ping)
        else:
            return False # IP is not in use
    except subprocess.CalledProcessError:
        return False # IP is not in use (ping failed)
		
#########################################################
################# update function #######################


# Function to update the IP address status to 'active'

def update_ip_status_in_netbox(ip_address):

    vrf = vrf_input
    netbox_ipam = f'{nbox_api}ipam/ip-addresses/'
    data = json.dumps({ 
	      "address": f"{ip_address}/24,
		  "vrf": {"name":f"{vrf},
	      "status" : "active"}
          )

    check_url = f"{nbox_api}/api/ipam/ip-addresses/?address={ip_address}"
    response = requests.get(check_url, headers=HEADERS)
    
    if response.status_code == 200 and response.json()['count'] > 0:
        # IP already exists in NetBox, update it
        ip_id = response.json()['results'][0]['id']
        update_url = f"{nbox_api}/api/ipam/ip-addresses/{ip_id}/"
        update_response = requests.patch(update_url, headers=HEADERS, json=data)
		
        if update_response.status_code == 200:
            print(f"Address is already active.")
        else:
            print(f"Failed to update IP {ip_address}: {update_response.text}")
    else:
        # IP doesn't exist in NetBox, create it
        create_response = requests.post(url, headers=HEADERS, json=data)
        if create_response.status_code == 201:
            print(f"Successfully created and marked {ip_address} as 'Active' in NetBox.")
        else:
            print(f"Failed to create IP {ip_address}: {create_response.text}")
			
###############################################################################################

###################### DELETE ########################################

def update_nbox_delete(ip_address2):
    netbox_ipam = f'{nbox_api}ipam/ip-addresses/"
    check_url = f"{nbox_api}/api/ipam/ip-addresses/?address={ip_address}"	

    response = requests.get(check_url, headers=HEADERS)
    
    if response.status_code == 200 and response.json()['count'] > 0:
        ip_id = response.json()['results'][0]['id']
        update_url = f"{nbox_api}/api/ipam/ip-addresses/{ip_id}/"
        update_response = requests.request("DELETE", update_url, headers=HEADERS, json=data)
		
        if update_response.status_code == 204:
            print(f"Address is not in use and has been deleted.")
        else:
            print(f"Failed to update IP object: {update_response.text}")
    else:
        print(f"Ip is not in use and is listed as Inactive") 
################################################################################################
##################### Subnet Ping ###########################################################			
			
def ping_subnet_and_update_netbox(subnet):
    network = ipaddress.ip_network(subnet)

    for ip in network.hosts(): 
        ip_str = str(ip)
        print(f"Pinging IP: {ip_str}...")
        
        # Ping the IP address
        if ping_device(ip_str):
            print(f"IP {ip_str} is in use on the network.")
            update_ip_status_in_netbox(ip_str) 
        else:
            print(f"IP {ip_str} is not in use.")
			update_nbox_delete
			
			
if __name__ == "__main__":