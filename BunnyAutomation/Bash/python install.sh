"""This will create a virtual envorniment and download tools to get started on Network Automation"""

"""This section is for Linux or MacOS install."""
##############LINUX################
# sudo apt update #Linux
# sudo apt install python3 #Linux
###################################
##############MacOS################
# /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
# brew install python3
###################################

# cd ~ 
# mkdir MyPythonVirtualEnv
# cd MyPythonVirtualEnv
python3 -m venv .python_venv #Can re-name your env here
cd .python_venv
source bin/activate

python3 -m pip install netmiko #Paramiko on Easy mode
python3 -m pip install requests #Make API calls and work with the responses
python3 -m pip install napalm #Network Automation API used to simplify Network Automation Processes
python3 -m pip install NCClient #Work with Netconf to pass configurations of Network Devices
python3 -m pip install Genie #Allows for backups and configuration comparison of previous backups/current config for troubleshooting.
python3 -m pip install pyats #Cisco pyATS for taking operational snapshots of infrastructure