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
