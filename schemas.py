# Importing all needed modules.
from marshmallow import Schema, fields, ValidationError


# Defining the Intent Text Schema.
class SentimentTextSchema(Schema):
    # Defining the required schema fields.
    text = fields.Str(required=True)
    correlation_id = fields.Str(required=True)

    def validate_json(self, json_data : dict):
        '''
            This function validates the requests body.
                :param json_data: dict
                    The request body.
                :returns: dict, int
                    Returns the validated json or the errors in the json
                    and the status code.
        '''
        try:
            result = self.load(json_data)
        except ValidationError as err:
            return err.messages, 400
        return result, 200

class GeneralCredentialsSchema(Schema):
    host = fields.Str(required=True)
    port = fields.Int(required=True)
    name = fields.Str(required=True)

    def validate_json(self, json_data : dict):
        '''
            This function validates the requests body.
                :param json_data: dict
                    The request body.
                :returns: dict, int
                    Returns the validated json or the errors in the json
                    and the status code.
        '''
        try:
            result = self.load(json_data)
        except ValidationError as err:
            return err.messages, 400
        return result, 200

class SecuritySchema(Schema):
    secret_key = fields.Str(required=True)

    def validate_json(self, json_data : dict):
        '''
            This function validates the requests body.
                :param json_data: dict
                    The request body.
                :returns: dict, int
                    Returns the validated json or the errors in the json
                    and the status code.
        '''
        try:
            result = self.load(json_data)
        except ValidationError as err:
            return err.messages, 400
        return result, 200


# Defining the awake request schema.
class AwakeRequestSchema(Schema):
    # Defining the required schema fields.
    general = fields.Nested(GeneralCredentialsSchema, required=True)
    security = fields.Nested(SecuritySchema, required=True)

    def validate_json(self, json_data : dict):
        '''
            This function validates the requests body.
                :param json_data: dict
                    The request body.
                :returns: dict, int
                    Returns the validated json or the errors in the json
                    and the status code.
        '''
        try:
            result = self.load(json_data)
        except ValidationError as err:
            return err.messages, 400
        return result, 200

class IncreaseDecreaseSchema(Schema):
    # Defining the required schema fields.
    code = fields.Str(required=True)

    def validate_json(self, json_data : dict):
        '''
            This function validates the requests body.
                :param json_data: dict
                    The request body.
                :returns: dict, int
                    Returns the validated json or the errors in the json
                    and the status code.
        '''
        try:
            result = self.load(json_data)
        except ValidationError as err:
            return err.messages, 400
        return result, 200
