###Script piece that will ping a device and can modify true/false variable based on the desired outcome of the response

import subprocess

def ping_device(host):
    try:
        output = subprocess.check_output(["ping", "-c", "1", host], universal_newlines=True)
        if "1 packets transmitted, 1 received" in output:
            return True
        else:
            return False
    except subprocess.CalledProcessError:
        return False

def main():
    host = input(f"Input IP here: ")
    if ping_device(host):
        print(f"IP {host} is taken. Please choose another")
    else: 
        print(f"IP {host} is avaiable.")

if __name__ == "__main__":
    main()