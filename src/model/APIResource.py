class APIResource:
    def __init__(self, index: str, name: str, url: str):
        self.index = index
        self.name = name
        self.url = url

    def __repr__(self):
        return f"{self.name} ({self.index})"