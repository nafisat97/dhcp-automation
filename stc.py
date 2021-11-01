import matplotlib.pyplot as plt
import numpy as np
import polling
import os


use_rest_api = True
server_ip = "127.0.0.1"
session_name = "test"

if use_rest_api:
    os.environ["STC_REST_API"] = "1"
    os.environ["STC_SERVER_ADDRESS"] = server_ip
    os.environ["STC_SERVER_PORT"] = "8888"
    os.environ["STC_SESSION_NAME"] = session_name
    os.environ["STC_SESSION_TERMINATE_ON_DISCONNECT"] = "False"
    os.environ["EXISTING_SESSION"] = "kill"

    from stcrestclient.stcpythonrest import StcPythonRest as StcPython


def main():
    # Spirent Chassis and port details
    chassis_ip = "172.25.205.185"
    port = "11/2"

    stc = StcPython()
    project = stc.get("system1", "children-project")
    resultdict = stc.perform(
        "CreateLogicalPorts",
        ParentList=project,
        CreateClassId="port",
        PhyClassName="Ethernet10GigFiber",
    )

    port1 = resultdict["ReturnList"]
    stc.config(port1, location=f"//{chassis_ip}/{port}")

    # Create DHCP device on port
    resultdict = stc.perform(
        "DeviceCreate",
        ParentList=project,
        CreateCount=1,
        DeviceCount=1000,
        DeviceType="Host",
        IfStack="Ipv4If VlanIf EthIIIf",
        IfCount="1 1 1",
        port=port1,
    )

    dhcp_device = resultdict["ReturnList"]

    dhcp_enable = stc.perform(
        "ProtocolCreate",
        CreateClassId="Dhcpv4BlockConfig",
        ParentList=dhcp_device,
        UsesIfList=stc.get(dhcp_device, "primaryif"),
    )

    dhcp_block = dhcp_enable["ReturnList"]

    stc.config(
        dhcp_block, CircuitId="NAFISA-TEST 1/1/1/@x(122,1122)", EnableCircuitId=True
    )

    print("Connecting to chassis")
    stc.perform("AttachPorts")
    stc.apply()

    print("Start DHCP bind")
    stc.perform("Dhcpv4Bind", blockList=dhcp_block)

    print("Wait for DHCP bind")
    stc.perform("Dhcpv4BindWait", ObjectList=port1, WaitTime=100)

    if stc.get(dhcp_block, "BlockState") != "BOUND":
        exit()

    stc.perform("Dhcpv4Release", blockList=dhcp_block)
    stc.perform("Dhcpv4ReleaseWait", ObjectList=port1, WaitTime=100)

    results = stc.get(dhcp_block, "children-dhcpv4blockresults")
    print(f"Bind rate {stc.get(results, 'BindRate')} sessions/sec")


if __name__ == "__main__":
    main()
