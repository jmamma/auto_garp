#!/usr/bin/python

# Name: auto_garp.py
# Author: Justin Mammarella
# Date: November 2017
# Description: Generate gratuitious ARP for newly launched instances.

import os
import time
import subprocess
import argparse
import re
from datetime import datetime

def cmdline(command):
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
    out, err = proc.communicate()
    proc.wait()
    return (out.splitlines(), proc.returncode)

def main():
    macs = []
    # Get initial list of mac addresses
    (o,e) = cmdline("ifconfig | grep tap | grep HWaddr")
    for line in o:
        if line is not None:
          if "fe" in line:
              macs.append(line.split(" ")[5])

    #Periodically scan for new tap interfaces
    while True:
      time.sleep(10)
      (o,e) = cmdline("ifconfig | grep tap | grep HWaddr")
      for line in o:
        if line is not None:
          if "fe" in line:
             tap_mac = line.split(" ")[5]
             if tap_mac not in macs: 
                 #We've found a new interface with a MAC not in our mac array
                 #Change tap interface mac to instance mac
                 instance_mac = "FA:" + ':'.join(tap_mac.upper().split(':')[1:])
                 #Get interface prefix as used by neutron in iptables
                 interface = line.split(" ")[0].split("-")[0].strip("tap")
                 #Use iptables-save to find the instance_ip
                 (a,e) = cmdline("iptables-save | grep neutron-linuxbri-s" + interface + " | grep " + instance_mac)
                 instance_ip = None
                 if a:
                   #store the instance mac in memory so that we don't send additional garps.
                   macs.append(tap_mac)
                   if instance_mac in a[0]:
                      #get the instance ip
                      instance_ip = a[0].split(" ")[3].split("/")[0]
                   if instance_ip is not None:
                      #if we have both the mac and IP we can proceed in sending the garp
                      print "Sending GARP " + instance_mac + " " + instance_ip
                      cmdline("echo '" + str(datetime.now()) + ": Sending GARP for " + instance_mac + " " + instance_ip + "' >> /var/log/autogarp.log")
                      print "arping -c 3 -U -b " + instance_ip + " -I bond0 -A -S " + instance_ip + " -s " + instance_mac
                      (b,e) = cmdline("arping -c 3 -U -b " + instance_ip + " -I bond0 -A -S " + instance_ip + " -s " + instance_mac)
                   else: 
                      print "Error obtaining IP"

if __name__ == "__main__":
    main()
