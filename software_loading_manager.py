# (c) 2015 - Jaguar Land Rover.
#
# Mozilla Public License 2.0
#
# Python dbus service that faces the SOTA client.



import gobject
import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop

from slmtypes import NO_UPDATES, AWAITING_APPROVAL, INSTALLING, ERROR

DBUS_INTERFACE="org.genivi.software_loading_manager"
DBUS_BUSNAME=DBUS_INTERFACE
            
    
#
# Define the DBUS-facing Software Loading Manager service
#
class SLMService(dbus.service.Object):
    def __init__(self):
        
        # Retrieve the session bus.
        self.bus = dbus.SessionBus()

        # Define our own bus name
        self.slm_bus_name = dbus.service.BusName('org.genivi.software_loading_manager', 
                                                 bus=self.bus)
        
        # Define our own object on the software_loading_manager bus
        dbus.service.Object.__init__(self, 
                                     self.slm_bus_name, 
                                     "/org/genivi/software_loading_manager")
        self._updates = []
        self.update_state_changed(NO_UPDATES, 0)

    @dbus.service.method(DBUS_INTERFACE)
    def update_count(self):
        return len(self._updates)

    @dbus.service.method(DBUS_INTERFACE)
    def update_state(self):
       return self._state

    @dbus.service.signal(DBUS_INTERFACE)
    def update_state_changed(self, newstate, count):
        self._state = newstate

    @dbus.service.method(DBUS_INTERFACE, out_signature='aa{sv}')
    def details(self):
        r = []
        for package_id, major, minor, patch, command, size, description, vendor, target in self._updates:
            d = {
                'name': package_id,
                'size': size,
                'version': '%d.%d.%d' % (major, minor, patch),
            }
            if self._state == INSTALLING:
                d['status'] = 'installing'
            else:
                d['status'] = 'pending'
            r.append(d)
        return r

    @dbus.service.signal(DBUS_INTERFACE, signature="sss")
    def details_changed(self, name, version, state):
        print "details_changed %r %r %r" % (name, version, state)
        pass
    # 
    # Distribute a report of a completed installation
    # to all involved parties. So far those parties are
    # the SOTA client
    #
    def distribute_installation_report(self, 
                                       package_id, 
                                       major, 
                                       minor, 
                                       patch, 
                                       command, 
                                       path,
                                       size,
                                       description, 
                                       vendor, 
                                       target,
                                       result_code, 
                                       result_msg):
        #
        # Retrieve SOTA bus name, object, and installation report method
        #
        sota_bus_name = dbus.service.BusName("org.genivi.sota_client", bus=self.bus)
        sota_obj = self.bus.get_object(sota_bus_name.get_name(), "/org/genivi/sota_client")
        sota_installation_report = sota_obj.get_dbus_method("installation_report", 
                                                            "org.genivi.sota_client")
        
        # Send installation report to SOTA
        print "Sending report to sota.installation_report()"
        sota_installation_report(package_id, 
                                 major, 
                                 minor, 
                                 patch, 
                                 command, 
                                 path,
                                 size,
                                 description, 
                                 vendor, 
                                 target,
                                 result_code, 
                                 result_msg)

    @dbus.service.method(DBUS_INTERFACE, in_signature="siiisisss")
    def package_available(self, 
                          package_id, 
                          major, 
                          minor, 
                          patch, 
                          command, 
                          size, 
                          description, 
                          vendor,
                          target): 

        print "Got package available"
        print "  ID:     {}".format(package_id)
        print "  ver:    {}.{}.{} ".format(major, minor, patch)
        print "  cmd:    {}".format(command)
        print "  size:   {}".format(size)
        print "  descr:  {}".format(description)
        print "  vendor: {}".format(vendor)
        print "  target: {}".format(target)

        #
        # Send a notification to the HMI to get user approval / decline
        # Once user has responded, HMI will invoke self.package_confirmation()
        # to drive the use case forward.
        #
        self._updates.append((package_id, major, minor, patch, command, size, description, vendor, target))

        self.update_state_changed(AWAITING_APPROVAL, len(self._updates))
        
    @dbus.service.method(DBUS_INTERFACE,
                         async_callbacks=('send_reply', 'send_error'))
    def approve(self, packages, send_reply, send_error):
        
        # Send back an immediate reply since DBUS
        # doesn't like python dbus-invoked methods to do 
        # their own calls (nested calls).

        send_reply(True)
        packages_approved = set([name for name, version in packages])
        # Find the local sota client bus, object and method.
        sota_client_bus_name = dbus.service.BusName("org.genivi.sota_client",
                                                    bus=self.bus)
        sota_client_obj = self.bus.get_object(sota_client_bus_name.get_name(), 
                                              "/org/genivi/sota_client")
        sota_initiate_download = sota_client_obj.get_dbus_method(
                            "initiate_download", "org.genivi.sota_client")
        print "User has approved the installation of %d of %d packages" % (len(packages) , len(self._updates))
        has_started_installing = False
        for update in self._updates:
            (package_id, major, minor, patch,
             command, size, description, vendor, target) = update
        
            if package_id not in packages_approved:
                print "Skipping package %s that wasn't approved" % package_id
                continue
            has_started_installing = True
            print "Got package_confirmation()."
            print "  ID:       {}".format(package_id)
            print "  ver:      {}.{}.{} ".format(major, minor, patch)
            print "  cmd:      {}".format(command)
            print "  size:     {}".format(size)
            print "  descr:    {}".format(description)
            print "  vendor:   {}".format(vendor)
            print "  target:   {}".format(target)
            #
            # Call the SOTA client and ask it to start the download.
            # Once the download is complete, SOTA client will call 
            # download complete on this process to actually
            # process the package.
            #
            print "Approved: Will call initiate_download()"
            self.details_changed(package_id, "%d.%d.%d" % (major,minor,patch), "downloading")
            sota_initiate_download(package_id, major, minor, patch)
            print "Approved: Called sota_client.initiate_download()"
            print "---"
        if has_started_installing:
            self.update_state_changed(INSTALLING, len(self._updates))
        return None
        
    @dbus.service.method("org.genivi.software_loading_manager", 
                         async_callbacks=('send_reply', 'send_error'))
    def download_complete(self,
                          package_id,
                          major, 
                          minor, 
                          patch, 
                          command,
                          path,
                          size, 
                          description,
                          vendor,
                          target,
                          send_reply,
                          send_error): 
            
        print "Got download complete"
        print "  ID:     {}".format(package_id)
        print "  ver:    {}.{}.{} ".format(major, minor, patch)
        print "  cmd:    {}".format(command)
        print "  path:   {}".format(path)
        print "  size:   {}".format(size)
        print "  descr:  {}".format(description)
        print "  vendor: {}".format(vendor)
        print "  target: {}".format(target)
        print "---"

        # Send back an immediate reply since DBUS
        # doesn't like python dbus-invoked methods to do 
        # their own calls (nested calls).
        #
        send_reply(True)

        target_bus_name = dbus.service.BusName('org.genivi.'+target,
                                               bus=self.bus)
        
        target_obj = self.bus.get_object(target_bus_name.get_name(), 
                                         "/org/genivi/" + target)
            

        process_package = target_obj.get_dbus_method("process_package", 
                                                     "org.genivi." + target)


        #
        # Locate and invoke the correct package processor 
        # (ECU1ModuleLoaderProcessor.process_impl(), etc)
        #
        self.details_changed(package_id, "%d.%d.%d" % (major,minor,patch), "installing")
        process_package(package_id,
                        major, 
                        minor, 
                        patch, 
                        command,
                        path,
                        size, 
                        description,
                        vendor,
                        target)

        return None

        
    #
    # Receive and process a installation report.
    # Called by package_manager, partition_manager, or ecu_module_loader
    # once they have completed their process_package() calls invoked
    # by software_loading_manager
    #
    @dbus.service.method("org.genivi.software_loading_manager")
    def installation_report(self, 
                            package_id, 
                            major, 
                            minor, 
                            patch, 
                            command, 
                            path,
                            size, 
                            description, 
                            vendor,
                            target,
                            result_code,
                            result_text): 

        print "Got installation report()"
        print "  ID:          {}".format(package_id)
        print "  ver:         {}.{}.{} ".format(major, minor, patch)
        print "  cmd:         {}".format(command)
        print "  path:        {}".format(path)
        print "  size:        {}".format(size)
        print "  descr:       {}".format(description)
        print "  vendor:      {}".format(vendor)
        print "  target:      {}".format(target)
        print "  result_code: {}".format(result_code)
        print "  result_text: {}".format(result_text)
        print "---"
        if (result_code == 0):
            self.update_state_changed(NO_UPDATES, 0)
            self._updates = []
        else:
            self.update_state_changed(ERROR, len(self._updates))

    @dbus.service.method(DBUS_INTERFACE, out_signature='aa{sv}')
    def get_installed_packages(self): 
        print "Got get_installed_packages()"
        return [ { "package_id": "bluez_driver", 
                   "major": 1,
                   "minor": 2,
                   "patch": 3 },
                 { "package_id": "bluez_apps", 
                   "major": 3,
                   "minor": 2,
                   "patch": 1 } ]
                 
if __name__ == "__main__":
    print
    print "Software Loading Manager."
    print

    DBusGMainLoop(set_as_default=True)
    slm_sota = SLMService()
    loop = gobject.MainLoop()
    loop.run()
# vim: set expandtab tabstop=4 shiftwidth=4:
