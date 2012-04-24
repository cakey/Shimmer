import unittest
import json

import os

# Set the DJANGO_SETTINGS_MODULE environment variable.
os.environ['DJANGO_SETTINGS_MODULE'] = "mock_settings"

import rest_framework

class Request(object):
    def __init__(self, method, post_data=""):
        self._method = method
        self._post_data = post_data
        
    @property
    def raw_post_data(self):
        return self._post_data
        
    @property
    def method(self):
        return self._method

    @property
    def REQUEST(self):
        return {}

class TestBasicOperations(unittest.TestCase):
    def test_get(self):
        class Handler(rest_framework.BaseHandler):
            def read(self, request):
                return "test_output"
                
        resource = rest_framework.Resource(Handler)
        output = resource(Request("get"))
        self.assertEqual(json.loads(output.content), {'data':"test_output"})
        self.assertEqual(output.status_code, 200)
        
    def test_post(self):
    
        class Handler(rest_framework.BaseHandler):
            def create(self, request):
                return "test_output"
                
        resource = rest_framework.Resource(Handler)
        output = resource(Request("post"))
        self.assertEqual(json.loads(output.content), {'data':"test_output"})
        self.assertEqual(output.status_code, 200)
        
    def test_put(self):
        class Handler(rest_framework.BaseHandler):
            def update(self, request):
                return "test_output"
                
        resource = rest_framework.Resource(Handler)
        output = resource(Request("put"))
        self.assertEqual(json.loads(output.content), {'data':"test_output"})
        self.assertEqual(output.status_code, 200)
        
    def test_delete(self):
        class Handler(rest_framework.BaseHandler):
            def delete(self, request):
                return "test_output"
                
        resource = rest_framework.Resource(Handler)
        output = resource(Request("delete"))
        self.assertEqual(json.loads(output.content), {'data':"test_output"})
        self.assertEqual(output.status_code, 200)
        
class TestEdgeCases(unittest.TestCase):
    def test_handles_error_gracefully_debug_off(self):
        class Handler(rest_framework.BaseHandler):
            def read(self, request):
                1/0
                
        resource = rest_framework.Resource(Handler)
        
        output = resource(Request("get"))
        self.assertTrue('error' in json.loads(output.content))
        self.assertEqual(json.loads(output.content)['error']['type'], 'APIError')
        self.assertEqual(output.status_code, 500)
