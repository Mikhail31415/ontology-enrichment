import os


class InvalidChatGptResponse(Exception):
    def __init__(self, message):
        super().__init__(message)

class JsonNotFountError(InvalidChatGptResponse):
    def __init__(self, gpt_response):
        super().__init__(f"JSON not found in GPT response: {gpt_response}")

class WrongJsonStructureError(InvalidChatGptResponse):
    def __init__(self, json):
        super().__init__(f"Wrong JSON structure: {json}")

class InconsistentChatGptResponse(InvalidChatGptResponse):
    def __init__(self, response):
        super().__init__(response)

class ObjectsNotFoundInResponseError(InvalidChatGptResponse):
    def __init__(self, response):
        super().__init__(f"Objects")
