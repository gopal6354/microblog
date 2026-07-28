class RedirectException(Exception):
    def __init__(self, url: str):
        self.url = url
