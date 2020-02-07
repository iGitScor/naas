"""
Error declaration and lifecycle.
"""


class AbstractApiException(Exception):
    """
    Abstract error class.
    """
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        """
        :param str message: description of the error
        :param int status_code: associated error code
        :param dict payload: append this values to the response
        """
        Exception.__init__(self)
        self.message = message
        if isinstance(status_code, int):
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        """
        :rtype: dict
        """
        rv_ = dict(self.payload or ())
        rv_['message'] = self.message
        rv_['status'] = self.status_code
        return rv_

    def __repr__(self):
        return '<{}: {}>'.format(self.__class__.__name__, self.message[:25])

    def __str__(self):
        return self.__repr__()


class GenericApiError(AbstractApiException):
    """
    Generic error class.
    """
    status_code = 500


class UncatchedApiError(AbstractApiException):
    """
    Error class for uncatched errors.
    """
    status_code = 500


class AuthenticationError(AbstractApiException):
    """
    Authentification errors.
    """
    status_code = 401
