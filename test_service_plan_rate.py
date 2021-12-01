"""
    TC:QOS_1 - Egress Traffic Queueing/Shaping
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    This test is for sending best effort (BE) towards subscriber

    Test Steps:
        1. Use existing sub in WSIR
        2. Create DHCP device on access port in Spirent TestCenter (STC)
        3. Create Traffic-only device in STC
        4. Create bound streamblock in STC from network to access port
        5. Start traffic generator
    
    Result:
        Pass if actual bitrate is within +/- 10% of expected bitrate
        Fail otherwise
"""

import os
import sys
import math
import unittest

import HtmlTestRunner

from SpirentSLC import SLC

# STC session authentication
server_ip = "127.0.0.1"
session_name = "test"

os.environ["STC_REST_API"] = "1"
os.environ["STC_SERVER_ADDRESS"] = server_ip
os.environ["STC_SERVER_PORT"] = "8888"
os.environ["STC_SESSION_NAME"] = session_name
os.environ["STC_SESSION_TERMINATE_ON_DISCONNECT"] = "True"
os.environ["EXISTING_SESSION"] = "kill"

from stcrestclient.stcpythonrest import StcPythonRest as StcPython

# Spirent Chassis and port details
chassis_ip = "172.25.205.185"
port1 = "11/2"
port2 = "2/4"


class TestEgressTrafficQueueing(unittest.TestCase):
    def setUp(self) -> None:
        """Create network and access ports, set up dhcp client, create streamblock"""
        self.stc = StcPython()
        self.project = self.stc.get("system1", "children-project")

        # Create access and network port
        self.access_port = self.stc.create(
            "port", under=self.project, location=f"//{chassis_ip}/{port1}"
        )
        self.network_port = self.stc.create(
            "port", under=self.project, location=f"//{chassis_ip}/{port2}"
        )

        # Create DHCP device on access port
        resultdict = self.stc.perform(
            "DeviceCreate",
            ParentList=self.project,
            CreateCount=1,
            DeviceCount=1,
            DeviceType="Host",
            IfStack="Ipv4If VlanIf EthIIIf",
            IfCount="1 1 1",
            Port=self.access_port,
        )
        self.dhcp_device = resultdict["ReturnList"]
        self.stc.config(self.dhcp_device, EnablePingResponse=True)
        self.dhcpinterface = self.stc.get(self.dhcp_device, "primaryif")
        self.stc.config(self.dhcpinterface, Gateway="10.158.0.1", PrefixLength=18)
        dhcp_enable = self.stc.perform(
            "ProtocolCreate",
            CreateClassId="Dhcpv4BlockConfig",
            ParentList=self.dhcp_device,
            UsesIfList=self.dhcpinterface,
        )
        self.dhcp_block = dhcp_enable["ReturnList"]
        self.stc.config(
            self.dhcp_block, CircuitId="NAFISA-TEST 1/1/1/20", EnableCircuitId=True
        )

        # Create traffic only device on network port
        resultdict = self.stc.perform(
            "DeviceCreate",
            ParentList=self.project,
            CreateCount=1,
            DeviceCount=1,
            DeviceType="Host",
            IfStack="Ipv4If EthIIIf",
            IfCount="1 1",
            Port=self.network_port,
        )
        self.static_device = resultdict["ReturnList"]
        self.stc.config(self.static_device, EnablePingResponse=True)
        self.staticinterface = self.stc.get(self.static_device, "primaryif")
        self.stc.config(
            self.staticinterface,
            Address="10.157.3.252",
            Gateway="10.157.3.253",
            PrefixLength=29,
        )

        # Bound streamblock creation from port2 (network) to port1 (dhcp client)
        self.streamblock1 = self.stc.create(
            "StreamBlock",
            under=self.network_port,
            srcbinding=self.staticinterface,
            dstbinding=self.dhcpinterface,
            Name="static2dhcp",
        )

        # Subscribe to stream results
        self.stc.perform(
            "ResultsSubscribe",
            Parent=self.project,
            ConfigType="StreamBlock",
            ResultType="TxStreamResults",
            ViewAttributeList="BitRate",
        )

        self.stc.perform(
            "ResultsSubscribe",
            Parent=self.project,
            ConfigType="StreamBlock",
            ResultType="RxStreamSummaryResults",
            ViewAttributeList="BitRate",
        )

    def test_undersubscription(self):
        # Set lower traffic load on network port
        self.stc.config(
            f"{self.network_port}.generator.generatorconfig",
            FixedLoad=10,
            LoadUnit="MEGABITS_PER_SECOND",
        )

        self.stc.perform("AttachPorts")
        self.stc.apply()

        self.stc.perform("Dhcpv4Bind", blockList=self.dhcp_block)
        self.stc.perform("Dhcpv4BindWait", ObjectList=self.access_port, WaitTime=100)

        # The streamblockupdate is always required for bound streamblocks.
        self.stc.perform(
            "StreamBlockUpdate",
            StreamBlock=self.streamblock1,
        )
        # Resolve ips
        self.stc.perform(
            "ArpNdStartOnAllStreamBlocks",
            portList=[self.access_port, self.network_port],
        )

        self.stc.perform("StreamBlockStart", StreamBlockList=self.streamblock1)
        self.stc.sleep(20)

        results = self.stc.get(self.streamblock1, "resultchild-Targets").split()
        tx = float(self.stc.get(results[0])["BitRate"]) / (10 ** 6)
        rx = float(self.stc.get(results[1])["BitRate"]) / (10 ** 6)

        self.assertTrue(
            math.isclose(rx, tx, rel_tol=0.10), f"Sent {tx} Mbps. Received {rx} Mbps"
        )

    def test_fullsubscription(self):
        # Set similar traffic load on network port
        self.stc.config(
            f"{self.network_port}.generator.generatorconfig",
            FixedLoad=15,
            LoadUnit="MEGABITS_PER_SECOND",
        )

        self.stc.perform("AttachPorts")
        self.stc.apply()

        self.stc.perform("Dhcpv4Bind", blockList=self.dhcp_block)
        self.stc.perform("Dhcpv4BindWait", ObjectList=self.access_port, WaitTime=100)

        # The streamblockupdate is always required for bound streamblocks.
        self.stc.perform(
            "StreamBlockUpdate",
            StreamBlock=self.streamblock1,
        )
        # Resolve ips
        self.stc.perform(
            "ArpNdStartOnAllStreamBlocks",
            portList=[self.access_port, self.network_port],
        )

        self.stc.perform("StreamBlockStart", StreamBlockList=self.streamblock1)
        self.stc.sleep(20)

        results = self.stc.get(self.streamblock1, "resultchild-Targets").split()
        tx = float(self.stc.get(results[0])["BitRate"]) / (10 ** 6)
        rx = float(self.stc.get(results[1])["BitRate"]) / (10 ** 6)

        self.assertTrue(
            math.isclose(rx, tx, rel_tol=0.10), f"Sent {tx} Mbps. Received {rx} Mbps"
        )

    def test_oversubscription(self):
        # Set higher traffic load on network port
        self.stc.config(
            f"{self.network_port}.generator.generatorconfig",
            FixedLoad=25,
            LoadUnit="MEGABITS_PER_SECOND",
        )

        self.stc.perform("AttachPorts")
        self.stc.apply()

        self.stc.perform("Dhcpv4Bind", blockList=self.dhcp_block)
        self.stc.perform("Dhcpv4BindWait", ObjectList=self.access_port, WaitTime=100)

        # The streamblockupdate is always required for bound streamblocks.
        self.stc.perform(
            "StreamBlockUpdate",
            StreamBlock=self.streamblock1,
        )
        # Resolve ips
        self.stc.perform(
            "ArpNdStartOnAllStreamBlocks",
            portList=[self.access_port, self.network_port],
        )

        self.stc.perform("StreamBlockStart", StreamBlockList=self.streamblock1)
        self.stc.sleep(20)

        results = self.stc.get(self.streamblock1, "resultchild-Targets").split()
        tx = float(self.stc.get(results[0])["BitRate"]) / (10 ** 6)
        rx = float(self.stc.get(results[1])["BitRate"]) / (10 ** 6)

        self.assertTrue(
            math.isclose(rx, 15.0, rel_tol=0.10), f"Sent {tx} Mbps. Received {rx} Mbps"
        )

    def tearDown(self) -> None:
        """Stop traffic and release dhcp client"""
        self.stc.perform("GeneratorStop")

        self.stc.perform("Dhcpv4Release", blockList=self.dhcp_block)
        self.stc.perform("Dhcpv4ReleaseWait", ObjectList=self.access_port, WaitTime=100)
        if self.stc.get(self.dhcp_block, "BlockState") != "IDLE":
            sys.exit(1)

        self.stc.delete(self.project)
        self.stc._end_session()


if __name__ == "__main__":
    template_args = {"custom_test_case_name": "Egress Traffic Queueing/Shaping"}
    unittest.main(
        testRunner=HtmlTestRunner.HTMLTestRunner(
            template=f"{os.getcwd()}\\report_template.html", template_args=template_args
        )
    )
