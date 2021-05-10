import unittest
from dateutil.parser import parse as parse_date
from unittest.mock import MagicMock

from create_service_now_ticket import Request

MOCK_CREDENTIALS = ["username", "pass"]


def handle_paramaterized_function_asserts(c, exp):
    if "called" in exp:
        for func_name, value in exp["called"].items():
            getattr(c, func_name).assert_called_with(*value)
    if "not_called" in exp:
        for func_name in exp["not_called"]:
            getattr(c, func_name).assert_not_called()


def print_case_pass_fail(func):
    def wrapper(err, *args):
        print(args[0], end="... ")
        if err is None:
            try:
                func(*args)
                print("pass!")
                return None
            except Exception as e:
                print("failed.")
                err = e
        else:
            print("skipped.")
        return err

    return wrapper


class TestRequest(unittest.TestCase):
    def test_set_url(self):
        print("\nRunning: test_set_url")
        parameters = [
            # Case 1 - environment is not prod
            (
                "Case 1",
                {"environment": "", "table": "sometable"},
                "https://godaddydev.service-now.com/api/now/table/sometable",
            ),
            # Case 2 - environment is 'prod'
            (
                "Case 2",
                {"environment": "prod", "table": "sometable"},
                "https://godaddy.service-now.com/api/now/table/sometable",
            ),
        ]

        def test_case(case, _config, exp):
            r = Request(MOCK_CREDENTIALS)
            r._config = _config
            r._set_url()
            self.assertEqual(r._url, exp)

        err = None
        for (case, _config, exp) in parameters:
            err = print_case_pass_fail(test_case)(err, case, _config, exp)
        if err is not None:
            raise err

    def test_extract_config(self):
        print("\nRunning: test_extract_config")

        config_val1 = {}
        # {
        #     _config,
        #     _table_fields,
        #     exp functions
        # }
        parameters = [
            # Case 1: test empty
            # Even though this isn't expected, it will test at the same time
            # all cases being empty
            (
                "Case 1",
                {},
                {},
                {
                    "not_called": [
                        "_set_data_field",
                        "_set_data_replace",
                        "_set_data_datetime",
                    ]
                },
            ),
            # Case 2: test "direct" setting -
            # should call only _set_data_field
            (
                "Case 2",
                {"con": config_val1},
                {"direct": {"con": "snow"}},
                {
                    "called": {
                        "_set_data_field": ("snow", config_val1),
                    },
                    "not_called": ["_set_data_replace", "_set_data_datetime"],
                },
            ),
            # Case 3: test "string" setting -
            # should call only _set_data_replace
            (
                "Case 3",
                {"con": config_val1},
                {"string": {"con": "snow"}},
                {
                    "called": {"_set_data_replace": ("snow", config_val1, "con")},
                    "not_called": ["_set_data_field", "_set_data_datetime"],
                },
            ),
            # Case 4: test "datetime" setting -
            # should call only _set_data_datetime
            (
                "Case 4",
                {"con": config_val1},
                {"datetime": {"con": "snow"}},
                {
                    "called": {
                        "_set_data_datetime": ("snow", config_val1),
                    },
                    "not_called": [
                        "_set_data_field",
                        "_set_data_replace",
                    ],
                },
            ),
        ]

        def test_case(case, _config, _table_fields, exp):
            r = Request(MOCK_CREDENTIALS)
            r._config = _config
            r._table_fields = _table_fields

            r._set_data_field = MagicMock()
            r._set_data_replace = MagicMock()
            r._set_data_datetime = MagicMock()

            r._extract_config()

            handle_paramaterized_function_asserts(r, exp)

        err = None
        for (case, _config, _table_fields, exp) in parameters:
            err = print_case_pass_fail(test_case)(
                err, case, _config, _table_fields, exp
            )
        if err is not None:
            raise err

    def test_data(self):
        print("\nRunning: test_data")

        def test_case(*args):
            r = Request(MOCK_CREDENTIALS)
            r._set_data_field("k", "v")

            exp = {"k": "v"}

            self.assertEqual(r._data, exp)

        err = print_case_pass_fail(test_case)(None, ("Case 1"))
        if err is not None:
            raise err

    def test_data_replace(self):
        print("\nRunning: test_data_replace")
        parameters = [
            # Case 1 - with value -
            # should call _set_data_field and _replace_params
            (
                "Case 1",
                {"snow_field": "field", "value": "val", "config_field": "_"},
                {
                    "called": {
                        "_set_data_field": ("field", "_replace_params.returns"),
                        "_replace_params": ("val",),
                    }
                },
            ),
            # Case 2 - mapped value -
            # should replace the value with IPE ID from the MAPS constant
            (
                "Case 2",
                {
                    "snow_field": "u_assignment_field",
                    "value": "ENG-IPE",
                    "config_field": "ticket_assignment_group",
                },
                {
                    "called": {
                        "_set_data_field": (
                            "u_assignment_field",
                            "2a9cd2534f19fe00dc4927201310c76e",
                        ),
                    },
                    "not_called": ["_replace_params"],
                },
            ),
            # Case 3 - empty string -
            # should not call _set_data_field and _replace_params
            (
                "Case 3",
                {"snow_field": "field", "value": "", "config_field": "_"},
                {"not_called": ["_set_data_field", "_replace_params"]},
            ),
            # Case 4 - with None -
            # should not call _set_data_field and _replace_params
            (
                "Case 4",
                {"snow_field": "field", "value": None, "config_field": "_"},
                {"not_called": ["_set_data_field", "_replace_params"]},
            ),
        ]

        def test_case(case, values, exp):
            r = Request(MOCK_CREDENTIALS)
            r._set_data_field = MagicMock()
            r._replace_params = MagicMock(return_value="_replace_params.returns")

            r._set_data_replace(**values)

            handle_paramaterized_function_asserts(r, exp)

        err = None
        for (case, values, exp) in parameters:
            err = print_case_pass_fail(test_case)(err, case, values, exp)
        if err is not None:
            raise err

    def test_set_data_datetime(self):
        print("\nRunning: test_set_data_datetime")
        some_time = "2006-01-02T15:04:05"
        some_time_in_snow = "2006-01-02 15:04:05"
        _result = {"_time": 1136214245.000}
        parameters = [
            # Case 1 - with 'now' - value = 'now'
            (
                "Case 1",
                {
                    "snow_field": "field",
                    "value": "now",
                    "now": parse_date("2006-01-02T15:04:05"),
                },
                {
                    "called": {"_set_data_field": ("field", some_time_in_snow)},
                    "not_called": ["_extract_field"],
                },
            ),
            # Case 2 - with value - value = '_time'
            (
                "Case 2",
                {"snow_field": "field", "value": "_time", "now": "0"},
                {
                    "called": {"_set_data_field": ("field", some_time_in_snow)},
                    "not_called": ["_extract_field"],
                },
            ),
            # Case 2 - with value - value = *
            (
                "Case 2",
                {"snow_field": "field", "value": "some.value", "now": "0"},
                {
                    "called": {
                        "_extract_field": ("some.value",),
                        "_set_data_field": ("field", some_time_in_snow),
                    },
                },
            ),
            # Case 3 - with none - value = None
            (
                "Case 3",
                {"snow_field": "field", "value": None, "now": "0"},
                {"not_called": ["_set_data_field", "_extract_field"]},
            ),
            # Case 4 - with empty string - value = ''
            (
                "Case 4",
                {"snow_field": "field", "value": "", "now": "0"},
                {"not_called": ["_set_data_field", "_extract_field"]},
            ),
        ]

        def test_case(case, values, exp):
            r = Request(MOCK_CREDENTIALS)
            r._result = _result
            r._set_data_field = MagicMock()
            r._extract_field = MagicMock(return_value=some_time)

            r._set_data_datetime(**values)

            handle_paramaterized_function_asserts(r, exp)

        err = None
        for (case, values, exp) in parameters:
            err = print_case_pass_fail(test_case)(err, case, values, exp)
        if err is not None:
            raise err

    def test_replace_params(self):
        print("\nRunning: test_replace_params")

        _replace_params_returns = "returned"
        parameters = [
            # Case 1 - No regex match & no newlinw -
            # string without "{{}}" and \n
            (
                "Case 1",
                {"string": "Some string."},
                {"not_called": ["_replace_next_param"], "got": "Some string."},
            ),
            # Case 2 - No regex match & newlinw -
            # string without "{{}}"
            (
                "Case 2",
                {"string": "Some\\nstring."},
                {"not_called": ["_replace_next_param"], "got": "Some\nstring."},
            ),
            # Case 3 - regex match & newlinw -
            # string with "{{}}"
            (
                "Case 3",
                {"string": "{{some.string}}"},
                {
                    "called": {"_replace_next_param": ("{{some.string}}",)},
                    "got": _replace_params_returns,
                },
            ),
        ]

        def test_case(case, values, exp):
            r = Request(MOCK_CREDENTIALS)
            r._replace_next_param = MagicMock(return_value=_replace_params_returns)

            got = r._replace_params(**values)

            handle_paramaterized_function_asserts(r, exp)
            self.assertEqual(got, exp["got"])

        err = None
        for (case, values, exp) in parameters:
            err = print_case_pass_fail(test_case)(err, case, values, exp)
        if err is not None:
            raise err

    def test_replace_next_param(self):
        print("\nRunning: test_replace_next_param")
        _event = {
            "field_one": "value1",
            "field.two": "value2",
        }
        parameters = [
            # Case 1 - field = "_raw"
            (
                "Case 1",
                {"param_string": "some {{_raw}}"},
                {"_parse_raw": False, "_parse_param": "_raw", "_extract_field": "_"},
                {
                    "called": {"_parse_param": ("some {{_raw}}",)},
                    "not_called": ["_extract_field"],
                    "got": 'some {"field_one": "value1", "field.two": "value2"}',
                },
            ),
            # Case 2 - field contains '.' and _parse_raw = True
            # _extract_field returns string
            (
                "Case 2",
                {"param_string": "some {{field.two}}"},
                {
                    "_parse_raw": True,
                    "_parse_param": "field.two",
                    "_extract_field": "value3",
                },
                {
                    "called": {
                        "_parse_param": ("some {{field.two}}",),
                        "_extract_field": ("field.two",),
                    },
                    "got": "some value3",
                },
            ),
            # Case 3 - field contains '.' and _parse_raw = False
            # _extract_field returns string
            (
                "Case 3",
                {"param_string": "some {{field.two}}"},
                {
                    "_parse_raw": False,
                    "_parse_param": "field.two",
                    "_extract_field": "value3",
                },
                {
                    "called": {
                        "_parse_param": ("some {{field.two}}",),
                    },
                    "got": "some value2",
                },
            ),
            # Case 4 - field contains '.'
            # _extract_field returns dict
            (
                "Case 4",
                {"param_string": "some {{field.three}}"},
                {
                    "_parse_raw": True,
                    "_parse_param": "field.three",
                    "_extract_field": {"some": "dict"},
                },
                {
                    "called": {
                        "_parse_param": ("some {{field.three}}",),
                        "_extract_field": ("field.three",),
                    },
                    "got": 'some {"some": "dict"}',
                },
            ),
            # Case 5 - field does not contain '.'
            (
                "Case 5",
                {"param_string": "some {{field_one}}"},
                {
                    "_parse_raw": False,
                    "_parse_param": "field_one",
                    "_extract_field": "_",
                },
                {
                    "called": {"_parse_param": ("some {{field_one}}",)},
                    "not_called": ["_extract_field"],
                    "got": "some value1",
                },
            ),
        ]

        err = None

        def test_case(case, values, returns, exp):
            r = Request(MOCK_CREDENTIALS)
            r._event = _event
            r._parse_raw = returns["_parse_raw"]
            r._parse_param = MagicMock(return_value=returns["_parse_param"])
            r._extract_field = MagicMock(return_value=returns["_extract_field"])

            got = r._replace_next_param(**values)

            handle_paramaterized_function_asserts(r, exp)

            self.assertEqual(got, exp["got"])

        for (case, values, returns, exp) in parameters:
            err = print_case_pass_fail(test_case)(err, case, values, returns, exp)

        if err is not None:
            raise err

    def test_parse_param(self):
        print("\nRunning: test_parse_param")
        parameters = [
            ("Case 1", {"param_string": "{{some.string}}"}, "some.string"),
            ("Case 2", {"param_string": "a {{some.string}} b"}, "some.string"),
            ("Case 3", {"param_string": "a {{some}} b {{string}} c"}, "some"),
        ]

        def test_case(case, values, exp):
            r = Request(MOCK_CREDENTIALS)

            got = r._parse_param(**values)

            self.assertEqual(got, exp)

        err = None
        for (case, values, exp) in parameters:
            err = print_case_pass_fail(test_case)(err, case, values, exp)
        if err is not None:
            raise err

    def test_extract_field(self):
        print("\nRunning: test_extract_field")
        _event = {
            "case_one": "value1",
            "case": {"two": "value2", "three": {"value": "3"}},
        }

        parameters = [
            # Case 1 - No '.'
            ("Case 1", {"field_path": "case_one"}, "value1"),
            # Case 2 - One '.'
            ("Case 2", {"field_path": "case.two"}, "value2"),
            # Case 3 - Multiple '.'
            ("Case 3", {"field_path": "case.three.value"}, "3"),
        ]

        def test_case(case, values, exp):
            r = Request(MOCK_CREDENTIALS)
            r._event = _event

            got = r._extract_field(**values)

            self.assertEqual(got, exp)

        err = None
        for (case, values, exp) in parameters:
            err = print_case_pass_fail(test_case)(err, case, values, exp)
        if err is not None:
            raise err


if __name__ == "__main__":
    unittest.main()
