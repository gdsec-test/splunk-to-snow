APPNAMESPACE = "splunk_to_snow"

STATE_COLLECTION_NAME = "gd_splunk_to_snow"

# Tables added here should be added to /default/data/ui/alerts/create_service_now_ticket.html as well
CONFIG_TO_TABLE_FIELDS = {
    "u_physical_security": {
        "direct": {"ticket_state": "u_state"},
        "string": {
            "ticket_title": "u_title",
            "ticket_impact": "u_impact",
            "ticket_urgency": "u_urgency",
            "ticket_summary": "u_summary",
            "ticket_assignment_group": "u_assignment_group",
            "ticket_category": "u_category",
            "ticket_sub_category": "u_sub_category",
            "ticket_detection_method": "u_detection_method",
        },
        "datetime": {
            "ticket_detect_time": "u_detect_time",
            "ticket_event_time": "u_event_time",
        },
        "boolean": {"ticket_dsr": "u_dsr"},
    }
}

BASE_DOMAIN = "https://godaddy"

SERVICENOW_REQUEST_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
}


MANDATORY_CONFIG = [
    "environment",
    "from_raw",
    "ticket_dsr",
    "table",
    "ticket_state",
    "ticket_title",
    "ticket_impact",
    "ticket_urgency",
]


PARAMETER_REGEX = r"\{\{\S+?\}\}"


VALUE_MAPS = {
    "ticket_assignment_group": {
        # Intrusion Prevention Engineering assignment group ID
        "ENG-IPE": "2a9cd2534f19fe00dc4927201310c76e",
        "OPS-GCSO": "6918525edb696380f1bd5434ce96199e",
    }
}

SNOW_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
