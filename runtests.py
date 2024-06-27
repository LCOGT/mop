# Based on an example in Django's documentation:
# https://docs.djangoproject.com/en/4.2/topics/testing/advanced/#testing-reusable-applications

#!/usr/bin/env python
import os
import sys
import argparse
import django
from django.conf import settings
from django.test.utils import get_runner

def get_args():

    parser = argparse.ArgumentParser()
    parser.add_argument('module', help='name of module to test or all')
    options = parser.parse_args()

    return options

if __name__ == "__main__":
    options = get_args()
    os.environ["DJANGO_SETTINGS_MODULE"] = "tests.test_settings"
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=1)
    if options.module == 'all':
        failures = test_runner.run_tests(["tests"])
    else:
        failures = test_runner.run_tests([options.module])
    sys.exit(bool(failures))