from __future__ import print_function

from constants import (
    APPNAMESPACE,
    STATE_COLLECTION_NAME,
    MANDATORY_CONFIG,
    CONFIG_TO_TABLE_FIELDS,
    VALUE_MAPS,
    SNOW_TIME_FORMAT,
    BASE_DOMAIN,
    PARAMETER_REGEX,
    SERVICENOW_REQUEST_HEADERS,
    SECRET_NAME,
    SECRET_DELIMITER,
)
from dateutil.parser import parse as parse_date
from datetime import datetime
from operator import itemgetter
import traceback
import logging
import sys
import json
import re
import requests
import hashlib
import time

if __name__ == "__main__":
    import splunk.entity as entity
    import splunk.rest as rest


def getCredentials(sessionKey):
    """
    Access the credentials in /servicesNS/nobody/app_name/admin/passwords
    2-Write-a-python-script-that-uses-credentials
    From: https://dev.splunk.com/enterprise/docs/developapps/setuppage/setupxmlexamples/
    """
    try:
        # list all credentials.
        # WARNING: Credentials are sorted at insertion time with username.
        entities = entity.getEntities(
            ["admin", "passwords"],
            namespace=APPNAMESPACE,
            owner="nobody",
            sessionKey=sessionKey,
        )

        for e in entities.values():
            if e["username"] == SECRET_NAME:
                username, password = e["clear_password"].split(SECRET_DELIMITER)
                return username, password

        raise Exception(
            f"Secret {SECRET_NAME} not found within {len(entities.values())} secrets. Please Set up credentials first."
        )
    except Exception as e:
        raise Exception(
            f"Could not get {APPNAMESPACE} credentials from splunk. Error: {str(e)}"
        )


def exception_logging(exctype, value, tb):
    write_val = {
        "exception_type": str(exctype),
        "trace": str(traceback.format_tb(tb)),
        "message": value,
    }

    logging.exception(str(write_val))


def params_are_valid(_config):
    """
    Checks that all values for MANDATORY_CONFIG in the alert are set in the
    alert action.
    """
    for c in MANDATORY_CONFIG:
        value = _config.get(c)
        if value is None or _config.get(c) == "":
            logging.exception(
                "'{}' is a mandatory setup parameter, \
                  but its values is None.".format(
                    c
                )
            )
            return False

        if value == "table" and value not in CONFIG_TO_TABLE_FIELDS:
            logging.exception(
                "'{}' is not a configured table. \
                Add it to CONFIG_TO_TABLE_FIELDS in order to use it".format(
                    c
                )
            )
            return False

    return True


def string_0_1_to_bool(string):
    return string == "1"


def construct_key(configuration, result):
    if configuration["roll_up_match_fields"] != "":
        match_field_values = ""
        for field in configuration["roll_up_match_fields"].split(","):
            match_field_values += result[field]

        return kv_store.hash_key_meta(
            b"{}{}".format(configuration["ticket_title"], match_field_values)
        )
    else:
        return kv_store.hash_key_meta(b"{}".format(configuration["ticket_title"]))


def update_existing_ticket(ticket_id):
    ticket_state = get_existing_ticket_state(ticket_id)

    request.set_state(ticket_state)
    request.update_ticket(ticket_id)


def get_existing_ticket_state(sys_id):
    cur_ticket_state = request.get(sys_id)["u_state"]

    if cur_ticket_state == "closed" and string_0_1_to_bool(
        configuration["roll_up_reopen"]
    ):
        return "new"
    else:
        return cur_ticket_state


class Request(object):
    def __init__(self, credentials):
        self._url = None  # Service-Now URL
        self._result = None  # The "result" of the Alert Action"
        self._config = None  # The "configuration" of the Alert Action
        self._event = None  # The "_raw" field of the result json.loads to dict
        self._data = {}  # Data that will be posted to Service-Now
        self._credentials = credentials

    def construct_from_payload(self, result, configuration):
        """
        Operations as a part of the initialization of this Request object.
        """
        self._result = result
        self._config = configuration

        self._parse_raw = string_0_1_to_bool(configuration.get("from_raw"))

        if self._parse_raw:
            self._event = self._parse_event(result["_raw"])
        else:
            self._event = result

        self._table_fields = CONFIG_TO_TABLE_FIELDS[configuration.get("table")]
        self._set_url()
        self._extract_config()

    @staticmethod
    def _parse_event(string):
        first_event = re.findall("^.*$", string, flags=re.MULTILINE)[0]
        if first_event.startswith("{"):
            return json.loads(first_event)
        else:
            raise Exception("Cannot parse non-JSON.")

    def _set_url(self):
        """
        Constructs the URL used for the request (between dev and prod
        Service-Now instances).
        """
        if self._config.get("environment") == "prod":
            domain = BASE_DOMAIN
        else:
            domain = BASE_DOMAIN + "dev"
        self._url = (
            domain + ".service-now.com/api/now/table/" + self._config.get("table")
        )

    def _extract_config(self):
        """
        Processes the event and assigns the proper values to the data
        that will be sent with the Service-Now request.
        """
        if "direct" in self._table_fields:
            for config_field, snow_field in self._table_fields["direct"].items():
                self._set_data_field(snow_field, self._config.get(config_field))

        if "string" in self._table_fields:
            for config_field, snow_field in self._table_fields["string"].items():
                self._set_data_replace(
                    snow_field, self._config.get(config_field), config_field
                )

        if "datetime" in self._table_fields:
            for config_field, snow_field in self._table_fields["datetime"].items():
                self._set_data_datetime(snow_field, self._config.get(config_field))

        if "boolean" in self._table_fields:
            for config_field, snow_field in self._table_fields["boolean"].items():
                self._set_data_boolean(snow_field, self._config.get(config_field))

    def _set_data_field(self, key, value):
        """
        Add key and value to the data that will be posted to Service-Now
        """
        self._data[key] = value

    def _set_data_replace(self, snow_field, value, config_field):
        """
        Assigns value based on map or after searching for user-defined
        parameters from the event
        """
        if value is not None and value != "":
            if config_field in VALUE_MAPS and value in VALUE_MAPS[config_field]:
                set_value = VALUE_MAPS[config_field][value]
            else:
                set_value = self._replace_params(value)

            self._set_data_field(snow_field, set_value)

    def _set_data_datetime(self, snow_field, value, now=datetime.now()):
        """
        Handles datetime fields
        """
        timestamp = None

        if value == "now":
            timestamp = now
        elif value == "_time":
            unix_timestamp = float(self._result["_time"])
            timestamp = datetime.utcfromtimestamp(unix_timestamp)

        elif value != "" and value is not None:
            param = self._extract_field(value)
            timestamp = parse_date(param)

        if timestamp is not None:
            self._set_data_field(snow_field, timestamp.strftime(SNOW_TIME_FORMAT))

    def _set_data_boolean(self, snow_field, value):
        """
        Handles boolean fields
        """
        self._set_data_field(snow_field, string_0_1_to_bool(value))

    def _replace_params(self, string):
        """
        Checks for user-provided paramaters and replaces them
        and any newlines in the provided string
        """
        while re.search(PARAMETER_REGEX, string) is not None:
            string = self._replace_next_param(string)
        return string.replace("\\n", "\n")

    def _replace_next_param(self, param_string):
        """
        Parses out a field from the result that triggered this alert.
        ex: {{field.event}} will return the "event" value within the
        "field" dict within the event. Converts resultant dicts to strings.
        """
        field = self._parse_param(param_string)

        if "_raw" in field:
            param = self._event
        elif "." in field and self._parse_raw is True:
            param = self._extract_field(field)
        else:
            param = self._event[field]

        if isinstance(param, dict):
            param = json.dumps(param)
        elif isinstance(param, int):
            param = str(param)

        return re.sub(PARAMETER_REGEX, param, param_string, 1)

    @staticmethod
    def _parse_param(param_string):
        """
        Returns the next parameter in the string
        """
        next_match = re.search(PARAMETER_REGEX, param_string).group(0)
        return next_match.replace("{{", "").replace("}}", "")

    def _extract_field(self, field_path):
        """
        Extracts value from a dict; and if applicable,
        traverses dict to get a nested value
        """
        nested_value_path = field_path.split(".")
        param = self._event[nested_value_path.pop(0)]

        for nfp in nested_value_path:
            param = param[nfp]

        return param

    def post(self):
        """
        Sends the data to Service-Now and checks for a 200 status code.
        """
        response = requests.post(
            url=self._url,
            auth=self._credentials,
            headers=SERVICENOW_REQUEST_HEADERS,
            data=json.dumps(self._data),
        )

        if 200 < response.status_code and response.status_code <= 299:
            sys_id = response.json()["result"]["sys_id"]
            return sys_id
        else:
            raise RuntimeError(
                json.dumps(
                    {
                        "Status:": response.status_code,
                        "Headers:": str(response.headers),
                        "Error Response:": response.json(),
                    }
                )
            )

    def update_ticket(self, roll_up_sys_id, state=None):
        if "u_summary" in self._data:
            data = {"u_narrative": self._data["u_summary"]}
        else:
            data = {"u_narrative": "A new event has triggered this alert."}

        if state is not None:
            data["u_state"] = state
        self.put(roll_up_sys_id, data)

    def put(self, roll_up_sys_id, data):
        """
        Sends the data to Service-Now and checks for a 200 status code.
        """
        response = requests.put(
            url=self._url + "/{}".format(roll_up_sys_id),
            auth=self._credentials,
            headers=SERVICENOW_REQUEST_HEADERS,
            data=json.dumps(data),
        )

        if 200 > response.status_code or response.status_code > 299:
            raise RuntimeError(
                json.dumps(
                    {
                        "Status:": response.status_code,
                        "Headers:": str(response.headers),
                        "Error Response:": response.json(),
                    }
                )
            )

    def get(self, sys_id):
        response = requests.get(
            url=self._url
            + "?sysparm_query=sys_id%3D{}&sysparm_fields=u_state&sysparm_limit=1".format(
                sys_id
            ),
            auth=self._credentials,
        )
        if 200 <= response.status_code and response.status_code < 299:
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

    def set_state(self, state):
        self._data["state"] = state


class KVStore(object):
    def __init__(self, sessionKey):
        self.sessionKey = sessionKey

    def getState(self, key):
        try:
            [headers, bodyRaw] = rest.simpleRequest(
                "/servicesNS/nobody/search/storage/collections/data/{}/{}?output_mode=json".format(
                    STATE_COLLECTION_NAME, key
                ),
                sessionKey=self.sessionKey,
            )
            status = headers["status"]
            body = json.loads(bodyRaw)

            if status == "200":
                return body
        except Exception as err:
            if err.statusCode == 404:
                return None
            else:
                raise err

        exceptMessage = "Unknown status. Status: {}. Messages:".format(status)

        i = 0
        for message in body["messages"]:
            i += 1
            exceptMessage += "\n{}. {}".format(i, message["text"])

        raise Exception(exceptMessage)

    def createCollection(self):
        collection_name = {"name": STATE_COLLECTION_NAME}
        return rest.simpleRequest(
            "/servicesNS/nobody/search/storage/collections/config?output_mode=json",
            postargs=collection_name,
            sessionKey=self.sessionKey,
        )

    def defineNewCollectionSchema(self):
        collection_schema = {
            "field.key": "integer",
            "field.ticket_id": "string",
            "field.timestamp": "integer",
        }
        return rest.simpleRequest(
            "/servicesNS/nobody/search/storage/collections/config?output_mode=json",
            postargs=collection_schema,
            sessionKey=self.sessionKey,
        )

    def raiseIfCollectionNotExist(self):
        [headers, bodyRaw] = self.createCollection()
        status = headers["status"]
        # 201 = successfully created
        # 409 = already exists
        if status == "201":
            self.defineNewCollectionSchema()
        elif status != "409":
            body = json.loads(bodyRaw)
            exceptMessage = "Failed to make collection. Status: {}. Messages:".format(
                status
            )

            i = 0
            for message in body["messages"]:
                i += 1
                exceptMessage += "\n{}. {}".format(i, message["text"])

            raise Exception(exceptMessage)

    def postState(self, key, ticket_id, timestamp, new):
        if new is False:
            post_url = "/servicesNS/nobody/search/storage/collections/data/{}/{}?output_mode=json".format(
                STATE_COLLECTION_NAME, key
            )
        else:
            post_url = "/servicesNS/nobody/search/storage/collections/data/{}?output_mode=json".format(
                STATE_COLLECTION_NAME
            )
        state = {"_key": key, "ticket_id": ticket_id, "timestamp": timestamp}
        [headers, bodyRaw] = rest.simpleRequest(
            post_url,
            jsonargs=json.dumps(state),
            sessionKey=self.sessionKey,
        )
        status = headers["status"]

        if status != "200" and status != "201":
            body = json.loads(bodyRaw)
            exceptMessage = "Failed to update collection. Status: {}. Messages:".format(
                status
            )

            i = 0
            for message in body["messages"]:
                i += 1
                exceptMessage += "\n{}. {}".format(i, message["text"])

            raise Exception(exceptMessage)

    @staticmethod
    def hash_key_meta(meta):
        return hashlib.sha256(meta).hexdigest()


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.StreamHandler(sys.stderr))
    sys.excepthook = exception_logging

    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        payload = json.loads(sys.stdin.read())
        session_key, configuration, result = itemgetter(
            "session_key", "configuration", "result"
        )(payload)
        credentials = getCredentials(session_key)

        if params_are_valid(configuration) is False:
            sys.exit(2)

        request = Request(credentials)
        request.construct_from_payload(result, configuration)

        if configuration["roll_up_duration"] == "":
            request.post()
        else:
            kv_store = KVStore(session_key)
            kv_state_key = construct_key(configuration, result)
            kv_store.raiseIfCollectionNotExist()
            state = kv_store.getState(kv_state_key)

            now = int(time.time())  # floor
            timestamp = now
            if state is not None:
                roll_up_time_out = state["timestamp"] + int(
                    configuration["roll_up_duration"]
                )
                if roll_up_time_out > now:
                    update_existing_ticket(state["ticket_id"])
                    sys_id = state["ticket_id"]

                    if string_0_1_to_bool(configuration["roll_up_rolling"]) is False:
                        timestamp = state["timestamp"]
                else:
                    sys_id = request.post()
            else:
                sys_id = request.post()

            kv_store.postState(kv_state_key, sys_id, timestamp, state is None)

        sys.exit(0)
