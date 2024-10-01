from datetime import datetime
from mongoengine import Document, StringField, DateTimeField, FloatField
import random
import string

def generate_random_string(length=8):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

class User(Document):
    status = StringField(required=True, default="1")
    createdOn = DateTimeField(default=datetime.utcnow)
    d1 = StringField(required=True, min_length=8, max_length=8)
    d2 = StringField(required=True, min_length=8, max_length=8)
    d3 = StringField(required=True, min_length=8, max_length=8)
    d4 = StringField(required=True, min_length=8, max_length=8)
    balance = FloatField(default=0.0)
    ipAddress = StringField(required=True)
    userAgent = StringField(required=True)

    meta = {
        'indexes': [
            {
                'fields': ('d1', 'd2', 'd3', 'd4'),
                'unique': True
            }
        ]
    }
