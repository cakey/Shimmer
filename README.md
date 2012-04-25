This is a rest framework for use with Django.

It aids in routing requests to the appropriate method, handling exceptions, encoding and decoding json, introduces 'Emitters' which help you aggregate data and structure a response, without repeating yourself, and an auth hook.

Shimmer's requirements are currently django and dateutil (hopefully removed soon).

The most basic usage is:

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



For other use cases, look in the tests or ask. 
There are few tests directly for Shimmer at the moment, but the framework is used in a number of applications that are extensively tested.