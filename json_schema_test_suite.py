#!/usr/bin/env python
# coding: utf-8

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from collections import Counter, defaultdict, namedtuple
from textwrap import dedent
import argparse
import json
import sys

try:
    from enum import Enum, auto
except ImportError:
    from enum34 import Enum, auto

try:
    from pathlib import Path
except ImportError:
    from pathlib2 import Path

import fastjsonschema

class TestResult(Enum):
    FALSE_POSITIVE = auto()
    TRUE_POSITIVE = auto()
    FALSE_NEGATIVE = auto()
    TRUE_NEGATIVE = auto()
    UNDEFINED = auto()

Test = namedtuple("Test", "description exception result")


def _get_parser():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    p.add_argument("--test", help="Run a specific test only", type=Path)
    return p


def _main():
    tests_dir_path = Path().resolve() / "JSON-Schema-Test-Suite/tests/draft4"
    tests_ = defaultdict(dict)
    test_files_glob = tests_dir_path.glob("*.json")
    for test_file_path in test_files_glob:
        with test_file_path.open() as f:
            tests_[test_file_path.name] = defaultdict(dict)
            test_data = json.loads(f.read())
            for test_case in test_data:
                test_case_description = test_case["description"]
                schema = test_case["schema"]
                tests_[test_file_path.name][test_case_description] = []
                try:
                    validate = fastjsonschema.compile(schema)
                except Exception as e:
                    pass  # TODO record undefined schema exceptions
                for test in test_case["tests"]:
                    description = test["description"]
                    data = test["data"]
                    result = exception = None
                    try:
                        if test["valid"]:
                            try:
                                validate(data)
                                result = TestResult.TRUE_POSITIVE
                            except fastjsonschema.exceptions.JsonSchemaException as e:
                                result = TestResult.FALSE_NEGATIVE
                                exception = e
                        else:
                            try:
                                validate(data)
                                result = TestResult.FALSE_POSITIVE
                            except fastjsonschema.exceptions.JsonSchemaException as e:
                                result = TestResult.TRUE_NEGATIVE
                                exception = e
                    except Exception as e:
                        result = TestResult.UNDEFINED
                        exception = e
                    tests_[test_file_path.name][test_case_description].append(Test(description, exception, result))

    file_exceptions = test_case_exceptions = total_exceptions = 0
    test_results = Counter()
    for file_name, test_cases in tests_.items():
        file_exceptions += 1
        print("\n{}. {}".format(file_exceptions, file_name))
        j = 0
        for test_case_description, test_case in test_cases.items():
            j += 1
            test_case_exceptions += 1
            print("    {}. {}".format(j, test_case_description))
            for i, test in enumerate(test_case, 1):
                test_results.update({test.result: True})
                if test.result == TestResult.TRUE_POSITIVE:
                    print("        {}. ✔ {} {}".format(i, test.result.name, test.description))
                elif test.result == TestResult.TRUE_NEGATIVE:
                    print("        {}. ✔ {} {}".format(i, test.result.name, test.description))
                elif test.result == TestResult.FALSE_POSITIVE:
                    print("        {}. ✘ {} [{}] {}: {}".format(i, test.result.name, type(test.exception).__name__, test.description, test.exception))
                elif test.result == TestResult.FALSE_NEGATIVE:
                    print("        {}. ✘ {} [{}] {}: {}".format(i, test.result.name, type(test.exception).__name__, test.description, test.exception))
                elif test.result == TestResult.UNDEFINED:
                    print("        {}. ⚠ {} [{}] {}: {}".format(i, test.result.name, type(test.exception).__name__, test.description, test.exception))
                else:
                    print("        {}. 💀 DEATH")  # WTF

    total = sum(test_results.values())
    total_failures = total_passes = 0
    print("\nSummary of {} tests:\n".format(total))
    print("Failures:\n")
    for result in (TestResult.FALSE_POSITIVE, TestResult.FALSE_NEGATIVE, TestResult.UNDEFINED):
        total_failures += test_results[result]
        print("{:<14} {} {:>5.1%}".format(result.name, test_results[result], test_results[result] / total))
    print("               {} {:>5.1%}".format(total_failures, total_failures / total))
    print("\nPasses:\n")
    for result in (TestResult.TRUE_POSITIVE, TestResult.TRUE_NEGATIVE):
        total_passes += test_results[result]
        print("{:<13} {} {:5.1%}".format(result.name, test_results[result], test_results[result] / total))
    print("              {} {:5.1%}".format(total_passes, total_passes / total))


if __name__ == "__main__":
    args = _get_parser().parse_args()
    sys.exit(_main())
