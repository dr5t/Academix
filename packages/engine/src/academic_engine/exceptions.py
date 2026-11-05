class AcademixError(Exception):
    pass

class ConfigurationError(AcademixError):
    pass


class StorageError(AcademixError):
    pass


class ProviderUnavailableError(AcademixError):
    pass
