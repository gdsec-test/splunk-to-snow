# splunk-to-snow

| main                                                                                                                                                                                                  |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [![Build Workflow](https://github.com/gdcorp-infosec/splunk-to-snow/actions/workflows/build.yml/badge.svg?branch=main)](https://github.com/gdcorp-infosec/splunk-to-snow/actions/workflows/build.yml) |

Splunk to ServiceNow App. This repo is based off of [infosec/splunk-to-snow](https://github.secureserver.net/infosec/splunk-to-snow)

## How to contribute 💻

Please install following tool(s) prior to modification.

- Docker
- Python3

1. Install pre-commit hook & necessary packages.

```bash
$ make clean

$ make .venv

...
```

2. Unit test code.

```bash

$ make test

...

```

3. Validate the app.

```bash

$ make validate # Validate

... # Should be no error/failures

```

## Tips

Splunk alert input sample:

```
    "session_key": "<SOME_VERY_LONG_GUID>",
    "configuration": {
        "assignment_group": "My assignment group..",
        "category": "Unauthorized access",
        "contact_type": "siem",
        "description": "",
        "environment": "dev",
        "from_raw": "0",
        "priority": "4",
        "roll_up_duration": "",
        "roll_up_match_fields": "",
        "roll_up_reopen": "0",
        "roll_up_rolling": "0",
        "severity": "2",
        "short_description": "My description yes?",
        "state": "10",
        "subcategory": "-99"
    },
    "result": {
        "_confstr": "source::/Applications/Splunk/var/spool/splunk/<random_guid>_events.stash_new|host::<HOSTNAME_HERE>|json",
        "_eventtype_color": "",
        "_indextime": "1620776262",
        "_raw": '{"some.field.1":"shawnkoon", "service.name":"test", "tags": [\"security\", \"application\"]}',
        "_serial": "0",
        "_si": ["<HOSTNAME_HERE>", "main"],
        "_sourcetype": "json",
        "_time": "1620776262",
        "eventtype": "",
        "host": "<HOSTNAME_HERE>",
        "index": "main",
        "linecount": "",
        "service.name": "test",
        "source": "/Applications/Splunk/var/spool/splunk/<random_guid>_events.stash_new",
        "sourcetype": "json",
        "splunk_server": "<HOSTNAME_HERE>",
        "tags{}": ["security", "application"],
        "timestamp": "none",
        "some.field.1": "shawnkoon"
    }
```

# Integration Testing Strategy 🐛

## Alert Setup:

Search Tearm :

```bash
index="main" service.name="test"
```

Alert Type : Real-time
Trigger alert when : Number of Results
Is greater than : 0
in 1 minute(s)
Trigger: Once
Throttle: Checked
Suppress triggering for: 60 second(s)

## Payload:

```bash
| makeresults
| eval _raw = "{\"strField\": \"string_fi\\\neld_val\", \"strField2\": \"string_field_val2\", \"listField\": [\"listt\", 123], \"objField\": { \"strField\": \"obj_str_field_val\", \"listField\": [\"uhm\", \"what\", 123]}, \"service\": {\"name\": \"test\"}}"
| collect index="main" sourcetype=json
```

## Test Cases

### No Rollup

- Raw: Yes
- Short Description: RAW !Rollup Test {{service.name}} {{strField}}
- Description: -RAW !Rollup Test- \n\nobjField: {{objField}}\nobjField.strField: {{objField.strField}}\nstrField: {{strField}}\nobjField.listField: {{objField.listField}}\nlistField: {{listField}}\n_raw: {{_raw}}\n\nRAW !Rollup Test END
- Severity:
  - High
  - Medium
  - Low
- Pirority: <ANY>
- Category:
  - Unauthorized access
  - UNKNOWN
  - Phishing
- SubCategory: -- None --
- Contact Type:

  - siem
  - UNKNOWN
  - Phone

- Raw: No
- Short Description: !Rollup Test {{service.name}} {{strField}}
- Description: -!Rollup Test- \n\nobjField: {{objField}}\nobjField.strField: {{objField.strField}}\nstrField: {{strField}}\nobjField.listField: {{objField.listField}}\nlistField: {{listField}}\n_raw: {{_raw}}\n\n!Rollup Test END
- Severity: <ANY>
- Priority:
  - Critical
  - High
  - Moderate
  - Low
  - Minor
- Category:
  - Unauthorized access
- Subcategory:
  - Abuse of access privileges (1)
  - Brute force password cracking attempts (3)
  - Stolen password(s) (30)
  - Unauthorized access to data (33)
  - Unauthorized login attemtps (34)
- Contact Type: siem

### With Rollup

- Raw: <ANY>
- Short Description: Rollup Test {{service.name}} {{strField}}
- Description: -Rollup Test- \n\nobjField: {{objField}}\nobjField.strField: {{objField.strField}}\nstrField: {{strField}}\nobjField.listField: {{objField.listField}}\nlistField: {{listField}}\n_raw: {{_raw}}\n\nRollup Test END
- Severity: <ANY>
- Priority: <ANY>
- Category: <ANY>
- Subcategory: <ANY>
- Contact Type: <ANY>

1. Test rollup duration.

- Roll Up Duration : 120
- Rolling: No
- Re Open: No
- Match Field(s): <EMPTY>

Create one more alert after 60 seconds.
Observe new alert rolls up, not create a new ticket

2. Test Rolling. (Roll rolling time)

- Roll Up Duration : 120
- Rolling: Yes
- Re Open: No
- Match Field(s): <EMPTY>

Create one more alert after 60 seconds.
Observe new alert rolls up, not create a new ticket

Create one more alert after 60 seconds.
Observe new alert rolls up, not create a new ticket

3. Test Re Open - No

- Roll Up Duration : 120
- Rolling: <ANY>
- Re Open: No
- Match Field(s): <EMPTY>

Update the status to something else other than "Draft (10)"
Create one more alert after 60 seconds.
Observe new alert rolls up, not create a new ticket, ticket state stays the same.

4. Test Re Open - Yes

- Roll Up Duration : 120
- Rolling: <ANY>
- Re Open: Yes
- Match Field(s): <EMPTY>

Update the status to something else other than "Draft (10)"
Create one more alert after 60 seconds.
Observe new alert rolls up, not create a new ticket, update ticket state back to "Draft"

5. Test Match Field(s)

- Roll Up Duration : 600
- Rolling: <ANY>
- Re Open: <ANY>
- Match Field(s): strField,service.name

Create one more alert after 60 seconds.
Observe new alert rolls up, not create a new ticket.
Continue to next test case before 600 seconds is up.

5. Test Match Field(s) - Different field

- Roll Up Duration : 600
- Rolling: <ANY>
- Re Open: <ANY>
- Match Field(s): strField2,service.name

Observe new ticket gets created
Create one more alert after 60 seconds.
Observe new alert rolls up, not create a new ticket.
