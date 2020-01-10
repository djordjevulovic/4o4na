from ydk.services import CRUDService
from ydk.providers import NetconfServiceProvider
import ydk.models.cisco_ios_xe.Cisco_IOS_XE_native as xe_native
from ydk.services.codec_service import CodecService
from ydk.providers.codec_provider import CodecServiceProvider
import logging
import netaddr
import ydk.types

ydk_provider = None
ydk_crud = None


def set_device_params(arg_ip, arg_username, arg_password, arg_netconf_port,arg_cli_port):
    global ydk_provider
    global ydk_crud

    ydk_provider = NetconfServiceProvider(address=arg_ip,
                                          port=arg_netconf_port,
                                          username=arg_username,
                                          password=arg_password,
                                          protocol='ssh')

    ydk_crud = CRUDService()


def set_verbose_output():
    log_level = logging.DEBUG
    logging.getLogger('ncclient.transport.ssh').setLevel(log_level)
    logging.getLogger('ncclient.transport.session').setLevel(log_level)
    logging.getLogger('ncclient.operations.rpc').setLevel(log_level)


def create_acl(xe_native_config, arg_svc_name, arg_prefix):
    netaddr_prefix = netaddr.IPNetwork(arg_prefix)

    acl = xe_native_config.ip.access_list

    new_acl = acl.Standard()
    new_acl.name = arg_svc_name + "-ACL-in"

    new_rule = new_acl.AccessListSeqRule()
    new_rule.sequence = 10
    new_rule.permit.std_ace.ipv4_prefix = str(netaddr_prefix.network)
    new_rule.permit.std_ace.mask = str(netaddr_prefix.hostmask)

    new_acl.access_list_seq_rule.append(new_rule)
    acl.standard.append(new_acl)


def find_next_subif(xe_native_config, arg_if_type, arg_if_num):
    filter = xe_native_config.interface
    config = ydk_crud.read(ydk_provider, filter)

    max_subif = 0

    if_type_list = {"GigabitEthernet": config.gigabitethernet}

    for intf in if_type_list[arg_if_type]:
        if '.' in intf.name:
            if_parts = intf.name.split('.')
            if if_parts[0] == arg_if_num:
                max_subif = int(if_parts[1])

    return max_subif + 1


def create_subif(xe_native_config, arg_svc_name, arg_if_type, arg_if_num, arg_prefix):
    ge_list = xe_native_config.interface.gigabitethernet

    new_if = xe_native_config.interface.GigabitEthernet()

    subif = find_next_subif(xe_native_config, arg_if_type, arg_if_num)

    netaddr_prefix = netaddr.IPNetwork(arg_prefix)

    new_if.name = arg_if_num + "." + str(subif)
    new_if.description = arg_svc_name
    new_if.encapsulation.dot1q.vlan_id = subif
    new_if.ip.address.primary.address = str(list(netaddr_prefix)[2])
    new_if.ip.address.primary.mask = str(netaddr_prefix.netmask)

    new_if.ip.access_group.in_.acl.acl_name = arg_svc_name + "-ACL-in"
    new_if.ip.access_group.in_.acl.in_ = ydk.types.Empty()

    new_standby_list = new_if.standby.StandbyList()
    new_standby_list.group_number = 1
    new_standby_list.ip = new_standby_list.Ip()
    new_standby_list.ip.address = str(list(netaddr_prefix)[1])
    new_standby_list.priority = 120
    new_if.standby.standby_list.append(new_standby_list)

    ge_list.append(new_if)

    return subif


def create_ospf_network(xe_native_config, arg_prefix):
    netaddr_prefix = netaddr.IPNetwork(arg_prefix)

    ospf_process = xe_native_config.router.Ospf()
    ospf_process.id = 1
    ospf_process_network = ospf_process.Network()
    ospf_process_network.ip = str(netaddr_prefix.network)
    ospf_process_network.mask = str(netaddr_prefix.hostmask)
    ospf_process_network.area = 1
    ospf_process.network.append(ospf_process_network)
    xe_native_config.router.ospf.append(ospf_process)


def create_service(arg_svc_name, arg_if_type, arg_if_num, arg_prefix, arg_dryrun=False):
    xe_native_config = xe_native.Native()

    create_acl(xe_native_config, arg_svc_name, arg_prefix)
    subif = create_subif(xe_native_config, arg_svc_name, arg_if_type, arg_if_num, arg_prefix)
    create_ospf_network(xe_native_config, arg_prefix)

    if arg_dryrun is False:
        ydk_crud.create(ydk_provider, xe_native_config)
        return str(subif)
    else:
        codec_service = CodecService()
        codec_provider = CodecServiceProvider(type='xml')

        print(codec_service.encode(codec_provider, xe_native_config))
        return str(subif)
