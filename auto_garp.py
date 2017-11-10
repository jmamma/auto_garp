#!/usr/bin/python

# Name: auto_garp.py
# Author: Justin Mammarella
# Date: November 2017
# Description: Generate gratuitious ARP for newly launched VMS.

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

def log(text):
    cmdline("echo '" + str(datetime.now()) + ": " + text + "' >> /var/log/autogarp.log")

def my_exit(text):
    log(text)
    sys.exit(text)

def main():
    log("AutoGARP starting")
    macs = []
    send_interface = None
    (b,e) = cmdline("brctl show | grep br | awk '{ print $1 }'")
    if b:
      send_interface = b[1].split(' ')[0]
      if "br" not in send_interface:
        my_exit("Unable to detect bridge interface")
    else:
      my_exit("Unable to detect bridge interface")
    # Get initial list of mac addresses
    print send_interface
    (o,e) = cmdline("ifconfig | grep tap | grep HWaddr")
    for line in o:
      if line is not None:
        if "fe" in line:
          macs.append(line.split(" ")[5])

    #Periodically scan for new tap interfaces
    while True:
      time.sleep(20)
      (o,e) = cmdline("ifconfig | grep tap | grep HWaddr")
      for line in o:
        if line is not None:
            if "HWaddr fe:16" in line:
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
                      log(str(datetime.now()) + ": Sending GARP for " + instance_mac + " " + instance_ip)
                      print "arping -c 3 -U -b " + instance_ip + " -I " + send_interface + " -A -S " + instance_ip + " -s " + instance_mac
                      (b,e) = cmdline("arping -c 3 -U -b " + instance_ip + " -I " + send_interface + " -A -S " + instance_ip + " -s " + instance_mac)
                   else:
                      print "Error obtaining IP"

if __name__ == "__main__":
    main()
