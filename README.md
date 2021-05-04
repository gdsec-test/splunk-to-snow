# splunk-to-snow
| main |
| --- |
| [![Build Workflow](https://github.com/gdcorp-infosec/splunk-to-snow/actions/workflows/build.yml/badge.svg?branch=main)](https://github.com/gdcorp-infosec/splunk-to-snow/actions/workflows/build.yml) |

Splunk to ServiceNow App

## How to contribute 💻

Please install following tool(s) prior to modification.

- Docker
- Python3

1. Install pre-commit hook.

```bash
$ python3 -m venv .venv # Create new python virtual envrionment

$ source .venv/bin/activate # Activate virtual envrionment

(.venv) $ pip install --upgrade pip # Upgrade pip

(.venv) $ pip install -r requirements.txt # Install required dependencies

(.venv) $ pre-commit install # Install pre-commit hook to your local env
```

2. Validate the app.

```bash

$ make validate # Validate

```
