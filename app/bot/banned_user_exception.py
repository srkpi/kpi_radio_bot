class BannedUserException(Exception):
    def __init__(self, message="User is banned"):
        self.message = message
        super().__init__(self.message)
