#!/usr/bin/env python

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from collections import defaultdict
from textwrap import dedent
import argparse
import json
import sys

try:
    from pathlib import Path
except ImportError:
    from pathlib2 import Path

import fastjsonschema


def _get_parser():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    p.add_argument("--test", help="Run a specific test only", type=Path)
    return p


def _main():
    blacklist = [
        "additionalProperties",
        "definitions",
        "dependencies",
        "patternProperties",
    ]
    tests_dir_path = Path().resolve() / "JSON-Schema-Test-Suite/tests/draft4"
    tests = {
        "files": 0,
        "cases": 0,
        "tests": 0
    }
    exceptions = defaultdict(dict)

    test_files_glob = tests_dir_path.glob("*.json")
    for test_file_path in test_files_glob:
        if test_file_path.stem not in blacklist:
            with test_file_path.open() as f:
                tests["files"] += 1
                test_data = json.loads(f.read())
                for test_case in test_data:
                    tests["cases"] += 1
                    test_case_description = test_case["description"]
                    schema = test_case["schema"]
                    try:
                        validate = fastjsonschema.compile(schema)
                    except Exception as e:
                        if "fastjsonschema" not in exceptions[test_file_path.name]:
                            exceptions[test_file_path.name]["fastjsonschema"] = []
                        exceptions[test_file_path.name]["fastjsonschema"].append("{}: {}".format(test_case_description, e))
                    for test in test_case["tests"]:
                        tests["tests"] += 1
                        description = test["description"]
                        data = test["data"]
                        try:
                            if test["valid"]:
                                validate(data)
                            else:
                                try:
                                    validate(data)
                                except fastjsonschema.exceptions.JsonSchemaException:
                                    pass  # Expected to be invalid
                        except Exception as e:
                            if test_case_description not in exceptions[test_file_path.name]:
                                exceptions[test_file_path.name][test_case_description] = []
                            exceptions[test_file_path.name][test_case_description].append("{}: {}".format(description, e))

    print("\nSkipped:\n")
    for i, name in enumerate(blacklist, 1):
        print("{}. {}.json".format(i, name))
    if exceptions:
        print("\nFailure summary:")
        file_exceptions = test_case_exceptions = total_exceptions = 0
        for file_name, test_cases in exceptions.items():
            file_exceptions += 1
            print("\n{}. {}".format(file_exceptions, file_name))
            j = 0
            for test_case_description, failures in test_cases.items():
                j += 1
                test_case_exceptions += 1
                print("    {}. {}".format(j, test_case_description))
                for i, failure in enumerate(failures, 1):
                    total_exceptions += 1
                    print("        {}. {}".format(i, failure))
        sys.exit(dedent("""
        Failures:
            tests: {}/{} {:.1%}
            cases: {}/{} {:.1%}
            files: {}/{} {:.1%}\
        """).format(
            total_exceptions, tests["tests"], total_exceptions / tests["tests"],
            test_case_exceptions, tests["cases"], test_case_exceptions / tests["cases"],
            file_exceptions, tests["files"], file_exceptions / tests["files"])
        )


if __name__ == "__main__":
    args = _get_parser().parse_args()
    sys.exit(_main())
