import requests
import json
from collections import OrderedDict

nso_host = None
nso_username = None
nso_password = None
nso_port = None
nso_device = None
debug_on = False


def nso_post_patch_put(uri, json_payload, function, restconf=True):
    global debug_on

    try:

        if function == requests.post:
            f_str = "POST"
        else:
            f_str = "PATCH"

        if restconf is True:
            header = {"Content-Type": "application/yang-data+json", "Accept": "application/yang-data+json"}
            url = "http://{}:{}/restconf/{}".format(nso_host, nso_port, uri)
        else:
            header = {"Content-Type": "application/vnd.yang.data+json", "Accept": "application/vnd.yang.data+json"}
            url = "http://{}:{}/api/{}".format(nso_host, nso_port, uri)

        if debug_on is True:
            print("{} URL: {}".format(f_str, url))
            print("Auth = {}/{}".format(nso_username, nso_password))
            print("Payload")
            print(json_payload)

        response = function(url,
                            data=json_payload,
                            auth=requests.auth.HTTPBasicAuth(nso_username, nso_password),
                            headers=header,
                            verify=False)

        if debug_on is True:
            print("{} Response Code = {}".format(f_str, response.status_code))
            print("{} Response Message = {}".format(f_str, response.text))

        return response

    except requests.exceptions.RequestException as e:
        if debug_on is True:
            print("ERROR: cannot send request, error ({})".format(e))
        return None


def nso_post(uri, json_payload, restconf=True):
    return nso_post_patch_put(uri, json_payload, requests.post, restconf)


def nso_patch(uri, json_payload, restconf=True):
    return nso_post_patch_put(uri, json_payload, requests.patch, restconf)


def nso_put(uri, json_payload, restconf=True):
    return nso_post_patch_put(uri, json_payload, requests.put, restconf)


def nso_call_action(action_name, action_input=None, restconf=True):
    if action_input is None:
        action_input = {}

    if restconf is True:
        url = "operations/" + action_name
    else:
        url = "config/" + action_name

    dict = {"input": action_input}

    json_payload = json.dumps(dict, sort_keys=False)

    response = nso_post(url, json_payload, restconf)

    if response is None:
        return None

    if response.status_code == 200:
        return response.json()
    else:
        return None


def nso_device_sync_from(device_name, restconf=True):
    if restconf is True:
        url = "devices/device={}/sync-from".format(device_name)
    else:
        url = "devices/device/{}/_operations/sync-from".format(device_name)

    return nso_call_action(url, restconf=restconf)


def set_verbose_output():
    global debug_on

    debug_on = True


def set_device_params(arg_ip, arg_username, arg_password, arg_netconf_port,arg_cli_port):
    return


def set_proxy_params(arg_proxy_host, arg_proxy_username, arg_proxy_password, arg_proxy_port, arg_proxy_hostname):
    global nso_host
    global nso_username
    global nso_password
    global nso_port
    global nso_device

    nso_host = arg_proxy_host
    nso_username = arg_proxy_username
    nso_password = arg_proxy_password
    nso_port = arg_proxy_port
    nso_device = arg_proxy_hostname


def create_service(arg_svc_name, arg_if_type, arg_if_num, arg_prefix, arg_dryrun=False):
    if nso_device is None:
        print("ERROR: Cannot map host into NSO device")
        return None

    restconf = False

    nso_device_sync_from(nso_device, restconf)

    if restconf is True:
        url = "data/option4-nso-svc={}{}".format(arg_svc_name, "?dryrun" if arg_dryrun is True else "")
    else:
        url = "running/option4-nso-svc/{}{}".format(arg_svc_name, "?dryrun=native" if arg_dryrun is True else "")

    dict = OrderedDict([("name", arg_svc_name),
                        ("device", nso_device),
                        ("GigabitEthernet", {"name": arg_if_num}),
                        ("ip-prefix", arg_prefix)])

    json_payload = json.dumps(dict, sort_keys=False)

    response = nso_put(url, json_payload, restconf)

    if response.status_code == 201:
        if arg_dryrun is True:
            json_response = response.json()
            print(json_response['dryrun-result']['native']['device'][0]['data'])
        return ''
    else:
        print("ERROR: service not created, error ({})".format(response.text))
        return None

"""
    dict = {"option4-nso-svc:option4-nso-svc": [{"name": arg_svc_name,
                                                 "device": nso_device,
                                                 "GigabitEthernet": {"name": arg_if_num},
                                                 "ip-prefix": arg_prefix
                                                 }]}
"""
