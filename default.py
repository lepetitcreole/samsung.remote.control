import xbmc
import xbmcgui
import xbmcaddon
import time
import sys
import colorsys
import os
import datetime
import math
import socket
import base64
import subprocess

NOSE = os.environ.get('NOSE', None)
DEBUG = False
connected = False

remote  = 'xbmc remote'
app     = 'xbmc'
tv      = 'UE40D6500'

if not NOSE:
  import xbmc
  import xbmcaddon

__icon__       = os.path.join(xbmcaddon.Addon().getAddonInfo('path'),"icon.png")

def notify(title, msg=""):
 if not NOSE:
   global __icon__
   xbmc.executebuiltin("XBMC.Notification(%s, %s, 3, %s)" % (title, msg, __icon__))
   
def logger(log):
   if DEBUG:
      xbmc.log("[DEBUG] Samsung TV : " + log)
        
def start_autodisover():
  notify("Samsung TV", "Discovery in progress...")
  
  remote_mac_address = ""
  remote_ip_address = ""
  remote_ip_address = subprocess.check_output("ifconfig eth0 | grep 'inet adr' | cut -d ':' -f 2 | cut -d ' ' -f 1", shell=True)
  remote_mac_address = subprocess.check_output("ifconfig eth0 | grep -Eo '([[:xdigit:]]{1,2}[:-]){5}[[:xdigit:]]{1,2}' | tr ':' '-'", shell=True)
  if remote_ip_address == "":
      remote_ip_address = subprocess.check_output("ifconfig wlan0 | grep 'inet adr' | cut -d ':' -f 2 | cut -d ' ' -f 1", shell=True)
      remote_mac_address = subprocess.check_output("ifconfig wlan0 | grep -Eo '([[:xdigit:]]{1,2}[:-]){5}[[:xdigit:]]{1,2}' | tr ':' '-'", shell=True)
  if remote_ip_address == "":
      notify("Samsung TV", "Remote IP address not found")
      xbmc.log("[DEBUG] Samsung TV : Remote IP address not found")
      sys.exit(0)
  xbmcaddon.Addon().setSetting("remote_ip", str(remote_ip_address))
  xbmc.log("[DEBUG] Samsung TV : " + remote_ip_address)
  xbmc.log("[DEBUG] Samsung TV : " + remote_mac_address)
  if remote_mac_address == "":
      notify("Samsung TV", "Remote MAC address not found")
  else:
      remote_mac_address = remote_mac_address.splitlines()[0]
      xbmcaddon.Addon().setSetting("remote_mac_address", str(remote_mac_address))
      notify("Samsung TV", remote_mac_address)
  
  tv_ip = ""
  port = 1900
  ip = "239.255.255.250"
  address = (ip, port)
  data = ('M-SEARCH * HTTP/1.1\r\n' +
'ST: urn:schemas-upnp-org:device:MediaRenderer:1\r\n' +
'MX: 3\r\n' +
'MAN: "ssdp:discover"\r\n' +
'HOST: 239.255.255.250:1900\r\n\r\n') 
  client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  
  num_retransmits = 0
  while(num_retransmits < 10) and tv_ip == "":
      num_retransmits += 1
      client_socket.sendto(data, address)
      recv_data, addr = client_socket.recvfrom(2048)
      xbmc.log("[DEBUG] Samsung TV : " + recv_data)
      if "dmr" in recv_data and "SamsungMRDesc.xml" in recv_data:
        tv_ip = recv_data.split("LOCATION: http://")[1].split(":")[0]
        xbmcaddon.Addon().setSetting("tv_ip", tv_ip)
      time.sleep(1)
  xbmc.log("[DEBUG] Samsung TV : " + tv_ip)    
  if tv_ip == "":
      notify("Samsung TV", "Not found")
  else:
      notify("Samsung TV", tv_ip)
  return tv_ip
  
class Samsung:
   
  def readxml(self):
    global NOSE
    global DEBUG
    
    self.tv_ip                   =        xbmcaddon.Addon().getSetting("tv_ip")
    self.remote_ip               =        xbmcaddon.Addon().getSetting("remote_ip")
    self.remote_mac_address      =        xbmcaddon.Addon().getSetting("remote_mac_address")
    self.switchToHDMI_boot       =        xbmcaddon.Addon().getSetting("switchToHDMI_boot") == "true"
    self.switchToTV_shutdown     =        xbmcaddon.Addon().getSetting("switchToTV_shutdown") == "true"
    self.starting_delay          =        xbmcaddon.Addon().getSetting("starting_delay")
    self.disable_notifications   =        xbmcaddon.Addon().getSetting("disable_notifications") == "true"
    self.debug                   =        xbmcaddon.Addon().getSetting("debug") == "true"
    
    if self.disable_notifications:
      NOSE = True
    if self.debug:
      DEBUG = True  

  def push(self, key):
    new = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    new.connect((self.tv_ip, 55000))
    msg = chr(0x64) + chr(0x00) +\
          chr(len(base64.b64encode(self.remote_ip)))    + chr(0x00) + base64.b64encode(self.remote_ip) +\
          chr(len(base64.b64encode(self.remote_mac_address)))    + chr(0x00) + base64.b64encode(self.remote_mac_address) +\
          chr(len(base64.b64encode(remote))) + chr(0x00) + base64.b64encode(remote)
    pkt = chr(0x00) +\
          chr(len(app)) + chr(0x00) + app +\
          chr(len(msg)) + chr(0x00) + msg
    new.send(pkt)
    msg = chr(0x00) + chr(0x00) + chr(0x00) +\
          chr(len(base64.b64encode(key))) + chr(0x00) + base64.b64encode(key)
    pkt = chr(0x00) +\
          chr(len(tv))  + chr(0x00) + tv +\
          chr(len(msg)) + chr(0x00) + msg
    new.send(pkt)
    new.close()
    xbmc.sleep(1000)
   
  def setInput(self, input):
    str1 = '%s%s' % ("KEY_", input)
    logger(str1)
    self.push(str1)
    str2 = "Input : " + input
    notify("Samsung TV", str2)
    logsStr = "Set input : " + input
    logger(logsStr)
    xbmc.sleep(1000)
  
  def testConnection(self):
   global connected
   new = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
   try:
      new.connect((self.tv_ip, 55000)) 
   except socket.error:
      notify("Samsung TV", "Not connected")
      connected = False
      logger("Test connection failed")
   else:
      new.close()
      connected = True
      notify("Samsung TV", "Connected")
      logger("Test connection success")
      xbmc.sleep(1000)

if len(sys.argv) == 2:
    args = sys.argv[1]    
    if sys.argv[1] == "start_discover":
      start_autodisover()
      sys.exit(0)

samsung = Samsung()      
samsung.readxml()

xbmc.sleep(int(samsung.starting_delay)*1000)

if samsung.tv_ip == "":
	notify("Samsung TV", "Not configured yet")
	sys.exit(0)
samsung.testConnection()
if connected:
   if samsung.switchToHDMI_boot:
      samsung.setInput("HDMI")

while not xbmc.abortRequested:
   xbmc.sleep(500)

samsung.readxml()
samsung.testConnection()
if connected:
   if samsung.switchToTV_shutdown:
      samsung.setInput("TV")
