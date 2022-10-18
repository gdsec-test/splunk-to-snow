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

3. [Validate](https://dev.splunk.com/enterprise/docs/developapps/testvalidate/appinspect/useappinspectclitool/#Validate-a-Splunk-app) the app.

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

## Pre-req

- Register an account via https://www.splunk.com/ using godaddy email address.
- Request "Personalized Dev/Test Licenses for Splunk Customers".
  - FAQ : https://www.splunk.com/en_us/resources/personalized-dev-test-licenses/faq.html
  - Req : https://www.splunk.com/en_us/resources/personalized-dev-test-licenses.html?301=/dev-test
  - **Note:**
    - If no email received even after multiple re-requests - Resetting splunk account password & re-requesting license fixed issue for me 9/12/2022.
- Install splunk-enterprise software for your Operating System (OS).
  - https://www.splunk.com/en_us/download/splunk-enterprise.html
- Once installed, add license as instructed in the email you received.

## Install local version of the app

1. Build application.
   ```bash
   $ make package
   ```
2. Navigate to apps page (Splunk Enterprise v9.0.1 atm)
   - http://localhost:8000/en-US/manager/launcher/apps/local
3. Click the `Install app from file` button on right top of the page.
4. Upload the `splunk_to_snow.spl` file built from Step 1.
   - Check `Upgrade app` checkbox.
5. Click the `Upload` button, you will then see a page that says "App setup required"
6. Click the `Set up now` button.
   - Setup page is based on what is inside of [src/appserver/](./src/appserver/)
7. Navigate to dev-private AWS account, identify dev ServiceNOW/CMDB AWS Secrets Manager (ASM).
8. Enter username & password you got from dev cmdb ASM into setup page form.
9. Validate that apps page (Step 2) reflects latest [version](./src/default/app.conf) of the app you are testing.
   - You will see `Set up` (Splunk Enterprise v9.0.1 atm) hyperlink on the right side of your app row as well. If you need to update ServiceNOW/CMDB credential.

## Alert Setup:

1. Navigate to search page.
   - http://localhost:8000/en-US/app/search/search
2. Enter the following Search Processing Language (SPL) & hit magnifying glass icon to search.
   ```bash
   index="main" service.name="test"
   ```
3. Click the `Save As` dropdown.
4. Click the `Alert` dropdown menu item.
5. Fill in the Alert `Settings`:
   - `Title`: splunk-to-snow test alert
   - `Permissions`: Shared in App
   - `Alert Type`: Real-time
   - `Expires`: 24 hours (define the lifespan of triggered Alert basically how long you can access the result of triggered alert.)
6. Fill in the Alert `Trigger Conditions`:
   - `Trigger alert when`: Number of Results
     - `is greater than`: 0
     - `in`: 1 minute(s) (Will help when testing batch logs)
     - `Trigger`: Once
     - `Trottle`: Checked
     - `Suppress triggering for`: 60 second(s)
7. Add `Trigger Actions` by clicking `+ Add Actions`
   - Select `Create ServiceNOW SIR Ticket` action.
   - You will be updating alert action settings in later step(s).
8. Hit `Save`.
9. You can view alerts at anytime & configure them.
   - http://localhost:8000/en-US/app/search/alerts

## Payload:

Use following SPL to generate a record which will trigger alert you setup above.

**But please, first follow the "Test Cases" step below to finish configuring the alert**

```bash
| makeresults
| eval _raw = "{\"strField\": \"string_fi\\\neld_val\", \"strField2\": \"string_field_val2\", \"listField\": [\"listt\", 123], \"objField\": { \"strField\": \"obj_str_field_val\", \"listField\": [\"uhm\", \"what\", 123]}, \"service\": {\"name\": \"test\"}}"
| collect index="main" sourcetype=json
```

## Test Cases

> Fields with `[ANY]` indicates, possible permutations needs to be tested.
>
> All alerts can be viewed https://godaddydev.service-now.com/nav_to.do?uri=%2Fsn_si_incident_list.do%3Fsysparm_query%3Dassignment_group%253D70e5dc8413d41094f8b076666144b0e5%26sysparm_first_row%3D1%26sysparm_view%3D

### Common alert settings:

- Environment: `Dev`
- Assignment Group: `ENG-Product Security`

### No Rollup

- Alert test w/ RAW enabled.
  - Raw: Yes
  - Short Description: `RAW !Rollup Test {{service.name}} {{strField}}`
  - Description: `-RAW !Rollup Test- \n\nobjField: {{objField}}\nobjField.strField: {{objField.strField}}\nstrField: {{strField}}\nobjField.listField: {{objField.listField}}\nlistField: {{listField}}\n_raw: {{_raw}}\n\nRAW !Rollup Test END`
  - Severity: [ANY]
  - Pirority: [ANY]
  - Category:
    - Unauthorized access
    - UNKNOWN
    - Phishing
  - SubCategory: [ANY]
  - Contact Type:
    - siem
    - UNKNOWN
    - Phone
- Alert test w/ RAW disabled.
  - Raw: No
  - Short Description: `!Rollup Test {{service.name}} {{strField}}`
  - Description: `-!Rollup Test- \n\nobjField: {{objField}}\nobjField.strField: {{objField.strField}}\nstrField: {{strField}}\nobjField.listField: {{objField.listField}}\nlistField: {{listField}}\n_raw: {{_raw}}\n\n!Rollup Test END`
  - Severity: [ANY]
  - Priority: [ANY]
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

- Raw: [ANY]
- Short Description: `Rollup Test {{service.name}} {{strField}}`
- Description: `-Rollup Test- \n\nobjField: {{objField}}\nobjField.strField: {{objField.strField}}\nstrField: {{strField}}\nobjField.listField: {{objField.listField}}\nlistField: {{listField}}\n_raw: {{_raw}}\n\nRollup Test END`
- Severity: [ANY]
- Priority: [ANY]
- Category: [ANY]
- Subcategory: [ANY]
- Contact Type: [ANY]

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
- Rolling: [ANY]
- Re Open: No
- Match Field(s): <EMPTY>

Update the status to something else other than "Draft (10)"
Create one more alert after 60 seconds.
Observe new alert rolls up, not create a new ticket, ticket state stays the same.

4. Test Re Open - Yes

- Roll Up Duration : 120
- Rolling: [ANY]
- Re Open: Yes
- Match Field(s): <EMPTY>

Update the status to something else other than "Draft (10)"
Create one more alert after 60 seconds.
Observe new alert rolls up, not create a new ticket, update ticket state back to "Draft"

5. Test Match Field(s)

- Roll Up Duration : 600
- Rolling: [ANY]
- Re Open: [ANY]
- Match Field(s): strField,service.name

Create one more alert after 60 seconds.
Observe new alert rolls up, not create a new ticket.
Continue to next test case before 600 seconds is up.

5. Test Match Field(s) - Different field

- Roll Up Duration : 600
- Rolling: [ANY]
- Re Open: [ANY]
- Match Field(s): strField2,service.name

Observe new ticket gets created
Create one more alert after 60 seconds.
Observe new alert rolls up, not create a new ticket.
