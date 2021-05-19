from __future__ import print_function

import logging
import json
import re
import hashlib


def is_params_valid(configuration, mandatory_fields):
    """
    Checks that all values for mandatory_fields in the alert are set in the
    alert action.
    """
    for c in mandatory_fields:
        value = configuration.get(c)
        if value is None or value == "":
            logging.exception(
                f"'{c}' is a mandatory setup parameter, but its values is None."
            )
            return False

    return True


def parse_raw_data(raw_string):
    """
    Parse raw data string to Python obj.
    """
    first_event = re.findall("^.*$", raw_string, flags=re.MULTILINE)[0]
    if first_event.startswith("{"):
        return json.loads(first_event)
    else:
        raise Exception("Cannot parse non-JSON.")


def extract_path_from_dict(path, dictionary):
    """
    Extracts value from a dict; and if applicable,
    traverses dict to get a nested value
    """
    keys = path.split(".")
    val = dictionary

    for k in keys:
        if not isinstance(val, dict):
            return None

        val = val.get(k)

    return val


def get_servicenow_url(base_url, env, table_name):
    """
    Get ServiceNow URL based on env value.
    """
    servicenow_url = base_url

    if env != "prod":
        servicenow_url += "dev"

    return servicenow_url + ".service-now.com/api/now/table/" + table_name


def boolean(val):
    """
    If `val` == "1" # returns True.

    Else # returns False.
    """
    return val == "1"


def hash(input):
    """
    Hash input using sha256, then return.
    """
    return hashlib.sha256(input).hexdigest()
