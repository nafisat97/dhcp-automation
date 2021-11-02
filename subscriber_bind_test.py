"""Subscriber bind confirmations on RE01"""
import os
import unittest
import re
from SpirentSLC import SLC

# STC session authentication
server_ip = "127.0.0.1"
session_name = "test"

os.environ["STC_REST_API"] = "1"
os.environ["STC_SERVER_ADDRESS"] = server_ip
os.environ["STC_SERVER_PORT"] = "8888"
os.environ["STC_SESSION_NAME"] = session_name
os.environ["STC_SESSION_TERMINATE_ON_DISCONNECT"] = "False"
os.environ["EXISTING_SESSION"] = "kill"

from stcrestclient.stcpythonrest import StcPythonRest as StcPython

# Device authentication
re01 = {
    "ipAddress": "172.25.205.146",
    "user": "t970164",
    "password": "y1etIzac1o2T/OQekPq8Ew==",
}

# Spirent Chassis and port details
chassis_ip = "172.25.205.185"
port = "11/2"


# Utility methods
def slc_session():
    """Creates an iTest session to connect to a device"""
    slc = SLC.init(host="localhost:9005")
    s1 = slc.sessions.ssh.open(
        properties={
            **re01,
            "TerminalProperties": {
                "prompts": [
                    {
                        "prompt1": {"Content": "*B:EDTN-LAB-RE01#"},
                        "prompt2": {"Content": "Password:"},
                    }
                ]
            },
        }
    )
    return s1


class SingleSubTest(unittest.TestCase):
    def setUp(self) -> None:
        self.stc = StcPython()
        project = self.stc.get("system1", "children-project")
        resultdict = self.stc.perform(
            "CreateLogicalPorts",
            ParentList=project,
            CreateClassId="port",
            PhyClassName="Ethernet10GigFiber",
        )

        self.port1 = resultdict["ReturnList"]
        self.stc.config(self.port1, location=f"//{chassis_ip}/{port}")

        # Create DHCP device on port
        resultdict = self.stc.perform(
            "DeviceCreate",
            ParentList=project,
            CreateCount=1,
            DeviceCount=1,
            DeviceType="Host",
            IfStack="Ipv4If VlanIf EthIIIf",
            IfCount="1 1 1",
            port=self.port1,
        )

        self.dhcp_device = resultdict["ReturnList"]

        self.dhcp_enable = self.stc.perform(
            "ProtocolCreate",
            CreateClassId="Dhcpv4BlockConfig",
            ParentList=self.dhcp_device,
            UsesIfList=self.stc.get(self.dhcp_device, "primaryif"),
        )

        self.dhcp_block = self.dhcp_enable["ReturnList"]

        self.stc.config(
            self.dhcp_block, CircuitId="NAFISA-TEST 1/1/1/122", EnableCircuitId=True
        )

        self.stc.perform("AttachPorts")
        self.stc.apply()

    def tearDown(self) -> None:
        self.stc.perform("Dhcpv4Release", blockList=self.dhcp_block)
        self.stc.perform("Dhcpv4ReleaseWait", ObjectList=self.port1, WaitTime=100)
        if self.stc.get(self.dhcp_block, "BlockState") != "IDLE":
            exit()

    def test_single_sub_bind(self):
        self.stc.perform("Dhcpv4Bind", blockList=self.dhcp_block)
        self.stc.perform("Dhcpv4BindWait", ObjectList=self.port1, WaitTime=100)

        if self.stc.get(self.dhcp_block, "BlockState") == "BOUND":
            s1 = slc_session()
            s1.command("environment no more")
            response = s1.command(
                'show service active-subscribers detail | match "Subscriber sl_NAFISA-TEST/1/1/1/122"'
            )
            sublines = re.findall("sl_\S+", response.text)

        self.assertEqual(
            "sl_NAFISA-TEST/1/1/1/122",
            sublines[0],
            f"Subscriber {sublines[0]} is not bound",
        )


class HundredSubTest(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.stc = StcPython()
        project = self.stc.get("system1", "children-project")
        resultdict = self.stc.perform(
            "CreateLogicalPorts",
            ParentList=project,
            CreateClassId="port",
            PhyClassName="Ethernet10GigFiber",
        )

        self.port1 = resultdict["ReturnList"]
        self.stc.config(self.port1, location=f"//{chassis_ip}/{port}")

        # Create DHCP device on port
        resultdict = self.stc.perform(
            "DeviceCreate",
            ParentList=project,
            CreateCount=1,
            DeviceCount=100,
            DeviceType="Host",
            IfStack="Ipv4If VlanIf EthIIIf",
            IfCount="1 1 1",
            port=self.port1,
        )

        self.dhcp_device = resultdict["ReturnList"]

        self.dhcp_enable = self.stc.perform(
            "ProtocolCreate",
            CreateClassId="Dhcpv4BlockConfig",
            ParentList=self.dhcp_device,
            UsesIfList=self.stc.get(self.dhcp_device, "primaryif"),
        )

        self.dhcp_block = self.dhcp_enable["ReturnList"]

        self.stc.config(
            self.dhcp_block,
            CircuitId="NAFISA-TEST 1/1/1/@x(300,400)",
            EnableCircuitId=True,
        )

        self.stc.perform("AttachPorts")
        self.stc.apply()

    def tearDown(self) -> None:
        self.stc.perform("Dhcpv4Release", blockList=self.dhcp_block)
        self.stc.perform("Dhcpv4ReleaseWait", ObjectList=self.port1, WaitTime=100)
        if self.stc.get(self.dhcp_block, "BlockState") != "IDLE":
            exit()

    def test_hundred_sub_bind(self):
        # Simulates subs created in wsir
        accounts = []
        for i in range(300, 400):
            accounts.append(f"sl_NAFISA-TEST/1/1/1/{str(i)}")

        self.stc.perform("Dhcpv4Bind", blockList=self.dhcp_block)
        self.stc.perform("Dhcpv4BindWait", ObjectList=self.port1, WaitTime=100)

        if self.stc.get(self.dhcp_block, "BlockState") == "BOUND":
            s1 = slc_session()
            s1.command("environment no more")
            response = s1.command(
                'show service active-subscribers detail | match "Subscriber sl_NAFISA-TEST"'
            )
            sublines = re.findall("sl_\S+", response.text)

        self.assertListEqual(accounts, sublines)


if __name__ == "__main__":
    unittest.main()
