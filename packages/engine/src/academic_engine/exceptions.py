class AcademixError(Exception):
    pass


class ConfigurationError(AcademixError):
    pass


class StorageError(AcademixError):
    pass


class ProviderUnavailableError(AcademixError):
    pass


class DocumentValidationError(AcademixError):
    pass


class DocumentNotFoundError(AcademixError):
    pass
