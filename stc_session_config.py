from SpirentSLC import SLC
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
    s1 = slc.sessions.ssh.open(
        properties={
            "ipAddress": "172.25.205.146",
            "user": "t970164",
            "password": "cgLeUdKCiBlcle5lPgMMTYdUtGlayvWt",
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
        'show service active-subscribers detail | match "Subscriber {}"'.format(subline)
    )
    if step_response.result == "success":
        if step_response.text:
            with open("C:\\Users\\t970164\\Documents\\subscribers.txt", "w") as file:
                file.write(step_response.text)
                file.write("\n")
        else:
            raise Exception("Subscriber did not bind")


def chart_dhcp_bind_rate(slc):
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
            "config": "file:/C:/Users/t970164/spirent11.2.tcc",
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
    pass


def main(slc, logger, status):
    # param = Params({
    #     'ldap_pass': 'cgLeUdKCiBlcle5lPgMMTYdUtGlayvWt',
    # })
    procedure_result = "{}"

    hsia = WSIR("hsia-service-instances")
    chrg = WSIR("hsia-data-usage-charging-balance-groups")
    ids = create_ref_id()

    r1 = hsia.post(
        payload={
            "telusServiceInstanceReferenceId": ids[0],
            "telusHSIAAccessInterfaceId": "NAFISA-TEST 1/1/1/122",
            "telusHSIASubscriberLineId": "sl_NAFISA-TEST/1/1/1/122",
            "telusNetworkPolicy": [
                "up-speed-kbps:15000",
                "dn-speed-kbps:15000",
                "conn-conf-set:hsia|ttv",
            ],
        }
    )

    r2 = chrg.post(
        payload={
            "telusServiceInstanceReferenceId": ids[0],
            "telusChrgBlnceGrpRefId": ids[1],
            "telusChrgBlnceGrpPolicy": [
                "mo-dat-usage-cap:1000",
                "bill-cycle-start-day:5",
            ],
        }
    )

    sub = hsia.get(extract_ref_id(r1))["telusHSIASubscriberLineId"]
    print("start stc dhcp session")
    stc = stc_session(slc)
    stc.subscribe("DhcpResults")
    stc.stepSequencer()  # DHCP bind session step
    stc.stepSequencer()  # DHCP wait for bind step
    stc.waitSequencer()  # Pause sequencer
    print("confirm sub is bound on RE")
    show_re_test_subscribers(sub)
    print("dhcp release")
    stc.stepSequencer()  # DHCP release step
    stc.waitSequencer()  # Pause sequencer
    stc.stepSequencer()  # DHCP wait for release
    stc.stopDevices()
    print("clean up")
    chrg.delete(extract_ref_id(r2))
    hsia.delete(extract_ref_id(r1))

    # chart_dhcp_bind_rate(slc)
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
            multi_subs(slc, logger, status)
    except TestTermination:
        pass
    except:
        status.fail_test()
        raise
    finally:
        logger.info("Execution completed (%ds)" % int(time.time() - begin))
        logger.info("Status: %s" % status.get())
