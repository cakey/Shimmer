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
        
    def test_handles_wrong_method_gracefully(self):
    
        resource = rest_framework.Resource(rest_framework.BaseHandler)
        
        output = resource(Request("get"))
        self.assertTrue('error' in json.loads(output.content))
        self.assertEqual(json.loads(output.content)['error']['type'], 'NotImplemented')
        self.assertEqual(output.status_code, 405)
    
    def test_handles_bad_method_gracefully(self):
    
        resource = rest_framework.Resource(rest_framework.BaseHandler)
        
        output = resource(Request("nosuchmethod!"))
        self.assertTrue('error' in json.loads(output.content))
        self.assertEqual(json.loads(output.content)['error']['type'], 'NotImplemented')
        self.assertEqual(output.status_code, 405)
        
class TestJson(unittest.TestCase):
    def test_handles_bad_json_gracefully(self):
        class Handler(rest_framework.BaseHandler):
            def create(self, request):
                return request.data
                
        resource = rest_framework.Resource(Handler)
        output = resource(Request("post", 23423))
        self.assertTrue('error' in json.loads(output.content))
        self.assertEqual(json.loads(output.content)['error']['type'], 'InvalidParameter')
        self.assertEqual(output.status_code, 400)

    def test_handles_good_json(self):
    
        raw_data = {"hi":"moo"}
        json_dump = json.dumps(raw_data)
        
        class Handler(rest_framework.BaseHandler):
            def create(slf, request):
                self.assertEqual(request.data, raw_data)
                return request.data
                
        resource = rest_framework.Resource(Handler)
        output = resource(Request("post", json_dump))
        self.assertEqual(json.loads(output.content)['data'], raw_data)
        self.assertEqual(output.status_code, 200)
        
class TestAuthHook(unittest.TestCase):
    def test_assigns_user_id_correctly(self):
    
        expected_user = "my_user"
        
        class Handler(rest_framework.BaseHandler):
            def read(slf, request):
                self.assertEqual(request.user_id, expected_user)
                return request.user_id
                
        class R(rest_framework.Resource):
            def auth(self, request):
                return expected_user
        resource = R(Handler)
        
        output = resource(Request("get"))
        self.assertEqual(json.loads(output.content)['data'], expected_user)
        self.assertEqual(output.status_code, 200)
        
    def test_handles_bad_auth_func_gracefully(self):
    
        expected_user = "my_user"
        
        class Handler(rest_framework.BaseHandler):
            def read(slf, request):
                self.assertEqual(request.user_id, expected_user)
                return request.user_id
                
        class R(rest_framework.Resource):
            def auth(self, request):
                1/0
        resource = R(Handler)
        
        output = resource(Request("get"))
        self.assertTrue('error' in json.loads(output.content))
        self.assertEqual(json.loads(output.content)['error']['type'], 'APIError')
        self.assertEqual(output.status_code, 500)