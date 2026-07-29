import paramiko
import time


ip = ''
username = ''
password = ''
enable_password = '' #Leave blank if enable not required.



def send_command(channel, command, delay=2):
    """
    Sends a command through the Paramiko channel and returns the output.
    """
    buffer = ''
    channel.send(command + '\n')
    time.sleep(delay)
    while channel.recv_ready():
        buffer += channel.recv(9999).decode('utf-8')
        time.sleep(0.2)
    return buffer

def get_cisco_outputs(ip, username, password, enable_password=None):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ip, username=username, password=password, look_for_keys=False, allow_agent=False)

    channel = ssh.invoke_shell()
    time.sleep(1)
    channel.recv(9999)  # Clear the buffer

    # Optional: enter enable mode
    if enable_password:
        send_command(channel, "enable")
        send_command(channel, enable_password)

    send_command(channel, "terminal length 0")

    # Send and capture outputs
    show_version_output = send_command(channel, "show version")
    show_run_output = send_command(channel, "show run", delay=5)

    # Cleanup
    channel.close()
    ssh.close()

    return show_version_output, show_run_output



show_version, show_run = get_cisco_outputs(ip, username, password, enable_password)

# Print out the results!
print("-" * 100 )
print(show_version)
print("*" * 100)
print(show_run)
print("-" * 100)