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
    url(r'^hi/$, Resource(views.myHandler))
)

```

GETting /hi/ should return a json object of {'data':'hi'}

The four supported methods are currently:
* GET: read
* POST: create
* PUT: update
* DELETE: delete