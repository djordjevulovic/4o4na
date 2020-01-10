#!/usr/bin/python3

import option1
import option2
import option3
import option4
import yaml
import argparse
import logging


def load_yaml(filename):
    with open(filename, 'r') as ymlfile:
        return yaml.load(ymlfile)


parser = argparse.ArgumentParser()
parser.add_argument('--device-configuration-file', '-d', default='devices.yml',
                    help="YAML file for device configuration")
parser.add_argument('--service-configuration-file', '-s', help="YAML file for service configuration")
parser.add_argument('--option', '-o', type=int, choices=[1, 2, 3, 4], help="Option (1-4)")
parser.add_argument("--verbose", '-v', help="Increase output verbosity (debug)", action="store_true")
parser.add_argument("--dry-run", '-y', help="Dry-run (test)", action="store_true")
args = parser.parse_args()

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

try:

    devices_config = load_yaml(args.device_configuration_file)

    svc_config = load_yaml(args.service_configuration_file)

    option_callback_list = {"1":
                                {"create": option1.create_service,
                                 "set_device_params": option1.set_device_params,
                                 "set_proxy_params": None,
                                 "set_verbose_output": option1.set_verbose_output
                                 },
                            "2":
                                {"create": option2.create_service,
                                 "set_device_params": option2.set_device_params,
                                 "set_proxy_params": None,
                                 "set_verbose_output": option2.set_verbose_output
                                 },
                            "3":
                                {"create": option3.create_service,
                                 "set_device_params": option3.set_device_params,
                                 "set_proxy_params": None,
                                 "set_verbose_output": option3.set_verbose_output
                                 },
                            "4":
                                {"create": option4.create_service,
                                 "set_device_params": option4.set_device_params,
                                 "set_proxy_params": option4.set_proxy_params,
                                 "set_verbose_output": option4.set_verbose_output
                                 },
                            }

    for dev in devices_config['devices']:
        if dev['hostname'] == svc_config['parameters']['device']:

            callback = option_callback_list[str(args.option)]

            if args.verbose is True and callback["set_verbose_output"] is not None:
                callback["set_verbose_output"]()

            if callback["set_device_params"] is not None:
                callback["set_device_params"](dev['ip'],
                                              dev["username"],
                                              dev["password"],
                                              dev["netconf_port"],
                                              dev["cli_port"])

            if callback["set_proxy_params"] is not None:
                if "proxy_ip" in dev:
                    callback["set_proxy_params"](dev['proxy_ip'],
                                                 dev["proxy_username"],
                                                 dev["proxy_password"],
                                                 dev["proxy_port"],
                                                 dev["proxy_hostname"])
                else:
                    print("Option needs proxy but proxy not configured for device {}".format(dev['hostname']))
                    exit()

            new_subif = callback["create"](svc_config['parameters']['service_name'],
                                           svc_config['parameters']['interface_type'],
                                           str(svc_config['parameters']['interface_number']),
                                           svc_config['parameters']['ip_prefix'],
                                           args.dry_run)

            if new_subif is not None and args.dry_run is False:
                print("Service created.")
                if new_subif != '':
                    print("New subinterface {}{}.{}".format(svc_config['parameters']['interface_type'],
                                                            svc_config['parameters']['interface_number'],
                                                            new_subif))
            exit()

    print("Cannot find device {} in the configuration", format(svc_config['parameters']['device']))

except yaml.YAMLError as e:
    print("Error reading YAML file ({})", format(str(e)))
    exit()
