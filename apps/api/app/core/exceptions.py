class AppError(Exception):
    status_code = 500


class ValidationError(AppError):
    status_code = 400


class UnauthorizedError(AppError):
    status_code = 401


class ForbiddenError(AppError):
    status_code = 403


class NotFoundError(AppError):
    status_code = 404


class ConflictError(AppError):
    status_code = 409


class UnprocessableError(AppError):
    status_code = 422


class PayloadTooLargeError(AppError):
    status_code = 413


class UnsupportedMediaTypeError(AppError):
    status_code = 415


class ServiceUnavailableError(AppError):
    status_code = 503
