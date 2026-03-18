"""Domain exceptions with HTTP status codes."""


class DomainError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class ConfigNotFoundException(DomainError):
    def __init__(self, config_id: str) -> None:
        super().__init__(f"Config {config_id} not found", 404)


class InvalidInputError(DomainError):
    def __init__(self, message: str) -> None:
        super().__init__(message, 400)


class ExternalServiceError(DomainError):
    def __init__(self, message: str) -> None:
        super().__init__(message, 502)
