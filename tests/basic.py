import unittest
import json
import os

# Set the DJANGO_SETTINGS_MODULE environment variable.
os.environ['DJANGO_SETTINGS_MODULE'] = "mock_settings"

from django.db import models

import rest_framework

class Request(object):
    def __init__(self, method, post_data=""):
        self._method = method
        self._post_data = post_data
        self._REQUEST = {}
    
    def set_get(self, **kwargs):
        self._REQUEST = kwargs
    
    @property
    def raw_post_data(self):
        return self._post_data
        
    @property
    def method(self):
        return self._method

    @property
    def REQUEST(self):
        return self._REQUEST

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
        
class TestMethodPassing(unittest.TestCase):
    def test_can_pass_parameter(self):
    
        passed_param = "12345"
        class Handler(rest_framework.BaseHandler):
            def read(slf, request, param):
                self.assertEqual(param, passed_param)
                return param
 
        resource = rest_framework.Resource(Handler)
        
        output = resource(Request("get"), passed_param)
        self.assertEqual(json.loads(output.content)['data'], passed_param)
        self.assertEqual(output.status_code, 200)
    
    def test_handles_passing_too_few_parameters(self):
    
        class Handler(rest_framework.BaseHandler):
            def read(slf, request, param):
                pass
        resource = rest_framework.Resource(Handler)
        
        output = resource(Request("get"))
        self.assertTrue('error' in json.loads(output.content))
        self.assertEqual(json.loads(output.content)['error']['type'], 'APIError')
        self.assertEqual(output.status_code, 500)
        
    def test_handles_passing_too_many_parameters(self):
    
        class Handler(rest_framework.BaseHandler):
            def read(slf, request, param):
                pass
        resource = rest_framework.Resource(Handler)
        
        output = resource(Request("get"), 1, 2)
        self.assertTrue('error' in json.loads(output.content))
        self.assertEqual(json.loads(output.content)['error']['type'], 'APIError')
        self.assertEqual(output.status_code, 500)
        
class TestEmitters(unittest.TestCase):
    def test_emitter_can_handle_model_instance(self):
        class MockTable(models.Model):
            field1          =   models.TextField()
            field2          =   models.TextField()

        class Handler(rest_framework.BaseHandler):
            def read(slf, request):
                return MockTable(field1="trolol", field2="cowgoesmoo")

        resource = rest_framework.Resource(Handler)
        
        output = resource(Request("get"))
        self.assertEqual(json.loads(output.content)['data']['field1'], "trolol")
        self.assertEqual(json.loads(output.content)['data']['field2'], "cowgoesmoo")
        self.assertEqual(output.status_code, 200)
        
    def test_emitter_invokes_massager(self):
        class MockTable(models.Model):
            field1          =   models.TextField()
            field2          =   models.TextField()

        class Handler(rest_framework.BaseHandler):
            def read(slf, request):
                return MockTable(field1="trolol", field2="cowgoesmoo")

        class MyEmitter(rest_framework.Emitter):
            def construct(self, data):
                massagers = {MockTable: self.massage}
                
                return self._construct(data, manips=[], massagers=massagers)
                
            def massage(self, model_dict, data):
                model_dict['field2'] = "COMPLETELYDIFFERENT"
                return model_dict
                
        class R(rest_framework.Resource):
            output = {'default':MyEmitter}
               
        resource = R(Handler)
        
        output = resource(Request("get"))
        self.assertEqual(json.loads(output.content)['data']['field1'], "trolol")
        self.assertEqual(json.loads(output.content)['data']['field2'], "COMPLETELYDIFFERENT")
        self.assertEqual(output.status_code, 200)

    def test_emitter_respects_output_parameter(self):
        class MockTable(models.Model):
            field1          =   models.TextField()
            field2          =   models.TextField()

        class Handler(rest_framework.BaseHandler):
            def read(slf, request):
                return MockTable(field1="trolol", field2="cowgoesmoo")

        class MyEmitter(rest_framework.Emitter):
            def construct(self, data):
                massagers = {MockTable: self.massage}
                
                return self._construct(data, manips=[], massagers=massagers)
                
            def massage(self, model_dict, data):
                model_dict['field2'] = "COMPLETELYDIFFERENT"
                return model_dict
                
        class MyOtherEmitter(rest_framework.Emitter):
            def construct(self, data):
                massagers = {MockTable: self.massage}
                
                return self._construct(data, manips=[], massagers=massagers)
                
            def massage(self, model_dict, data):
                model_dict['field2'] = "ishouldbethis"
                return model_dict
                
        class R(rest_framework.Resource):
            output = {'default':MyEmitter, 'hello':MyOtherEmitter}
               
        resource = R(Handler)
        req = Request("get")
        req.set_get(output='hello')
        output = resource(req)
        self.assertEqual(json.loads(output.content)['data']['field1'], "trolol")
        self.assertEqual(json.loads(output.content)['data']['field2'], "ishouldbethis")
        self.assertEqual(output.status_code, 200)
        
    def test_emitter_invokes_massager_and_manipper(self):
        class MockTable(models.Model):
            field1          =   models.TextField()
            field2          =   models.TextField()

        class Handler(rest_framework.BaseHandler):
            def read(slf, request):
                return MockTable(field1="trolol", field2="cowgoesmoo")

        class MyEmitter(rest_framework.Emitter):
            def construct(self, data):
                manips = [self.manip]
                massagers = {MockTable: self.massage}
                
                return self._construct(data, manips=manips, massagers=massagers)
               
            def manip(self, data, ids):
                data['table'] = {}
                for id in ids['table']:
                    data['table'][id] = id + 1
                
                return data, ids
                
            def massage(self, model_dict, data):
                if self._pre:
                    self._ids['table'].add(5)
                else:
                    model_dict['field2'] = self.data['table'][5]
                    
                return model_dict
                
        class R(rest_framework.Resource):
            output = {'default':MyEmitter}
               
        resource = R(Handler)
        
        output = resource(Request("get"))
        self.assertEqual(json.loads(output.content)['data']['field1'], "trolol")
        self.assertEqual(json.loads(output.content)['data']['field2'], 6)
        self.assertEqual(output.status_code, 200)
        