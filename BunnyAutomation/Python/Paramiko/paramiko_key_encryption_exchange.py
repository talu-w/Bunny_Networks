###Script piece that you can insert to leverage Paramiko connections in FIPS envorinments.

import paramiko
import time
from hashlib import md5

def get_cisco_outputs(ip, username, password):
    class _PkeyChild(paramiko.Pkey):
        def get_fingerprint_improved(self):  
            """
            Declares the use of MD5 is not for Security Purposes and updates the key.
            """
            return md5(self.asbytes(), usedforsecurity=False).digest()
        
    paramiko.Pkey.get_fingerprint = _PkeyChild.get_fingerprint_improved
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ip, username=username, password=password, look_for_keys=False, allow_agent=False)
    
    channel = ssh.invoke_shell()
    time.sleep(1)
    channel.recv(9999)