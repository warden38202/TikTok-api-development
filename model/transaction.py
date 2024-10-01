from bson import ObjectId
from datetime import datetime
from mongoengine import Document, StringField, ObjectIdField, FloatField, DateTimeField, ValidationError
from model.user import User

def validate_positive(value):
    if value < 0:
        raise ValidationError("Amount must be a positive number")

def validate_status(value):
    if not value.isdigit() or int(value) < 0:
        raise ValidationError("Status must be a non-negative integer in string form")

def validate_direction(value):
    if value not in ['0', '1']:
        raise ValidationError("Direction must be '0' for debit or '1' for credit")

class Transaction(Document):
    status = StringField(required=True, validation=validate_status)
    user = ObjectIdField(required=True)
    type = StringField(required=True, validation=validate_status)
    direction = StringField(required=True, validation=validate_direction)
    amount = FloatField(required=True, validation=validate_positive)
    initiatedOn = DateTimeField(default=datetime.utcnow)
    note = StringField(default="")
    updatedOn = DateTimeField(default=datetime.utcnow)

    meta = {
        'indexes': [
            {'fields': ['user', 'status']},
            {'fields': ['direction', 'user', 'status']},
            {'fields': ['type', 'user', 'status']}
        ]
    }
