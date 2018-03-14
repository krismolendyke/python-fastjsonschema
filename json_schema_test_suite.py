#!/usr/bin/env python -u
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

from colorama import Fore
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
    p.add_argument("--tests", help="Run tests in this directory or file", type=Path,
                   default=Path().resolve() / "JSON-Schema-Test-Suite/tests/draft4")
    p.add_argument("--verbose", help="Print passing tests", action="store_true")
    return p


def _main():
    if args.tests.is_dir():
        test_file_paths = list(args.tests.glob("*.json"))
    elif args.tests.is_file():
        test_file_paths = [args.tests.resolve()]
    else:
        return args.tests + " must be a directory or a file"
    tests = defaultdict(dict)
    schema_exceptions = {}
    for test_file_path in test_file_paths:
        with test_file_path.open() as f:
            tests[test_file_path.name] = defaultdict(dict)
            test_data = json.loads(f.read())
            for test_case in test_data:
                test_case_description = test_case["description"]
                schema = test_case["schema"]
                tests[test_file_path.name][test_case_description] = []
                try:
                    validate = fastjsonschema.compile(schema)
                except Exception as e:
                    schema_exceptions[test_file_path.name] = e
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
                    tests[test_file_path.name][test_case_description].append(Test(description, exception, result))

    test_results = Counter()
    for file_name, test_cases in tests.items():
        for test_case in test_cases.values():
            if any(t for t in test_case if t.result in (TestResult.FALSE_POSITIVE, TestResult.FALSE_NEGATIVE)):
                print(Fore.RED + "✘" + Fore.RESET, file_name)
                break
            elif any(t for t in test_case if t.result == TestResult.UNDEFINED):
                print(Fore.YELLOW + "⚠" + Fore.RESET, file_name)
                break
            else:
                print(Fore.GREEN + "✔" + Fore.RESET, file_name)
                break
        for test_case_description, test_case in test_cases.items():
            if any(t for t in test_case if t.result in (TestResult.FALSE_POSITIVE, TestResult.FALSE_NEGATIVE)):
                print("  " + Fore.RED + "✘" + Fore.RESET, test_case_description)
            elif any(t for t in test_case if t.result == TestResult.UNDEFINED):
                print("  " + Fore.YELLOW + "⚠" + Fore.RESET, test_case_description)
            elif args.verbose:
                print("  " + Fore.GREEN + "✔" + Fore.RESET, test_case_description)
            for test in test_case:
                test_results.update({test.result: 1})
                if test.result in (TestResult.FALSE_POSITIVE, TestResult.FALSE_NEGATIVE):
                    print("    " + Fore.RED + "✘" + Fore.RESET,
                          Fore.CYAN + test.result.name + Fore.RESET,
                          Fore.RED + type(test.exception).__name__ + Fore.RESET,
                          "{}: {}".format(test.description, test.exception))
                elif test.result == TestResult.UNDEFINED:
                    print("    " + Fore.YELLOW + "⚠" + Fore.RESET,
                          Fore.CYAN + test.result.name + Fore.RESET,
                          Fore.YELLOW + type(test.exception).__name__ + Fore.RESET,
                          "{}: {}".format(test.description, test.exception))
                elif args.verbose:
                    print("    " + Fore.GREEN + "✔" + Fore.RESET,
                          Fore.CYAN + test.result.name + Fore.RESET,
                          test.description)

    if schema_exceptions:
        print("\nSchema exceptions:\n")
        for file_name, exception in schema_exceptions.items():
            print("  " + Fore.RED + "✘" + Fore.RESET,
                  "{}: {}: '{}'".format(file_name, exception, exception.text.strip()))

    total = sum(test_results.values())
    total_failures = total_passes = 0
    print("\nSummary of {} tests:\n".format(total))
    print("Failures:\n")
    for result in (TestResult.FALSE_POSITIVE, TestResult.FALSE_NEGATIVE, TestResult.UNDEFINED):
        total_failures += test_results[result]
        if result == TestResult.UNDEFINED:
            print("  " + Fore.YELLOW + "⚠", end=" ")
        else:
            print("  " + Fore.RED + "✘", end=" ")
        print(Fore.CYAN + "{:<14}".format(result.name) + Fore.RESET,
              "{} {:>5.1%}".format(test_results[result], test_results[result] / total))
    print("                   {} {:>5.1%}".format(total_failures, total_failures / total))
    print("\nPasses:\n")
    for result in (TestResult.TRUE_POSITIVE, TestResult.TRUE_NEGATIVE):
        total_passes += test_results[result]
        print("  " + Fore.GREEN + "✔",
              Fore.CYAN + "{:<14}".format(result.name) + Fore.RESET,
              "{} {:>5.1%}".format(test_results[result], test_results[result] / total))
    print("                   {} {:5.1%}".format(total_passes, total_passes / total))


if __name__ == "__main__":
    args = _get_parser().parse_args()
    sys.exit(_main())
