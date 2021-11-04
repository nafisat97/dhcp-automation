"""
    TC:1.1 - Basic Subscriber Bind Confirmation
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    This test is to verify whether a subscriber or set of subscribers are bound on an RE.

    Test Steps:
        Step 1: Use existing subscriber accounts in WSIR
        Step 2: Create DHCP device on Spirent TestCenter (STC)
        Step 3: Start the subscriber(s) on STC
        Step 4: Execute 'show service active-subscriber' command on 7750
    
    Result:
        Pass if list of sessions are outputted from Step 4
        Fail otherwise
"""

__author__ = "Nafisa Tabassum"
__version__ = "1.0.0"

import os
import unittest
import re
import HtmlTestRunner
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


class TestSubscriberBind(unittest.TestCase):
    def setUp(self):
        self.stc = StcPython()
        self.project = self.stc.get("system1", "children-project")
        resultdict = self.stc.perform(
            "CreateLogicalPorts",
            ParentList=self.project,
            CreateClassId="port",
            PhyClassName="Ethernet10GigFiber",
        )
        self.port1 = resultdict["ReturnList"]
        self.stc.config(self.port1, location=f"//{chassis_ip}/{port}")

    def test_single_sub_bind(self):
        # Create DHCP device on port
        resultdict = self.stc.perform(
            "DeviceCreate",
            ParentList=self.project,
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

    def test_hundred_sub_bind(self):
        # Create DHCP device on port
        resultdict = self.stc.perform(
            "DeviceCreate",
            ParentList=self.project,
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

    def test_thousand_sub_bind(self):
        # Create DHCP device on port
        resultdict = self.stc.perform(
            "DeviceCreate",
            ParentList=self.project,
            CreateCount=1,
            DeviceCount=1000,
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
            CircuitId="NAFISA-TEST 1/1/1/@x(122,1122)",
            EnableCircuitId=True,
        )
        self.stc.perform("AttachPorts")
        self.stc.apply()

        accounts = []
        for i in range(122, 1122):
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
            sorted_sublines = sorted(sublines, key=lambda x: int(x[21:]))

        self.assertListEqual(accounts, sorted_sublines)

    def tearDown(self):
        self.stc.perform("Dhcpv4Release", blockList=self.dhcp_block)
        self.stc.perform("Dhcpv4ReleaseWait", ObjectList=self.port1, WaitTime=100)
        if self.stc.get(self.dhcp_block, "BlockState") != "IDLE":
            exit()


if __name__ == "__main__":
    unittest.main(testRunner=HtmlTestRunner.HTMLTestRunner())
