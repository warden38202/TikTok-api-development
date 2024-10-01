from mongoengine import Document, StringField, ObjectIdField, DateTimeField, FloatField
from datetime import datetime


class FundingRequest(Document):
    status = StringField(required=True)
    user = ObjectIdField(required=True)
    transaction = ObjectIdField(required=False)
    amount = FloatField(required=True, min_value=0)
    approvedBy = ObjectIdField(required=False)
    initiatedOn = DateTimeField(default=datetime.utcnow)
    updatedOn = DateTimeField(default=datetime.utcnow)

    meta = {
        'indexes': [
            {'fields': ['user', 'status'], 'unique': False},
            {'fields': ['transaction', 'status'], 'unique': False},
            {'fields': ['approvedBy', 'user', 'status'], 'unique': False}
        ]
    }

