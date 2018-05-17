#!/usr/bin/env python3
# Author: William Henning <whenning@google.com>

import re
import os
import sys
import platform
from collections import defaultdict

# parse_test_results.py overview
#
# usage:
#    python parse_test_results.py
#
# This script parses the validation layers tests and reports the number of
# passes, failures, unexpected errors, and skipped tests.

class OutputStats(object):
  def __init__(self):
    self.current_profile = ""
    self.current_test = ""
    self.current_test_output = ""
    self.test_results = defaultdict(defaultdict)
    self.unexpected_errors = defaultdict(defaultdict)

  def match(self, line):
    self.new_profile_match(line)
    self.test_suite_end_match(line)
    self.start_test_match(line)
    if self.current_test != "":
      self.current_test_output += line
    self.skip_test_match(line)
    self.pass_test_match(line)
    self.fail_test_match(line)
    self.unexpected_error_match(line)

  def print_summary(self):
    if self.current_test != "":
      self.test_died()

    passed_tests = 0
    skipped_tests = 0
    failed_tests = 0
    unexpected_error_tests = 0
    did_fail = False

    for test_name, results in self.test_results.items():
      skipped_profiles = 0
      passed_profiles = 0
      failed_profiles = 0
      aborted_profiles = 0
      unexpected_error_profiles = 0
      for profile, result in results.items():
        if result == "pass":
          passed_profiles += 1
        if result == "fail":
          failed_profiles += 1
        if result == "skip":
          skipped_profiles += 1
        if self.unexpected_errors.get(test_name, {}).get(profile, "") == "true":
          unexpected_error_profiles += 1
      if failed_profiles != 0:
        print("TEST FAILED:", test_name)
        failed_tests += 1
      elif skipped_profiles == len(results):
        print("TEST SKIPPED ALL DEVICES:", test_name)
        skipped_tests += 1
      else:
        passed_tests += 1
      if unexpected_error_profiles != 0:
        print("UNEXPECTED ERRORS:", test_name)
        unexpected_error_tests += 1
    num_tests = len(self.test_results)
    print("PASSED: ", passed_tests, "/", num_tests, " tests")
    if skipped_tests != 0:
      did_fail = True
      print("NEVER RAN: ", skipped_tests, "/", num_tests, " tests")
    if failed_tests != 0:
      did_fail = True
      print("FAILED: ", failed_tests, "/", num_tests, "tests")
    if unexpected_error_tests != 0:
      did_fail = True
      print("UNEXPECTED OUPUT: ", unexpected_error_tests, "/", num_tests, "tests")
    return did_fail

  def new_profile_match(self, line):
    if re.search(r'Testing with profile .*/(.*)', line) != None:
      self.current_profile = re.search(r'Testing with profile .*/(.*)', line).group(1)

  def test_suite_end_match(self, line):
    if re.search(r'\[-*\]', line) != None:
      if self.current_test != "":
        # Here we see a message that starts [----------] before another test
        # finished running. This should mean that that other test died.
        self.test_died()

  def start_test_match(self, line):
    if re.search(r'\[ RUN\s*\]', line) != None:
      # This parser doesn't handle the case where one test's start comes between another test's start and result.
      assert self.current_test == ""
      self.current_test = re.search(r'] (.*)', line).group(1)
      self.current_test_output = ""

  def skip_test_match(self, line):
    if re.search(r'TEST_SKIPPED', line) != None:
      self.test_results[self.current_test][self.current_profile] = "skip"

  def pass_test_match(self, line):
    if re.search(r'\[\s*OK \]', line) != None:
      # If gtest says the test passed, check if it was skipped before marking it passed
      if self.test_results.get(self.current_test, {}).get(self.current_profile, "") != "skip":
          self.test_results[self.current_test][self.current_profile] = "pass"
      self.current_test = ""

  def fail_test_match(self, line):
    if re.search(r'\[\s*FAILED\s*\]', line) != None and self.current_test != "":
      self.test_results[self.current_test][self.current_profile] = "fail"
      self.current_test = ""

  def unexpected_error_match(self, line):
    if re.search(r'^Unexpected: ', line) != None:
      self.unexpected_errors[self.current_test][self.current_profile] = "true"

  def test_died(self):
    print("A test likely crashed. Testing is being aborted.")
    print("Final test output: ")
    print(self.current_test_output)
    exit(1)

def main():
  stats = OutputStats()
  for line in sys.stdin:
    stats.match(line)
  failed = stats.print_summary()
  if failed == True:
    print("\nFAILED CI")
    exit(1)

if __name__ == '__main__':
  main()
