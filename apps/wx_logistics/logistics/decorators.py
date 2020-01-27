from functools import wraps

from wxapp.https import wxapp_client


def with_access_token(func):
    """
    Auto check if has access token
    :param func: Function
    :return: Function
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        params = kwargs.pop('params', {})
        access_token = wxapp_client.get_access_token()

        if 'access_token' not in params:
            params.update({
                'access_token': access_token,
            })

        return func(*args, params=params, **kwargs)

    return wrapper
