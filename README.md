This is a rest framework for use with Django.

It aids in routing requests to the appropriate method, handling exceptions, encoding and decoding json, introduces 'Emitters' which help you aggregate data and structure a response, without repeating yourself, and an auth hook.

Shimmer's requirements are currently django and dateutil (hopefully removed soon).

Getting Started:
------------

In views.py:
```python
from Shimmer.rest_framework import BaseHandler

class myHandler(BaseHandler):
    def read(self, request):
        return "hi"
```

In urls.py:
```python
from Shimmer.rest_framework import Resource
from django.conf.urls.defaults import patterns, url
import views

urlpattern = patterns('',
    url(r'^hi/$', Resource(views.myHandler))
)

```

GETting /hi/ will return a json object of {'data':'hi'}

The four supported methods are currently:
* GET: read
* POST: create
* PUT: update
* DELETE: delete




You can provide an auth hook like so:

In views.py:
```python
from Shimmer.rest_framework import BaseHandler

class myHandler(BaseHandler):
    def read(self, request):
        return request.user_id
```

In urls.py:
```python
from Shimmer.rest_framework import Resource
from django.conf.urls.defaults import patterns, url
import views

class R(Resource):
    def auth(self, request):
        return "user_id_of_user"

urlpattern = patterns('',
    url(r'^myuserid/$', R(views.myHandler))
)

```

GETting /myuserid/ will return a json object of {'data':"user_id_of_user"}


Emitters:
---------
 
 (Warning: The api needs (a lot of !) work here, as it's just grown organically in the projects its been used in.)
 
 Emitters are used to change the output of model instances from your database.
 The idea is that if you have an api that returns events, you want the logic that constructs an event in a centralised place.
 If an Event is created by fetching data from a number of different tables such as locations, descriptions, comments, attending lists, photos etc, and a particular api call returns numerous events, then it is also important to create the response in a way that minimises database lookups.
 
 An Emitter consists of:
* Manips - which use the ids generated from massagers to collect data that are then used in massagers to change the output
* Massagers - which are called when the emitter is traversing the response, they are used to help aggregate which ids to lookup, and then to take the looked up data and put it into the response
* a construct method which specifies which manips and massagers you are using.

You may specify a number of Emitters, which the user client of the API can select from by using the GET parameter 'output'.

An example:

Create the Resource:
```python
from Shimmer.rest_framework import Resource

import emitters

class R(Resource):
    output = {'default':emitters.AnEmitter, 'mobile':emitters.AMobileEmitter}

```
In emitters.py:
```python

from Shimmer.rest_framework import Emitter
import myapp.models as mod

class AnEmitter(Emitter):
    def setup(self):
        """
            Calls the base constructor with the manips/massagers you want.
        """     
        self.manips = [self.get_locations, self.get_comments]
        self.massagers = { mod.Event:self.massage_event}
        
    def get_locations(self):
        """
            This is an example data collection function, that collates a certain type of
            information we need.
            Data and ids are dictionaries that store the data we need.
        """
        self.data['locations'] = mod.Location.objects.in_bulk(list(self.ids['locations']))
        
    def get_comments(self):
        self.data['comments'] = mod.Comment.objects.in_bulk(list(self.ids['comments']))

    def massage_event(self, model_dict, model_instance):
        """
            Example of an massager to change the output of a model instance.
        """
        if self.collecting:
            self.ids['locations'].add(model_dict['location_id']
            self.ids['comments'].add(model_dict['comment_id']
        else:
            model_dict['location'] = self.construct(self.data['locations'][model_dict['location_id'])
            model_dict['comment'] = self.construct(self.data['comments'][model_dict['comment_id'])
            
            del model_dict['location_id']
            del model_dict['comment_id']
        
        return model_dict
```
There is a lot of magic there, which will be reduced as the api is improved. The important points are:

* self._construct starts the conversion from the view response to json using the provided manips and massagers
* manips can edit and use the data and ids which are referred to and editted by the massagers
* model_dict is a python dictionary which has been constructed from a model instance
* data (in the parameter to the massager) is the actual model instance
* self._pre is True if we are in the initial traversal passof the data (collecting ids, and converting to python dictionaries), or False if we are in the second pass which involves massaging the data
* self._ids is passed to the manips as ids
* self._any converts its argument from a model instance to things that can be serialised into json
* self.data refers to the data that was edited in the manips
* we return the modified dictionary of data

Notes
-----

For other use cases, look in the tests or ask. 
There are few tests directly for Shimmer at the moment, but the framework is used in a number of applications that are extensively tested.