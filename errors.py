class StatusError(Exception):
    def __init__(self, status, body, reason, verify=None):
        self.status = status
        self.body = f'Reason: {reason} \n Body: {body}'

class NotManifestError(Exception):
    def __init__(self):
        super(self)