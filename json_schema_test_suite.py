#!/usr/bin/env python

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from collections import defaultdict
from textwrap import dedent
import json
import sys
import unittest

try:
    from pathlib import Path
except ImportError:
    from pathlib2 import Path

import fastjsonschema


class Draft4TestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tests_dir_path = Path().resolve() / "JSON-Schema-Test-Suite/tests/draft4"
        cls.tests = {
            "files": 0,
            "cases": 0,
            "tests": 0
        }
        cls.exceptions = defaultdict(dict)

    @classmethod
    def tearDownClass(cls):
        if cls.exceptions:
            print("\nFailure summary:")
            file_exceptions = test_case_exceptions = total_exceptions = 0
            for file_name, test_cases in cls.exceptions.items():
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
                total_exceptions, cls.tests["tests"], total_exceptions / cls.tests["tests"],
                test_case_exceptions, cls.tests["cases"], test_case_exceptions / cls.tests["cases"],
                file_exceptions, cls.tests["files"], file_exceptions / cls.tests["files"])
            )

    def test_validate(self):
        test_files_glob = self.tests_dir_path.glob("*.json")
        for test_file_path in test_files_glob:
            with test_file_path.open() as f:
                self.tests["files"] += 1
                test_data = json.loads(f.read())
                for test_case in test_data:
                    self.tests["cases"] += 1
                    test_case_description = test_case["description"]
                    schema = test_case["schema"]
                    try:
                        validate = fastjsonschema.compile(schema)
                    except Exception as e:
                        if "fastjsonschema" not in self.exceptions[test_file_path.name]:
                            self.exceptions[test_file_path.name]["fastjsonschema"] = []
                        self.exceptions[test_file_path.name]["fastjsonschema"].append("{}: {}".format(test_case_description, e))
                    for test in test_case["tests"]:
                        self.tests["tests"] += 1
                        description = test["description"]
                        data = test["data"]
                        try:
                            if test["valid"]:
                                validate(data)
                            else:
                                with self.assertRaises(fastjsonschema.exceptions.JsonSchemaException):
                                    validate(data)
                        except Exception as e:
                            if test_case_description not in self.exceptions[test_file_path.name]:
                                self.exceptions[test_file_path.name][test_case_description] = []
                            self.exceptions[test_file_path.name][test_case_description].append("{}: {}".format(description, e))


if __name__ == "__main__":
    unittest.main(verbosity=2)
