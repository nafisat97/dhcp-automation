from datetime import datetime
import requests
import json
import copy

hsia_base_url = "https://nsd.teluslabs.net/hsia-service-instances/"

charge_base_url = "https://nsd.teluslabs.net/hsia-data-usage-charging-balance-groups/"

wsir_hsia_headers = {
    "Content-Type": "application/json",
    "Accept": "application/vnd.telus.api.wsir-si-hsia-v1.1+json;charset=utf-8",
}

wsir_charge_headers = {
    "Content-Type": "application/json",
    "Accept": "application/vnd.telus.api.wsir-hsia-dat-usg-chrg-blnce-grp-v1.1+json;charset=utf-8",
}

wsir_auth = ("wlndevportal", "Telus2018")


class WSIR:
    # POST, GET, PUT, DELETE wsir account
    def __init__(self, service) -> None:
        """Initialize the WSIR REST API wrapper object

        Args:
            service (string): Specifies WSIR service, one of hsia-service-instances or
            hsia-data-usage-charging-balance-groups

        Raises:
            RuntimeError: [description]
        """

        if not service:
            raise RuntimeError("Service not set")

        self.url = "https://nsd.teluslabs.net/{}/".format(service)
        self.hsia_payload = {
            "telusSourceSystem": "falcon",
            "telusServiceInstanceReferenceId": "",
            "telusServiceInstanceStatus": "active",
            "telusAccessNetworkTechnologyType": "vdsl2",
            "telusHSIAServiceDeliveryMethod": "convergededge",
            "telusHSIASubscriberLineId": "",
            "telusHSIAAccessInterfaceId": "",
            "telusPCRFGroupAffinity": "AB",
            "telusNetworkPolicy": [],
            "telusServiceInstanceChargingMethod": "offline",
        }
        self.charge_payload = {
            "telusSourceSystem": "falcon",
            "telusServiceInstanceReferenceId": "",
            "telusServiceInstanceReferenceSourceSystem": "falcon",
            "telusChrgBlnceGrpRefId": "",
            "telusChrgBlnceGrpStatus": "active",
            "telusOCSGrpAffinity": "AB",
            "telusChrgBlnceGrpPolicy": [],
        }

    def get(self, rid):
        if self.url == hsia_base_url:
            self.hsia_payload["telusServiceInstanceReferenceId"] = rid

            url = (
                self.url
                + self.hsia_payload["telusSourceSystem"]
                + "/"
                + self.hsia_payload["telusServiceInstanceReferenceId"]
            )
            response = requests.get(
                url, verify=False, headers=wsir_hsia_headers, auth=wsir_auth
            )

        elif self.url == charge_base_url:
            self.charge_payload["telusChrgBlnceGrpRefId"] = rid

            url = (
                self.url
                + self.charge_payload["telusSourceSystem"]
                + "/"
                + self.charge_payload["telusChrgBlnceGrpRefId"]
            )
            response = requests.get(
                url, verify=False, headers=wsir_charge_headers, auth=wsir_auth
            )
        else:
            raise Exception("Service not supported")

        return response.json()

    def post(self, payload):
        if self.url == hsia_base_url:
            self.hsia_payload.update(payload)
            print(self.hsia_payload)
            response = requests.post(
                self.url,
                verify=False,
                headers=wsir_hsia_headers,
                auth=wsir_auth,
                json=self.hsia_payload,
            )

        elif self.url == charge_base_url:
            self.charge_payload.update(payload)
            response = requests.post(
                self.url,
                verify=False,
                headers=wsir_charge_headers,
                auth=wsir_auth,
                json=self.charge_payload,
            )

        else:
            raise Exception("Service not supported")

        return response.json()

    def put(self, payload=None):
        pass

    def delete(self, rid):
        if self.url == hsia_base_url:
            self.hsia_payload["telusServiceInstanceReferenceId"] = rid
            url = (
                self.url
                + self.hsia_payload["telusSourceSystem"]
                + "/"
                + self.hsia_payload["telusServiceInstanceReferenceId"]
            )
            response = requests.delete(
                url, verify=False, headers=wsir_hsia_headers, auth=wsir_auth
            )

        elif self.url == charge_base_url:
            self.charge_payload["telusChrgBlnceGrpRefId"] = rid
            url = (
                self.url
                + self.charge_payload["telusSourceSystem"]
                + "/"
                + self.charge_payload["telusChrgBlnceGrpRefId"]
            )
            response = requests.delete(
                url, verify=False, headers=wsir_charge_headers, auth=wsir_auth
            )
        else:
            raise Exception("Service not supported")

        return response.json()


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


def extract_ref_id(response):
    return str(response["message"].split("/")[-1].split()[0])
