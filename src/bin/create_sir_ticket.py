from __future__ import print_function

import traceback
import logging
import json
import sys
import requests
import re
import time

from constants import (
    APPNAMESPACE,
    BASE_DOMAIN,
    PARAMETER_REGEX,
    SECRET_DELIMITER,
    SECRET_NAME,
    SECRET_REALM,
    SERVICENOW_REQUEST_HEADERS,
    SIR_TABLE_FIELDS,
    SIR_TABLE_MANDATORY_FIELDS,
    SIR_TABLE_NAME,
)
import utils

if __name__ == "__main__":
    import splunk.entity as entity
    import splunk.rest as rest


class SplunkClient(object):
    def __init__(self, session_key, app_namespace, configuration, result):
        self.session_key = session_key
        self.app_namespace = app_namespace
        self.configuration = configuration
        self.result = result

        self._creds = self._get_credentials()
        self._kv_hash = self._get_kv_hash()
        self._base_url = "/servicesNS/nobody/search/storage/collections"

    def _get_credentials(self):
        """
        Get ServiceNow Credentials from Splunk entities store.
        """
        try:
            # list all credentials.
            # WARNING: Credentials are sorted at insertion time with username.
            entities = entity.getEntities(
                ["admin", "passwords"],
                namespace=self.app_namespace,
                owner="nobody",
                sessionKey=self.session_key,
                count="-1",
            )

            for e in entities.values():
                if e["realm"] == SECRET_REALM and e["username"] == SECRET_NAME:
                    username, password = e["clear_password"].split(SECRET_DELIMITER)
                    return username, password

            raise Exception(
                f"Secret {self.app_namespace} {SECRET_REALM} {SECRET_NAME} not found within {len(entities.values())} secrets. Please Set up credential first."
            )
        except Exception as e:
            raise Exception(
                f"Could not get {self.app_namespace} {SECRET_REALM} {SECRET_NAME} credential from splunk. Error: {str(e)}"
            )

    def _get_kv_hash(self):
        roll_up_fields = self.configuration["roll_up_match_fields"]
        short_desc = self.configuration["short_description"]

        if roll_up_fields == "":
            return utils.hash(f"{short_desc}".encode())

        fields = ""

        for field in roll_up_fields.split(","):
            fields += self.result.get(field.strip(), "")

        return utils.hash(f"{short_desc}{fields}".encode())

    def get_creds(self):
        return self._creds

    def upsert_collections(self):
        [headers, response] = rest.simpleRequest(
            f"{self._base_url}/config?output_mode=json",
            postargs={"name": SIR_TABLE_NAME},
            sessionKey=self.session_key,
        )

        status_code = headers["status"]

        if status_code == "409":  # 409 = already exists
            return

        if status_code == "201":  # 201 = success create
            rest.simpleRequest(
                f"{self._base_url}/config?output_mode=json",
                postargs={
                    "field.key": "integer",
                    "field.ticket_id": "string",
                    "field.timestamp": "integer",
                },
                sessionKey=self.session_key,
            )
            return

        body = json.loads(response)
        msg = f"Unexpected error while creating collections. Status: {status_code}. Messages:"

        for i, message in enumerate(body["messages"], start=1):
            msg += "\n{}. {}".format(i, message["text"])

        raise Exception(msg)

    def get_collection(self):
        try:  # Yes this rest call does throw exception.
            [headers, response] = rest.simpleRequest(
                f"{self._base_url}/data/{SIR_TABLE_NAME}/{self._kv_hash}?output_mode=json",
                sessionKey=self.session_key,
            )
            status_code = headers["status"]
            body = json.loads(response)

            if status_code == "200":
                return body
        except Exception as e:
            if e.statusCode == 404:
                return
            else:
                raise e

        msg = f"Unexpected error while fetching collection. Status: {status_code}. Messages:"

        for i, message in enumerate(body["messages"], start=1):
            msg += "\n{}. {}".format(i, message["text"])

        raise Exception(msg)

    def upsert_collection(self, ticket_id, timestamp, is_new_collection):
        url = f"{self._base_url}/data/{SIR_TABLE_NAME}?output_mode=json"

        if not is_new_collection:
            url = f"{self._base_url}/data/{SIR_TABLE_NAME}/{self._kv_hash}?output_mode=json"

        [headers, response] = rest.simpleRequest(
            url,
            jsonargs=json.dumps(
                {
                    "_key": self._kv_hash,
                    "ticket_id": ticket_id,
                    "timestamp": timestamp,
                }
            ),
            sessionKey=self.session_key,
        )
        status_code = headers["status"]

        if status_code == "200" or status_code == "201":
            return

        body = json.loads(response)
        msg = f"Failed to update collection. Status: {status_code}. Messages:"

        for i, message in enumerate(body["messages"], start=1):
            msg += "\n{}. {}".format(i, message["text"])

        raise Exception(msg)


class ServiceNowAlert(object):
    def __init__(self, credentials, configuration, result):
        self.creds = credentials
        self.configs = configuration
        self.result = result

        self._base_url = utils.get_servicenow_url(
            BASE_DOMAIN, configuration.get("environment"), SIR_TABLE_NAME
        )
        self._is_raw = utils.boolean(configuration.get("from_raw"))
        self._event = (
            utils.parse_raw_data(result.get("_raw")) if self._is_raw else result
        )
        self._payload = self._create_payload()

    def _create_payload(self):
        """
        Generate ServiceNow payload, based on pre-fined fields & actual alert config map.
        """
        payload = {}

        for type, fields in SIR_TABLE_FIELDS.items():
            if type == "string":
                for field in fields:
                    input = self.configs.get(field)
                    payload[field] = self._format_input(input)

        return payload

    def _format_input(self, input):
        """
        Replace any {{ field }} with correct replacements.
        """
        while re.search(PARAMETER_REGEX, input) is not None:
            var = (
                re.search(PARAMETER_REGEX, input)
                .group(0)
                .replace("{{", "")
                .replace("}}", "")
            )

            new_var = ""

            if "_raw" in var:
                new_var = self._event
            elif "." in var and self._is_raw:  # Maybe interested in object json
                new_var = utils.extract_path_from_dict(var, self._event)
            else:  # Not Raw? Try get exact value from result object
                new_var = self._event.get(var)

            if not isinstance(new_var, str):
                new_var = json.dumps(new_var)

            input = re.sub(PARAMETER_REGEX, new_var, input, 1)

        return input.replace("\\n", "\n")

    def get(self, ticket_id):
        response = requests.get(
            url=f"{self._base_url}?sysparm_query=sys_id%3D{ticket_id}&sysparm_fields=state&sysparm_limit=1",
            auth=self.creds,
        )

        if response.status_code >= 200 and response.status_code < 300:
            return response.json()["result"][0]

        raise RuntimeError(
            json.dumps(
                {
                    "Status:": response.status_code,
                    "Headers:": str(response.headers),
                    "Error Response:": response.json(),
                }
            )
        )

    def post(self):
        """
        Sends the data to Service-Now and checks for a 200 status code.
        """
        response = requests.post(
            url=self._base_url,
            auth=self.creds,
            headers=SERVICENOW_REQUEST_HEADERS,
            data=json.dumps(self._payload),
        )

        # Exit if status between 200 ~ 299
        if response.status_code >= 200 and response.status_code < 300:
            return response.json()["result"]["sys_id"]

        raise RuntimeError(
            json.dumps(
                {
                    "Status:": response.status_code,
                    "Headers:": str(response.headers),
                    "Error Response:": response.json(),
                }
            )
        )

    def update(self, ticket_id):
        state = self.get(ticket_id)["state"]

        if utils.boolean(self.configs["roll_up_reopen"]):
            state = 10  # Draft (10)

        response = requests.put(
            url=f"{self._base_url}/{ticket_id}",
            auth=self.creds,
            headers=SERVICENOW_REQUEST_HEADERS,
            data=json.dumps(
                {
                    "automation_activity": self._payload.get("description"),
                    "state": state,
                }
            ),
        )

        if response.status_code >= 200 and response.status_code < 300:
            return

        raise RuntimeError(
            json.dumps(
                {
                    "Status:": response.status_code,
                    "Headers:": str(response.headers),
                    "Error Response:": response.json(),
                }
            )
        )


def send_alert(session_key, configuration, result):
    """
    Main send alert action logic.

    Sample payload of session_key, configuration, and result can be found in repo `README.md`
    """
    if not utils.is_params_valid(configuration, SIR_TABLE_MANDATORY_FIELDS):
        sys.exit(2)

    splunk_client = SplunkClient(session_key, APPNAMESPACE, configuration, result)
    servicenow_client = ServiceNowAlert(
        splunk_client.get_creds(), configuration, result
    )

    if configuration["roll_up_duration"] == "":
        servicenow_client.post()
    else:
        splunk_client.upsert_collections()
        collection = splunk_client.get_collection()

        cur_time = int(time.time())

        ticket_id = None
        timestamp = cur_time

        if collection is not None and cur_time < (
            collection["timestamp"] + int(configuration["roll_up_duration"])
        ):
            ticket_id = collection["ticket_id"]

            if not utils.boolean(configuration["roll_up_rolling"]):
                timestamp = collection["timestamp"]  # keep original timestamp

            servicenow_client.update(ticket_id)
        else:
            ticket_id = servicenow_client.post()

        splunk_client.upsert_collection(ticket_id, timestamp, collection is None)


def exception_logging(exctype, value, tb):
    """Exception wrapper"""
    write_val = {
        "exception_type": str(exctype),
        "trace": str(traceback.format_tb(tb)),
        "message": value,
    }

    logging.exception(str(write_val))


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.StreamHandler(sys.stderr))
    sys.excepthook = exception_logging

    if len(sys.argv) < 1 or sys.argv[1] != "--execute":
        logging.error("Unsupported mode, expected --execute flag)")
        sys.exit(1)

    payload = json.loads(sys.stdin.read())

    send_alert(payload["session_key"], payload["configuration"], payload["result"])
