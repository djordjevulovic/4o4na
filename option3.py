import os
from ansible.parsing.dataloader import DataLoader
from ansible.vars.manager import VariableManager
from ansible.inventory.manager import InventoryManager
from ansible.executor.playbook_executor import PlaybookExecutor
from ansible.module_utils.common.collections import ImmutableDict
from ansible import context

global_loader = DataLoader()
global_inventory = InventoryManager(loader=global_loader, sources='localhost,')
global_variable_manager = VariableManager(loader=global_loader, inventory=global_inventory)


def set_verbose_output():
    global global_variable_manager
    global_variable_manager.extra_vars['debug'] = 'true'


def set_device_params(arg_ip, arg_username, arg_password, arg_netconf_port, arg_cli_port):
    global global_variable_manager
    global_variable_manager.extra_vars['device_ip'] = arg_ip
    global_variable_manager.extra_vars['device_username'] = arg_username
    global_variable_manager.extra_vars['device_password'] = arg_password
    global_variable_manager.extra_vars['device_port'] = arg_cli_port


def create_service(arg_svc_name, arg_if_type, arg_if_num, arg_prefix, arg_dryrun=False):
    global global_variable_manager

    playbook_path = 'option3.yml'

    if not os.path.exists(playbook_path):
        print("No playbook found!")
        return None

    global_variable_manager.extra_vars['service_name'] = arg_svc_name
    global_variable_manager.extra_vars['interface_type'] = arg_if_type
    global_variable_manager.extra_vars['interface_number'] = arg_if_num
    global_variable_manager.extra_vars['ip_prefix'] = arg_prefix
    global_variable_manager.extra_vars['dry_run'] = "true" if arg_dryrun is True else "false"

    context.CLIARGS = ImmutableDict(connection='local', forks=10, become=None, become_method=None, become_user=None,
                                   check=False, diff=False, syntax=False, start_at_task=None, verbosity=1)

    pbex = PlaybookExecutor(playbooks=[playbook_path],
                            variable_manager=global_variable_manager,
                            loader=global_loader,
                            inventory=global_inventory,
                            passwords={})

    results = pbex.run()
    print(results)
    return ''


global_variable_manager.extra_vars['debug'] = 'false'
