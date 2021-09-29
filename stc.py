from stcrestclient import stchttp

import re
import io
import sys
import logging
import collections
import json
import time
import math
import random
import os
from datetime import datetime


def main():
    stc = stchttp.StcHttp(server="127.0.0.1", port="8888")
    stc.new_session("nafisa", "test", kill_existing=True)
    stc.join_session("test - nafisa")
    print(stc.system_info())

    config_file = "ex.xml"

    if not os.path.isfile(config_file):
        print("missing file: {}".format(config_file))
        sys.exit(1)

    # Spirent Chassis and port details
    chassis_ip = "172.25.205.185"
    port = "11/2"

    project = stc.create("project")
    port_handle = stc.create("port", under=project)
    stc.config(port_handle, location="//{}/{}".format(chassis_ip, port))

    deviceList = stc.create("emulateddevice", under=project, affiliatedPort=port_handle)
    dhcp_block = stc.create(
        "dhcpv4blockconfig",
        under=deviceList,
        CircuitId="NAFISA-TEST 1/1/1/20",
        EnableCircuitId="TRUE",
        EnableRelayAgent="FALSE",
    )
    print(stc.get(deviceList, "children"))

    # stc.upload(config_file)
    # data = stc.perform("LoadFromXml", filename=config_file)

    # hProject = stc.get("system1", "children-project")
    # portList = stc.get(hProject, "children-port")
    # deviceList = stc.get(hProject, "children-emulateddevice")
    # dhcp_block = stc.get(deviceList, "children-dhcpv4blockconfig")

    # stc.connect(chassis_ip)
    # stc.perform("reservePort", location="//{}/{}".format(chassis_ip, port))
    # stc.perform("setupPortMappings")

    # print("Attaching ports")
    # stc.perform("AttachPorts", portList=[port_handle], autoConnect="TRUE")
    # stc.apply()

    # stc.perform("Dhcpv4BindCommand", blockList=dhcp_block)
    # print("waiting for bind")
    # time.sleep(10)

    # stc.perform("Dhcpv4ReleaseCommand", blockList=dhcp_block)
    # time.sleep(10)

    stc.disconnect(chassis_ip)
    stc.delete(deviceList)
    stc.delete(port_handle)
    # stc.delete(portList)
    # stc.delete(hProject)


if __name__ == "__main__":
    main()
