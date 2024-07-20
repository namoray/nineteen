import json
import os

import netaddr
import requests


def int_to_ip(int_val: int) -> str:
    r"""Maps an integer to a unique ip-string
    Args:
        int_val  (:type:`int128`, `required`):
            The integer representation of an ip. Must be in the range (0, 3.4028237e+38).

    Returns:
        str_val (:type:`str`, `required):
            The string representation of an ip. Of form *.*.*.* for ipv4 or *::*:*:*:* for ipv6

    Raises:
        netaddr.core.AddrFormatError (Exception):
            Raised when the passed int_vals is not a valid ip int value.
    """
    return str(netaddr.IPAddress(int_val))


def ip_to_int(str_val: str) -> int:
    r"""Maps an ip-string to a unique integer.
    arg:
        str_val (:type:`str`, `required):
            The string representation of an ip. Of form *.*.*.* for ipv4 or *::*:*:*:* for ipv6

    Returns:
        int_val  (:type:`int128`, `required`):
            The integer representation of an ip. Must be in the range (0, 3.4028237e+38).

    Raises:
        netaddr.core.AddrFormatError (Exception):
            Raised when the passed str_val is not a valid ip string value.
    """
    return int(netaddr.IPAddress(str_val))


def get_external_ip() -> str:
    r"""Checks CURL/URLLIB/IPIFY/AWS for your external ip.
    Returns:
        external_ip  (:obj:`str` `required`):
            Your routers external facing ip as a string.

    Raises:
        ExternalIPNotFound (Exception):
            Raised if all external ip attempts fail.
    """
    # --- Try AWS
    try:
        external_ip = requests.get("https://checkip.amazonaws.com").text.strip()
        assert isinstance(ip_to_int(external_ip), int)
        return str(external_ip)
    except Exception:
        pass

    # --- Try ipconfig.
    try:
        process = os.popen("curl -s ifconfig.me")
        external_ip = process.readline()
        process.close()
        assert isinstance(ip_to_int(external_ip), int)
        return str(external_ip)
    except Exception:
        pass
    # --- Try ipinfo.
    try:
        process = os.popen("curl -s https://ipinfo.io")
        external_ip = json.loads(process.read())["ip"]
        process.close()
        assert isinstance(ip_to_int(external_ip), int)
        return str(external_ip)
    except Exception:
        pass
