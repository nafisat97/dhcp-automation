from SpirentSLC import SLC
from SpirentSLC.topology import Device
from stcrestclient import stchttp
from SpirentSLC.Execution import *
from wsir_api import *

import re
import io
import sys
import logging
import collections
import json
import time
import math
import random
import matplotlib.pyplot as plt
import numpy as np

testbed_uri = "project://my_project/topologies/test1.tbml"


def show_re_test_subscribers(subline):
    """Show active subscribers as a result of DHCP bind"""

    # Simulates subs created in wsir
    accounts = []
    for i in range(20, 120):
        accounts.append("sl_NAFISA-TEST/1/1/1/{}".format(str(i)))

    s1 = slc.sessions.ssh.open(
        properties={
            "ipAddress": "172.25.205.146",
            "user": "t970164",
            "password": "y1etIzac1o2T/OQekPq8Ew==",
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

    s1.command("environment no more")
    step_response = s1.command(
        'show service active-subscribers detail | match "Subscriber sl_"'
    )
    if step_response.result == "success":
        sublines = re.findall("sl_\S+", step_response.text)
        for sub in accounts:
            if sub not in sublines:
                # Can log this instead
                print("Subscriber {} did not bind".format(sub))

        # with open("C:\\Users\\t970164\\Documents\\subscribers.txt", "w") as file:
        #     file.write(step_response.text)
        #     file.write("\n")


def chart_itest_dhcp_bind_rate(slc):
    stc = stc_session(slc)

    xdata = np.arange(6)
    ydata = []

    for i in range(6):
        stc.subscribe("DhcpResults")
        stc.stepSequencer()  # DHCP bind session step
        stc.stepSequencer()  # DHCP wait for bind step
        stc.waitSequencer()  # Pause sequencer
        dhcp_stats = stc.showStats("DhcpResults")
        if dhcp_stats.result == "success":
            bind_rate = dhcp_stats.query("BindRate('1', \"Device 1\")")
            ydata.append(bind_rate)
        stc.stepSequencer()  # DHCP release step
        stc.waitSequencer()  # Pause sequencer
        stc.stepSequencer()  # DHCP wait for release

    stc.stopDevices()

    # Plot the data
    plt.xlabel("Iteration #")
    plt.ylabel("Bind Rate (sessions/sec)")
    plt.axis(([0, 6, 0, 70]))
    plt.plot(xdata, np.array(ydata, dtype="float32"))
    plt.show()
    return


def stc_session(slc):
    """Creates a STC session profile"""
    stc = slc.sessions.testcenter_gui.open(
        properties={
            "ipAddress": "",
            "ports": "",
            "config": "file:/C:/Users/t970164/testsub.tcc",
            "forceOwnership": "false",
            "connectToPorts": "true",
            "tcl": {
                "interpreterLocation": "file:/C:/Program%20Files/Spirent%20Communications/Spirent%20TestCenter%204.94/Spirent%20TestCenter%20Application/Tcl/bin/tclsh85.exe",
                "testcenterTclAPIDir": "file:/C:/Program%20Files/Spirent%20Communications/Spirent%20TestCenter%204.94/Spirent%20TestCenter%20Application/",
            },
        }
    )
    return stc


def multi_subs(slc, logger, status):
    accounts = []
    for i in range(20, 120):
        accounts.append("sl_NAFISA-TEST/1/1/1/{}".format(str(i)))
    # pprint(accounts)

    file = open("C:\\Users\\t970164\\Documents\\subscribers.txt", "r")
    text = file.read()
    file.close()
    sublines = re.findall("sl_\S+", text)
    # pprint(sublines)

    not_sub = []
    for account in accounts:
        if account not in sublines:
            not_sub.append(account)

    print(not_sub)


def main(slc, logger, status):
    # param = Params({
    #     'ldap_pass': 'cgLeUdKCiBlcle5lPgMMTYdUtGlayvWt',
    # })
    procedure_result = "{}"

    hsia = WSIR("hsia-service-instances")
    chrg = WSIR("hsia-data-usage-charging-balance-groups")
    ids = create_ref_id()

    # r1 = hsia.post(
    #     payload={
    #         "telusServiceInstanceReferenceId": ids[0],
    #         "telusHSIAAccessInterfaceId": "NAFISA-TEST 1/1/1/122",
    #         "telusHSIASubscriberLineId": "sl_NAFISA-TEST/1/1/1/122",
    #         "telusNetworkPolicy": [
    #             "up-speed-kbps:15000",
    #             "dn-speed-kbps:15000",
    #             "conn-conf-set:hsia|ttv",
    #         ],
    #     }
    # )

    # r2 = chrg.post(
    #     payload={
    #         "telusServiceInstanceReferenceId": ids[0],
    #         "telusChrgBlnceGrpRefId": ids[1],
    #         "telusChrgBlnceGrpPolicy": [
    #             "mo-dat-usage-cap:1000",
    #             "bill-cycle-start-day:5",
    #         ],
    #     }
    # )
    # sub = hsia.get(extract_ref_id(r1))["telusHSIASubscriberLineId"]

    logger.info("Start stc dhcp session")
    stc = stchttp.StcHttp(server="127.0.0.1", port="8888")
    stc.new_session("nafisa", "test", kill_existing=True)
    stc.join_session("test - nafisa")

    # Spirent Chassis and port details
    chassis_ip = "172.25.205.185"
    port = "11/2"

    # Project hierarchy
    project = stc.create("project")
    port_handle = stc.create("port", under=project)
    stc.config(port_handle, location="//{}/{}".format(chassis_ip, port))

    # Emulated device relations
    deviceList = stc.create(
        "emulateddevice", under=project, affiliatedPort=port_handle, DeviceCount=100
    )
    ethiiIf = stc.create("EthIIIf", under=deviceList)
    vlanIF = stc.create("VlanIf", under=deviceList, StackedOn=ethiiIf)
    ipv4If = stc.create("Ipv4If", under=deviceList, StackedOn=vlanIF)
    stc.config(deviceList, PrimaryIf=ipv4If, ToplevelIf=ipv4If)
    single_cID = "NAFISA-TEST 1/1/1/20"
    multi_cID = "NAFISA-TEST 1/1/1/@x(20,120)"
    dhcp_block = stc.create(
        "dhcpv4blockconfig",
        under=deviceList,
        CircuitId=multi_cID,
        EnableCircuitId="TRUE",
        EnableRelayAgent="FALSE",
        UsesIf=ipv4If,
    )

    # Subscribe to results
    dhcp_results = stc.perform(
        "ResultsSubscribeCommand",
        parent=project,
        resultParent=port_handle,
        resultType="Dhcpv4BlockResults",
        configType="Dhcpv4BlockConfig",
        ViewAttributeList="BindRate",
        FileNamePrefix="multi",
    )

    # Sequencer config
    sequencer = stc.create("sequencer", under="system1")
    bind = stc.create("Dhcpv4BindCommand", under=sequencer, BlockList=dhcp_block)
    bind_wait = stc.create(
        "Dhcpv4BindWaitCommand",
        under=sequencer,
        attributes={"ObjectList": deviceList, "WaitTime": 100.0},
    )
    release = stc.create("Dhcpv4ReleaseCommand", under=sequencer, blockList=dhcp_block)
    release_wait = stc.create(
        "Dhcpv4ReleaseWaitCommand",
        under=sequencer,
        attributes={"ObjectList": deviceList, "WaitTime": 100.0},
    )

    stc.perform(
        "SequencerInsertCommand", commandList=[bind, bind_wait, release, release_wait]
    )

    logger.info("Attaching ports")
    stc.perform("AttachPorts", portList=[port_handle], autoConnect="TRUE")
    stc.apply()

    for i in range(3):
        stc.perform("SequencerStartCommand")
        logger.info("Waiting for bind")

        logger.info("confirm sub is bound on RE")
        show_re_test_subscribers(None)

        logger.info("dhcp release")
        stc.wait_until_complete()

        results = stc.get(dhcp_results["ReturnedDataSet"], "ResultHandleList")
        print(stc.get(results, "BindRate"))

    # print("clean up")
    # chrg.delete(extract_ref_id(r2))
    # hsia.delete(extract_ref_id(r1))
    stc.delete(deviceList)
    stc.delete(port_handle)
    stc.delete(project)
    stc.end_session()

    return procedure_result


def tbml(subcommand, *argv):
    return internal_tbml(testbed_uri, subcommand, *argv)


if __name__ == "__main__":
    status = Status()
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s", level=logging.DEBUG
    )
    logger = logging.getLogger(__name__)
    begin = time.time()
    logger.info("Execution started")
    try:
        with SLC.init(host="localhost:9005") as slc:
            main(slc, logger, status)
    except TestTermination:
        pass
    except:
        status.fail_test()
        raise
    finally:
        logger.info("Execution completed (%ds)" % int(time.time() - begin))
        logger.info("Status: %s" % status.get())
