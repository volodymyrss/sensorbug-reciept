#!/usr/bin/env python3
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# bscan.py - Simple bluetooth LE scanner and data extractor

from bluepy.btle import Scanner, DefaultDelegate
import time
import struct
import json


from collections import defaultdict

#Enter the MAC address of the sensor from the lescan
SENSORS = {
            "ec:fe:7e:10:b7:e4": {'name': 'SensorBug1', 'data': None},
            "ec:fe:7e:10:a1:ab": {'name': 'SensorBug2', 'data': None},
        }

class DecodeErrorException(Exception):
     def __init__(self, value):
         self.value = value
     def __str__(self):
         return repr(self.value)

class ScanDelegate(DefaultDelegate):
    def __init__(self):
        DefaultDelegate.__init__(self)

    def handleDiscovery(self, dev, isNewDev, isNewData):
        pass
        #known_dev[dev.addr]+=1

        if isNewDev:
            print("Discovered device", dev.addr)
        elif isNewData:
            print("Received new data from", dev.addr)

scanner = Scanner().withDelegate(ScanDelegate())


def parse_dev(dev):
    CurrentDevAddr = dev.addr
    CurrentDevLoc = SENSORS[dev.addr]['name']
    for (adtype, desc, value) in dev.getScanData():
        print("  %s = %s" % (desc, value))
        if (desc == "Manufacturer"):
            ManuData = value

    if (ManuData == ""):
        print("No data received, end decoding")
        return

    for i, j in zip (ManuData[::2], ManuData[1::2]):
        ManuDataHex.append(int(i+j, 16))

    #Start decoding the raw Manufacturer data
    if ((ManuDataHex[0] == 0x85) and (ManuDataHex[1] == 0x00)):
        print("Header byte 0x0085 found")
    else:
        print("Header byte 0x0085 not found, decoding stop")
        return

    #Skip Major/Minor 
    #Index 5 is 0x3c, indicate battery level and config #
    if (ManuDataHex[4] == 0x3c):
        BatteryLevel = ManuDataHex[5]
        ConfigCounter = ManuDataHex[6]

    idx = 7
    #print "TotalLen: " + str(len(ManuDataHex))
    while (idx < len(ManuDataHex)):
        #print "Idx: " + str(idx)
        #print "Data: " + hex(ManuDataHex[idx]) 
        
        if (ManuDataHex[idx] == 0x41):
            #Accerometer data
            idx += 1
            AcceleroType = ManuDataHex[idx]
            AcceleroData = ManuDataHex[idx+1]
            idx += 2
        elif (ManuDataHex[idx] == 0x43):
            #Temperature data
            idx += 1
            TempData = ManuDataHex[idx]
            TempData += ManuDataHex[idx+1] * 0x100
            TempData = TempData * 0.0625
            idx += 2
        else:
            idx += 1

    print("Device Address: " + CurrentDevAddr) 
    print("rssi:", dev.rssi)
    print("Device Location: " + CurrentDevLoc) 
    print("Battery Level: " + str(BatteryLevel) + "%")
    print("Config Counter: " + str(ConfigCounter))
    #print("Accelero Data: " + hex(AcceleroType) + " " + hex(AcceleroData))
    print("Temp Data: " + str(TempData))

    data['addr'] = CurrentDevAddr
    data['rssi'] = dev.rssi
    data['name'] = CurrentDevLoc
    data['temperature'] = TempData

    return data

def report(d):
    print(json.dumps({**{'origin': 'bscan'}, **d}))

ManuDataHex = []
ReadLoop = True
try:
    all_devices={}

    while (ReadLoop):

        while True:
            try:
                devices = scanner.scan(2.0)
                break
            except Exception as e:
                print("failed", e)
                time.sleep(1)

        print("scan complete")
            
        ManuData = ""

        for dev in devices:
            data = {d.lower().replace(" ","-"):v for a,d,v in dev.getScanData()}
            data['rssi'] = dev.rssi

            all_devices[dev.addr] = data

            AcceleroData = 0 
            AcceleroType = 0 
            TempData = 0
            for saddr in SENSORS.keys():

                if (dev.addr == saddr):
                    print("Device %s (%s), RSSI=%d dB" % (dev.addr, dev.addrType, dev.rssi))
                
                    data.update(parse_dev(dev) or {})
                    SENSORS[saddr]['data'] = data
        


        if all([v['data'] is not None for v in SENSORS.values()]):
            ReadLoop = False
        
    for k,v in {**SENSORS, **all_devices}.items():
        report({'device':k, 'bdata': v})

    for k,v in SENSORS.items():
        report({'devnum':int(v['name'][-1:]), 'internal temperature': v['data']['temperature']})
    
    
    
except DecodeErrorException:
    pass


print("done")
