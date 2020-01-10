import ncclient
from ncclient import manager
from lxml import etree
import logging
from io import BytesIO
import netaddr

HOST = None
PORT = None
USER = None
PASS = None


def set_device_params(arg_ip, arg_username, arg_password, arg_netconf_port,arg_cli_port):
    global HOST
    global PORT
    global USER
    global PASS
    HOST = arg_ip
    PORT = arg_netconf_port
    USER = arg_username
    PASS = arg_password


def xml_prettyprint(config_e):
    print(etree.tostring(config_e, pretty_print=True).decode())


def set_verbose_output():
    log_level = logging.DEBUG
    logging.getLogger('ncclient.transport.ssh').setLevel(log_level)
    logging.getLogger('ncclient.transport.session').setLevel(log_level)
    logging.getLogger('ncclient.operations.rpc').setLevel(log_level)


def push_config(config_e):
    try:

        with manager.connect(host=HOST, port=PORT, username=USER, password=PASS, hostkey_verify=False) as m:
            response = m.edit_config(config=config_e, target="running")
            return True

    except ncclient.operations.rpc.RPCError as e:
        print("Error pushing configuration to device ({})", format(str(e)))
        return False


def get_config(filter_string=None):
    try:

        with manager.connect(host=HOST, port=PORT, username=USER, password=PASS, hostkey_verify=False) as m:

            if filter_string is None:
                return m.get_config(source='running').data_xml
            else:
                return m.get_config(source='running', filter=filter_string).data_xml

    except ncclient.operations.rpc.RPCError as e:
        print("Error getting configuration from device ({})", format(str(e)))
        return False


def create_acl(native_e, arg_svc_name, arg_prefix):
    netaddr_prefix = netaddr.IPNetwork(arg_prefix)

    ip_e = etree.SubElement(native_e, "ip")
    access_list_e = etree.SubElement(ip_e, "access-list")
    standard_e = etree.SubElement(access_list_e, "standard", nsmap={None: 'http://cisco.com/ns/yang/Cisco-IOS-XE-acl'})
    etree.SubElement(standard_e, "name").text = arg_svc_name + "-ACL-in"
    access_list_seq_rule_e = etree.SubElement(standard_e, "access-list-seq-rule")
    etree.SubElement(access_list_seq_rule_e, "sequence").text = '10'
    permit_e = etree.SubElement(access_list_seq_rule_e, "permit")
    std_ace_e = etree.SubElement(permit_e, "std-ace")
    etree.SubElement(std_ace_e, "ipv4-prefix").text = str(netaddr_prefix.network)
    etree.SubElement(std_ace_e, "mask").text = str(netaddr_prefix.hostmask)


def find_next_subif(arg_if_type, arg_if_num):
    filter = "<filter><native xmlns='http://cisco.com/ns/yang/Cisco-IOS-XE-native'><interface><{}></{}></interface></native></filter>".format(
        arg_if_type, arg_if_type)

    cfg = get_config(filter)

    max_subif = 0

    for action, elem in etree.iterparse(BytesIO(bytes(cfg, 'utf-8'))):
        if elem.tag == '{http://cisco.com/ns/yang/Cisco-IOS-XE-native}name':
            if '.' in elem.text:
                if_parts = elem.text.split('.')
                if if_parts[0] == arg_if_num:
                    max_subif = int(if_parts[1])

    return max_subif + 1


def create_subif(native_e, arg_svc_name, arg_if_type, arg_if_num, arg_prefix):
    subif = str(find_next_subif(arg_if_type, arg_if_num))

    netaddr_prefix = netaddr.IPNetwork(arg_prefix)

    interface_e = etree.SubElement(native_e, "interface")
    gigabitethernet_e = etree.SubElement(interface_e, "GigabitEthernet")
    etree.SubElement(gigabitethernet_e, "name").text = arg_if_num + "." + subif
    etree.SubElement(gigabitethernet_e, "description").text = arg_svc_name
    encapsulation_e = etree.SubElement(gigabitethernet_e, "encapsulation")
    dot1q_e = etree.SubElement(encapsulation_e, "dot1Q")
    etree.SubElement(dot1q_e, "vlan-id").text = subif

    ip_e = etree.SubElement(gigabitethernet_e, "ip")

    access_group_e = etree.SubElement(ip_e, "access-group")
    in_e = etree.SubElement(access_group_e, "in")
    acl_e = etree.SubElement(in_e, "acl")
    etree.SubElement(acl_e, "acl-name").text = arg_svc_name + "-ACL-in"
    in2_e = etree.SubElement(acl_e, "in")

    address_e = etree.SubElement(ip_e, "address")
    primary_e = etree.SubElement(address_e, "primary")
    etree.SubElement(primary_e, "address").text = str(list(netaddr_prefix)[2])
    etree.SubElement(primary_e, "mask").text = str(netaddr_prefix.netmask)

    standby_e = etree.SubElement(gigabitethernet_e, "standby")
    standby_list_e = etree.SubElement(standby_e, "standby-list")
    etree.SubElement(standby_list_e, "group-number").text = '1'
    ip2_e = etree.SubElement(standby_list_e, "ip")
    etree.SubElement(ip2_e, "address").text = str(list(netaddr_prefix)[1])
    etree.SubElement(standby_list_e, "priority").text = '120'

    return subif


def create_ospf_network(native_e, arg_prefix):
    netaddr_prefix = netaddr.IPNetwork(arg_prefix)

    router_e = etree.SubElement(native_e, "router")
    ospf_e = etree.SubElement(router_e, "ospf", nsmap={None: 'http://cisco.com/ns/yang/Cisco-IOS-XE-ospf'})
    etree.SubElement(ospf_e, "id").text = '1'
    network_e = etree.SubElement(ospf_e, "network")
    etree.SubElement(network_e, "ip").text = str(netaddr_prefix.network)
    etree.SubElement(network_e, "mask").text = str(netaddr_prefix.hostmask)
    etree.SubElement(network_e, "area").text = '1'


def create_service(arg_svc_name, arg_if_type, arg_if_num, arg_prefix, arg_dryrun=False):
    config_e = etree.Element("config")
    native_e = etree.SubElement(config_e, "native", nsmap={None: 'http://cisco.com/ns/yang/Cisco-IOS-XE-native'})

    create_acl(native_e, arg_svc_name, arg_prefix)
    subif = create_subif(native_e, arg_svc_name, arg_if_type, arg_if_num, arg_prefix)
    create_ospf_network(native_e, arg_prefix)

    if arg_dryrun is False:
        if push_config(config_e) is True:
            return str(subif)
        else:
            return None
    else:
        xml_prettyprint(config_e)
        return subif
