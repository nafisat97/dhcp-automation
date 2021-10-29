from tkinter import Toplevel
from stcrestclient import stchttp

import matplotlib.pyplot as plt
import numpy as np
import polling
from datetime import datetime


def main():
    stc = stchttp.StcHttp(server="127.0.0.1", port="8888")
    stc.new_session("nafisa", "test", kill_existing=True)
    stc.join_session("test - nafisa")

    # config_file = "ex.xml"

    # if not os.path.isfile(config_file):
    #     print("missing file: {}".format(config_file))
    #     sys.exit(1)

    # Spirent Chassis and port details
    chassis_ip = "172.25.205.185"
    port = "11/2"

    project = stc.create("project")
    port_handle = stc.create("port", under=project)
    stc.config(port_handle, location="//{}/{}".format(chassis_ip, port))

    deviceList = stc.create(
        "emulateddevice", under=project, affiliatedPort=port_handle, DeviceCount=1000
    )
    ethiiIf = stc.create("EthIIIf", under=deviceList)
    vlanIF = stc.create("VlanIf", under=deviceList, StackedOn=ethiiIf)
    ipv4If = stc.create("Ipv4If", under=deviceList, StackedOn=vlanIF)
    stc.config(deviceList, PrimaryIf=ipv4If, ToplevelIf=ipv4If)

    dhcp_block = stc.create(
        "dhcpv4blockconfig",
        under=deviceList,
        CircuitId="NAFISA-TEST 1/1/1/@x(122,1122)",
        EnableCircuitId="TRUE",
        EnableRelayAgent="FALSE",
        UsesIf=ipv4If,
    )

    # dhcp_results = stc.perform(
    #     "ResultsSubscribeCommand",
    #     parent=project,
    #     resultParent=port_handle,
    #     resultType="Dhcpv4BlockResults",
    #     configType="Dhcpv4BlockConfig",
    #     ViewAttributeList="BindRate",
    #     interval=1,
    # )

    # stc.upload(config_file)
    # data = stc.perform("LoadFromXml", filename=config_file)

    # hProject = stc.get("system1", "children-project")
    # portList = stc.get(hProject, "children-port")
    # deviceList = stc.get(hProject, "children-emulateddevice")
    # print(stc.get(deviceList, "children"))
    # dhcp_block = stc.get(deviceList, "children-dhcpv4blockconfig")

    sequencer = stc.create("sequencer", under="system1")
    bind = stc.create("Dhcpv4BindCommand", under=sequencer, BlockList=dhcp_block)
    bind_wait = stc.create(
        "Dhcpv4BindWaitCommand",
        under=sequencer,
        ObjectList=deviceList,
        WaitTime=100.0,
    )
    release_wait = stc.create(
        "Dhcpv4ReleaseWaitCommand",
        under=sequencer,
        ObjectList=deviceList,
        WaitTime=100.0,
    )
    release = stc.create("Dhcpv4ReleaseCommand", under=sequencer, blockList=dhcp_block)

    stc.perform(
        "SequencerInsertCommand", commandList=[bind, bind_wait, release, release_wait]
    )

    # stc.connect(chassis_ip)
    # stc.perform("reservePort", location="//{}/{}".format(chassis_ip, port))
    # stc.perform("setupPortMappings")

    print("Attaching ports")
    stc.perform("AttachPorts", portList=[port_handle], autoConnect="TRUE")
    stc.apply()

    xdata = np.arange(10)
    ydata = []

    stc.perform("Dhcpv4BindCommand", blockList=dhcp_block)

    polling.poll(
        lambda: stc.get(dhcp_block, "BlockState") == "BOUND",
        step=1,
        poll_forever=True,
    )

    print(f"State is now: {stc.get(dhcp_block, 'BlockState')}")

    stc.perform("Dhcpv4ReleaseCommand", blockList=dhcp_block)

    polling.poll(
        lambda: stc.get(dhcp_block, "BlockState") == "IDLE",
        step=1,
        poll_forever=True,
    )

    print(f"State is now: {stc.get(dhcp_block, 'BlockState')}")
    results = stc.get(dhcp_block, "children-dhcpv4blockresults")
    print(f"Bind rate {stc.get(results, 'BindRate')} sessions/sec")

    # for i in range(3):
    #     # dhcp = stc.perform("Dhcpv4BindCommand", blockList=dhcp_block)
    #     print("waiting for bind")
    #     # stc.perform("SequencerStepCommand")
    #     # stc.perform("SequencerStepCommand")
    #     # stc.perform("SequencerPauseCommand")
    #     # time.sleep(5)
    #     stc.perform("SequencerStartCommand")
    #     print("starting release")

    #     # stc.perform("Dhcpv4ReleaseCommand", blockList=dhcp_block)
    #     # time.sleep(5)
    #     # stc.perform("SequencerStepCommand")
    #     # stc.perform("SequencerStepCommand")
    #     # stc.perform("SequencerPauseCommand")
    #     # stc.perform("SequencerStopCommand")
    #     stc.wait_until_complete()
    #     results = stc.get(dhcp_results["ReturnedDataSet"], "ResultHandleList")
    #     # ydata.append(stc.get(results, "BindRate"))
    #     print("Bind rate: {}".format(stc.get(results, "BindRate")))

    # Plot the data
    # plt.xlabel("Iteration #")
    # plt.ylabel("Bind Rate (sessions/sec)")
    # plt.axis(([1, 10, 0, 70]))
    # plt.plot(xdata, np.array(ydata, dtype="float32"))
    # plt.show()

    stc.disconnect(chassis_ip)
    stc.delete(deviceList)
    stc.delete(port_handle)
    stc.delete(project)
    stc.end_session()


if __name__ == "__main__":
    main()
