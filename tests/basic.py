import unittest

import os

# Set the DJANGO_SETTINGS_MODULE environment variable.
os.environ['DJANGO_SETTINGS_MODULE'] = "mock_settings"

import rest_framework
class TestTest(unittest.TestCase):
    def test_nothing_much(self):
        pass