

class EndpointFabric:
    __instance = None

    @staticmethod
    def get_instance(public_key=None, private_key=None):
        if not EndpointFabric.__instance:
            EndpointFabric.__instance = EndpointFabric(public_key, private_key)
        return EndpointFabric.__instance

    def __init__(self, public_key=None, private_key=None):
        if EndpointFabric.__instance:
            raise Exception("This class is a singleton!")
        else:
            self.public_key = public_key
            self.private_key = private_key
            EndpointFabric.__instance = self

    def get_endpoint(self, klass, endpoint_url=None, entity_id=None):
        kwargs = {
            'public_key': self.public_key,
            'private_key': self.private_key,
            'endpoint_url': endpoint_url,
            'id': entity_id
        }
        return klass(**kwargs)
