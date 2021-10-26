from datetime import datetime
from pprint import pprint
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import json
import sys
import os
import pandas as pd
import time
import uuid

# TODO: look at performance of async http requests with tornado or something similar
# FIXME: not all requests get completed, better logging and error handling
#        create ref_id in csv file


hsia_base_url = "https://nsd.teluslabs.net/hsia-service-instances/"

charge_base_url = "https://nsd.teluslabs.net/hsia-data-usage-charging-balance-groups/"

wsir_hsia_headers = {
    "Content-Type": "application/json",
    "Accept": "application/vnd.telus.api.wsir-si-hsia-v1.1+json;charset=utf-8",
    "Connection": "keep-alive",
    "Keep-Alive": "timeout=10, max=500",
}

wsir_charge_headers = {
    "Content-Type": "application/json",
    "Accept": "application/vnd.telus.api.wsir-hsia-dat-usg-chrg-blnce-grp-v1.1+json;charset=utf-8",
    "Connection": "keep-alive",
    "Keep-Alive": "timeout=10, max=500",
}

wsir_auth = ("wlndevportal", "Telus2018")

directory = "C:\\Users\\t970164\\test-cases"


def create_ref_id():
    t = datetime.now()
    ids = (
        str(
            "132"
            + str(t.year)
            + str(t.month).zfill(2)
            + str(t.day).zfill(2)
            + str(t.hour).zfill(2)
            + str(t.minute).zfill(2)
            + str(t.second).zfill(2)
            + str(t.microsecond)[:2]
        ),
        str(
            ""
            + str(t.year)
            + str(t.month).zfill(2)
            + str(t.day).zfill(2)
            + str(t.hour).zfill(2)
            + str(t.minute).zfill(2)
            + str(t.second).zfill(2)
            + str(t.microsecond)[:2]
        ),
    )
    return ids


def uuid_ref_id():
    return (
        "132" + str(uuid.uuid4().int & (1 << 64) - 1)[:16],
        str(uuid.uuid4().int & (1 << 64) - 1)[:16],
    )


def extract_ref_id(response):
    return str(response["message"].split("/")[-1].split()[0])


def import_bulk(filename):
    wsir_service = {
        "telusSourceSystem": "falcon",
        "telusServiceInstanceReferenceId": "",
        "telusServiceInstanceStatus": "active",
        "telusAccessNetworkTechnologyType": "vdsl2",
        "telusHSIAServiceDeliveryMethod": "convergededge",
        "telusPCRFGroupAffinity": "AB",
        "telusNetworkPolicy": [],
        "telusServiceInstanceChargingMethod": "offline",
    }

    if os.path.isfile(os.path.join(directory, filename)):
        subscriber_filepath = os.path.realpath(os.path.join(directory, filename))
    else:
        print("File does not exist")
        sys.exit(1)

    bulk_subs = pd.read_csv(subscriber_filepath)
    bulk_subs = bulk_subs.to_dict(orient="records")

    ref_ids = {"subline": [], "hsia": [], "charge": []}
    payload = []

    for sub in bulk_subs:
        ids = None
        wsir_charge = {}
        sub.update(wsir_service)
        # ids = create_ref_id()
        ids = uuid_ref_id()
        sub["telusServiceInstanceReferenceId"] = ids[0]
        sub["telusNetworkPolicy"] = [
            f"up-speed-kbps:{str(sub.pop('up-speed-kbps'))}",
            f"dn-speed-kbps:{str(sub.pop('dn-speed-kbps'))}",
            "conn-conf-set:{}".format(sub.pop("conn-conf-set")),
        ]

        wsir_charge["telusSourceSystem"] = "falcon"
        wsir_charge["telusServiceInstanceReferenceId"] = ids[0]
        wsir_charge["telusServiceInstanceReferenceSourceSystem"] = "falcon"
        wsir_charge["telusChrgBlnceGrpRefId"] = ids[1]
        wsir_charge["telusChrgBlnceGrpStatus"] = "active"
        wsir_charge["telusOCSGrpAffinity"] = "AB"
        wsir_charge["telusChrgBlnceGrpPolicy"] = [
            f"mo-dat-usage-cap:{str(sub.pop('mo-dat-usage-cap'))}",
            f"bill-cycle-start-day:{str(sub.pop('bill-cycle-start-day'))}",
        ]
        payload.append((sub, wsir_charge))
        # time.sleep(1)

    for request in payload:
        ref_ids["subline"].append(request[0]["telusHSIASubscriberLineId"])
        ref_ids["hsia"].append(request[0]["telusServiceInstanceReferenceId"])
        ref_ids["charge"].append(request[1]["telusChrgBlnceGrpRefId"])

    df = pd.DataFrame(ref_ids)
    df.to_csv(f"{directory}/ref_ids_test2", encoding="utf-8", index=False)

    return payload


def post_wsir_service(payload):
    try:
        response = requests.post(
            hsia_base_url,
            verify=False,
            headers=wsir_hsia_headers,
            auth=wsir_auth,
            json=payload,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        return f"Error: {str(e)}"


def post_wsir_charge(payload):
    try:
        response = requests.post(
            charge_base_url,
            verify=False,
            headers=wsir_charge_headers,
            auth=wsir_auth,
            json=payload,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        return f"Error: {str(e)}"


def delete_wsir_service(url):
    response = requests.delete(
        url,
        verify=False,
        headers=wsir_hsia_headers,
        auth=wsir_auth,
    )
    return response.json()


def delete_wsir_charge(url):
    response = requests.delete(
        url,
        verify=False,
        headers=wsir_charge_headers,
        auth=wsir_auth,
    )
    return response.json()


def post_bulk(service, charge):
    post_wsir_service(service)
    post_wsir_charge(charge)


def delete_bulk(service, charge):
    delete_wsir_charge(f"{charge_base_url}falcon/{charge}")
    delete_wsir_service(f"{hsia_base_url}falcon/{service}")


def get_bulk():
    pass


def delete_imported_bulk():
    # write to csv file with instance IDs captured from successful calls
    # delete charge before service
    if os.path.isfile(os.path.join(directory, "ref_ids_test2")):
        subscriber_filepath = os.path.realpath(os.path.join(directory, "ref_ids_test2"))
    else:
        print("File does not exist")
        sys.exit(1)

    # data = pd.read_csv("ids.txt", sep=",", header=None)
    # data.columns = ["hsia", "charge"]
    # data = data.to_dict(orient="records")
    # return data

    subs_to_delete = pd.read_csv(subscriber_filepath)
    # for finding duplicate records
    # dupes = subs_to_delete["charge"].duplicated()
    # print(subs_to_delete["charge"][dupes])
    subs_to_delete = subs_to_delete.to_dict(orient="records")

    return subs_to_delete


def post_runner(subs):
    with ThreadPoolExecutor(max_workers=10) as executor:
        for sub in subs:
            executor.submit(post_bulk, service=sub[0], charge=sub[1])


def delete_runner():
    subs = delete_imported_bulk()
    with ThreadPoolExecutor(max_workers=10) as executor:
        for sub in subs:
            executor.submit(delete_bulk, service=sub["hsia"], charge=sub["charge"])


if __name__ == "__main__":
    # subs = import_bulk("subs.csv")
    # post_runner(subs)
    # delete_runner()
    delete_imported_bulk()
