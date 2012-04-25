# -*- coding: utf-8 -*-
""" 
    This framework handles receiving the requests and dispactching them to the
    appropriate views, and then collecting the data from the databases which it
    returns in a selection of detail levels.
    By Ben Shaw, inspired by Piston - https://bitbucket.org/jespern/django-piston/wiki/Home
"""
import collections
import decimal
import datetime
import itertools
import json
import logging
import traceback

import dateutil.parser

from django.utils import datetime_safe
from django.views.decorators.vary import vary_on_headers
from django.conf import settings
from django.db.models.query import QuerySet
from django.db.models import Model
from django.utils.encoding import smart_unicode
from django.http import HttpResponse
    
from django import get_version as django_version

class APIException(Exception):
    """
        Any intentional raised exception, about incorrect api usage
        should inherit from this Exception, and provide the same
        interface, namely a message, a fix, a status, and a return error
    """
    def __init__(self, *args, **kwargs):
        
        self.message = "Describe what the error is."
        self.fix = "Describe how the user can fix it."
        self.returnerror = {'error':{'type': "Exception",
                                     'message': self.message}}
        self.status = 500
        
class NotImplemented(APIException):
    def __init__(self, method):
        self.message = "The method '%s' is not implemented for this resource." % method
        self.fix = "Make sure you are using the appropriate HTTP method - GET/POST/PUT/DELETE"
        self.returnerror = {'error':{'type': "NotImplemented",
                                     'message': self.message}}
        self.status = 405
        logging.info('api usage error: %s' % self.message)

class InvalidParameter(APIException):
    def __init__(self, parameter, value=None, override=False, fix=None):
        self.paramater = parameter
        if override:
            self.message = str(parameter)
        else:
            self.message = "The provided %s was invalid." % parameter
        self.fix = fix
        self.status = 400
        
        if parameter in ['mime_type']:
            self.fix = "Expected 'application/json' in header 'CONTENT_TYPE'"
            
        self.returnerror = {'error':{'type': "InvalidParameter",
                                     'message': self.message}}
        if self.fix is not None:
            self.returnerror['error']['fix'] = self.fix
            
        if value is not None:
            self.returnerror['error']['value'] = value
            
        logging.debug('api usage error: %s' % self.message)        
        
class InvalidPermission(APIException):
    """
        Raised when attempting to perform an action that the user does
        not have permission for, as a result of his relationships
        to entities or events
    """
    def __init__(self, perm=None):
        logging.info('vapi error: invalid permission')
        self.message = "You do not have permission to do that."
        self.returnerror = {'error':{'type': "InvalidPermission",
                                     'message':self.message}}
        if perm is not None:
            self.returnerror['error']['perm'] = perm
        self.status = 401  

class DoesNotExist(APIException):
    """
        Raised when attempting to use an object that does not exist.
    """
    def __init__(self, parameter, **kwargs):
        self.parameter = str(parameter)
        params = " and ".join(["%s {%s}" %(pn, kwargs[pn]) for pn in kwargs])
        self.message = "The %s with %s does not exist." % (parameter, params)
        self.returnerror = {'error':{'type': "DoesNotExist",
                                     'message': self.message}}
        self.status = 404
        logging.info('api usage error: %s' % self.message)

class Mimer(object):
       
    def translate(self, request):
        """
        Will look at the `Content-type` sent by the client, and try
        to deserialise into json. Since the data is not just
        key-value (and maybe just a list), the data will be placed on
        `request.data` instead, and the handler will have to read from
        there.
        """    
        
        request.content_type = 'application/json'
        
        try:
            if request.raw_post_data == "":
                request.data = ""
            else:
                request.data = json.loads(request.raw_post_data)
            
            # Reset both POST and PUT from request, as its
            # misleading having their presence around.
            request.POST = request.PUT = dict()
        except (TypeError, ValueError):
            raise InvalidParameter("JSON")
        
        return request
        
class Emitter(object):
    """
    Super emitter. All other emitters should subclass
    this one. It has the `construct` method which
    conveniently returns a serialized `dict`. This is
    usually the only method you want to use in your
    emitter. See below for examples.
    """
    def __init__(self, request=None):
        self.request = request
        self.exclude_fields = ('active', '_state') # which fields of the models should we exclude
        self.DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S%z"
        self.DATE_FORMAT = "%Y-%m-%d"
        self.TIME_FORMAT = "%H:%M:%S"
        self.mimetype = 'application/json; charset=utf-8'

    @property
    def django_user(self):
        if self.request is not None:
            return self.request.user
              
    def _any(self, thing):
        """
        Dispatch, all types are routed through here.
        """
        ret = None
        if isinstance(thing, str):
            ret = thing
        elif isinstance(thing, QuerySet):
            ret = self._qs(thing)
        elif isinstance(thing, (tuple, list)):
            ret = self._list(thing)
        elif isinstance(thing, dict):
            ret = self._dict(thing)
        elif isinstance(thing, decimal.Decimal):
            ret = str(thing)
        elif isinstance(thing, Model):
            ret = self._model(thing)
        elif isinstance(thing, datetime.datetime):
            o2 = thing.replace(tzinfo=dateutil.tz.tzutc())
            return datetime.datetime.strftime(o2, self.DATETIME_FORMAT)
        elif isinstance(thing, datetime.date):
            d = datetime_safe.new_date(thing)
            return d.strftime(self.DATE_FORMAT)
        elif isinstance(thing, datetime.time):
            return thing.strftime(self.TIME_FORMAT)
        else:
            ret = smart_unicode(thing, strings_only=True)

        return ret
    
    def _model(self, data):
        """
        Models.
        """
        #logging.debug("in _model")
        ret = { }

        for f in data._meta.fields:
                #logging.debug(f.attname)
                if f.attname not in self.exclude_fields:
                    ret[f.attname] = self._any(getattr(data, f.attname))
                  
        # massage the data depending on what model it is
        if type(data) in self.massagers:
            ret = self.massagers[type(data)](ret, data) 
        
        
        return ret
        
    def _qs(self, data):
        """
        Querysets.
        """
        return [ self._any(v) for v in data]
            
    def _list(self, data):
        """
        Lists.
        """
        return [ self._any(v) for v in data]
        
    def _dict(self, data):
        """
        Dictionaries.
        """
        #logging.info([k for k in data])
        return {k:self._any(v) for k, v in data.iteritems()}
    
    def _pre_construct(self, data):
        """
            Does a first pass through the models to collect together 
            which event ids and entity ids it needs to get the appropriate
            data for, so we can collect it in constant time.
        """
        logging.info("pre constructing (enter)")
        self._ids = collections.defaultdict(set)
        self._pre = True
        pre_construct_data = self._any(data)
        self._pre = False
        logging.info("pre constructing (exit)")
        return pre_construct_data
        
    def _construct(self, data, manips=None, massagers=None):
        """
        Recursively serialize a lot of types, and
        in cases where it doesn't recognize the type,
        it will fall back to Django's `smart_unicode`.
        
        Returns the data constructed.
        """
        logging.info("overall constructing (enter)")
        
        if manips is None:
            manips = []
        
        if massagers is None:
            massagers = {}
            
        self.massagers = massagers
        
 
        pre_construct_data = self._pre_construct(data)
        # Kickstart the seralizin'.
        
         #if it found no ids, then we can just use the pre construct data
        if any((len(ids) > 0 for label, ids in self._ids.iteritems())):
            ids = self._ids #DRPEPPER
            manipdata = collections.defaultdict(dict)

                      
            for manip in manips:
                manipdata, ids = manip(manipdata, ids)
            
            self.data = manipdata
            
            logging.debug("constructing (enter)")
            # extend the output using the collated data we've found
            data =  self._any(data)
            logging.debug("constructing (exit)")
            
            logging.debug("overall constructing (exit)")
            return data
        else:
            logging.debug("overall constructing (exit)")
            return pre_construct_data
            
    def construct(self, *args, **kwargs):
        """ overwrite this to provide different manips """
        return self._construct(*args, **kwargs)
        
    def render(self, data):
        """ Implements a default JSON renderer """        
        logging.info("render (start)")
        
        seria = json.dumps(data, ensure_ascii=False, indent=4)
        logging.info("rendered %s characters (end)" % len(seria))
        return seria    
               
class BaseHandler(object):
    """
    Basehandler that gives you CRUD for free.
    You are supposed to subclass this for specific
    functionality.
    
    All CRUD methods (`read`/`update`/`create`/`delete`)
    receive a request as the first argument from the
    resource. Use this for checking `request.user`, etc.
    """
    status = None
    
    def read(self, request, *args, **kwargs):
        raise NotImplemented("GET")

    def create(self, request, *args, **kwargs):
        raise NotImplemented("POST")
           
    def update(self, request, *args, **kwargs):
        raise NotImplemented("PUT")
    
    def delete(self, request, *args, **kwargs):
        raise NotImplemented("DELETE")
        
class Resource(object):
    """
    Resource. Create one for your URL mappings, just
    like you would with Django. Takes one argument,
    the handler. The second argument is optional, and
    is an authentication handler. If not specified,
    `NoAuthentication` will be used by default.
    """
    callmap = { 'GET': 'read', 'POST': 'create', 
                'PUT': 'update', 'DELETE': 'delete' }

    output = {'default':Emitter}
    
    def __init__(self, handler):
        if not callable(handler):
            raise AttributeError("Handler not callable.")
        
        # we get passed a class naem, create an instance of it
        self.handler = handler()
        
        self.csrf_exempt = getattr( self.handler, 'csrf_exempt', True )
    
    @vary_on_headers('Authorization')
    def __call__(self, request, *args, **kwargs):
        """
        NB: Sends a `Vary` header so we don't cache requests
        that are different (OAuth stuff in `Authorization` header.)
        
        This function works as follows:
            1 put post data in an easy to reach place
            2 work out which view we want to call and call it
                2a if there is an expected api usage exception, it handles catching it and retuning the appropriate details
                2b if there is an unexpected failure in the view, it will catch that and log it
            3 construct the response, using the appropriate amount of detail
            4 render the response to json
        """
        logging.info("     >>>> framework resource (enter)")
        # try to keep as much in the try block as possible, as we want pretty error messages at the least
        try:
            # try to find the user_id
            try:
                request.user_id = self.auth(request)
            except AttributeError:
                pass
        
            rm = request.method.upper()

            handler = self.handler
            handler.status = None # reset status
            # Translate nested datastructs into `request.data` here.
            if rm in ('POST', 'PUT'):
                mimer = Mimer()
                mimer.translate(request)
            
            method_string = self.callmap.get(rm, None)
            if method_string is None:
                raise NotImplemented(rm)
            meth = getattr(handler, method_string, False)
            
            # tries to call the view
            logging.info("%s: %s" % (handler.__class__.__name__, self.callmap.get(rm)))
            result = meth(request, *args, **kwargs)
            
            # construct the response using the appropriate detail then render to json
            output_format = request.REQUEST.get('output','default')
            try:
                output_emitter = self.output[output_format]
            except:
                raise InvalidParameter("emission type", value=outputformat, fix="choose from [%s]" % "/".join(self.output.keys))
            
            emitter = output_emitter(request=request)# give request so we can lazily load the user only if necessary
            mimetype = emitter.mimetype


            construct = emitter.construct(data=result)
            stream = emitter.render({'data':construct})
            
            if handler.status is None:
                status = 200
            else:
                status = handler.status
        except (APIException) as e:
            stream = json.dumps(e.returnerror, indent=4)
            status = e.status
            mimetype = "application/json"
        except Exception as e: #keep this stuff simple so we KNOW it works
            logging.exception("Exception in API %s" % str(e))
            status = 500
            if settings.DEBUG:
                stream = json.dumps({'error':{
                                    'type':"APIError",
                                    'message':("API (Django %s) crash report:\n\n%s" % 
                        (django_version(), str(traceback.format_exc())))}}, indent=4)
                mimetype = "application/json"
            else:
                stream = json.dumps({'error':{
                                    'type':"APIError",
                                    'message':"An API error has occured, please try again later."}}, indent=4)
                mimetype = "application/json"
        
        #logging.info(stream)
        resp = HttpResponse(stream, mimetype=mimetype, status=status)
        logging.info(" <<<< framework resource (exit)")
        return resp 