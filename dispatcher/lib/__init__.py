"""
Generic functions.
"""
from copy import deepcopy
from decimal import Decimal, ROUND_HALF_UP


def change_key_name(dict_, key, with_):
    """
    Replace a key name in a dict by another name.

    :param dict dict_: targeted dict
    :param str key: targeted key name
    :param str with_: new key name
    :rtype: dict
    """
    dictionnary = dict_.copy()
    if key in dictionnary:
        dictionnary[with_] = dictionnary[key]
        del dictionnary[key]

    return dictionnary


def round_decimal(value):
    """
    Round a decimal to a float, with two digit precision.

    :param Decimal value:
    :rtype: float
    """
    return float(Decimal(value.quantize(Decimal('.01'), rounding=ROUND_HALF_UP)))


def sub_key(dictionary, key, default=None):
    """
    Find a dotted key from a dict.
    It can search in lists too (key.2.subkey)

    :param dict dictionary: where to search
    :param str key: subkey identification (key.sub.subsubkey)
    :param object default: default returned value
    :returns: the value in the dictionary
    """
    suburb = deepcopy(dictionary)
    for k in key.split('.'):
        if isinstance(suburb, list) and k.isdigit() and int(k) < len(suburb):
            suburb = suburb[int(k)]
            continue

        if not isinstance(suburb, dict):
            return default

        suburb = suburb.get(k, None)
        if suburb is None:
            return default

    return suburb
