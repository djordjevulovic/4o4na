# -*- mode: python; python-indent: 4 -*-
import ncs
from ncs.application import Service
import netaddr

def option4_find_next_subif(root,device_name,arg_if_type,arg_if_num):

    device_config = root.devices.device[device_name].config
    intf_map = { 'GigabitEthernet' : device_config.ios__interface.GigabitEthernet }

    intf_list = intf_map[arg_if_type]

    max = 0

    for intf in intf_list:
      if '.' in intf.name:
         if_parts=intf.name.split('.')
         if if_parts[0] == arg_if_num:
            max = int(if_parts[1])

    return max + 1

class Option4(Service):

    @Service.create
    def cb_create(self, tctx, root, service, proplist):
        self.log.info('Service create(service=', service._path, ')')

        vars = ncs.template.Variables()

        netaddr_prefix = netaddr.IPNetwork(service.ip_prefix)
        vars.add('CIDR',str(netaddr_prefix.network))
        vars.add('IP1',str(list(netaddr_prefix)[1]))
        vars.add('IP2',str(list(netaddr_prefix)[2]))
        vars.add('MASK',str(netaddr_prefix.netmask))
        vars.add('WILDCARD',str(netaddr_prefix.hostmask))

        if service.GigabitEthernet:
            vars.add('IF-NUM',service.GigabitEthernet.name)
            vars.add('SUBIF',str(option4_find_next_subif(root,service.device,'GigabitEthernet',service.GigabitEthernet.name)))

        template = ncs.template.Template(service)
        template.apply('option4-nso-svc-template', vars)

# ---------------------------------------------
# COMPONENT THREAD THAT WILL BE STARTED BY NCS.
# ---------------------------------------------
class Main(ncs.application.Application):
    def setup(self):
        # The application class sets up logging for us. It is accessible
        # through 'self.log' and is a ncs.log.Log instance.
        self.log.info('Main RUNNING')

        # Service callbacks require a registration for a 'service point',
        # as specified in the corresponding data model.
        #
        self.register_service('option4-nso-svc-servicepoint', Option4)

        # If we registered any callback(s) above, the Application class
        # took care of creating a daemon (related to the service/action point).

        # When this setup method is finished, all registrations are
        # considered done and the application is 'started'.

    def teardown(self):
        # When the application is finished (which would happen if NCS went
        # down, packages were reloaded or some error occurred) this teardown
        # method will be called.

        self.log.info('Main FINISHED')
