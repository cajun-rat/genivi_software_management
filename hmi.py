# (c) 2015 - Jaguar Land Rover.
#
# Mozilla Public License 2.0
#
# Python-based hmi PoC for Software Loading Manager
#
import gobject
import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop
from slmtypes import update_states_desc, AWAITING_APPROVAL

DBUS_INTERFACE="org.genivi.software_loading_manager"
DBUS_BUSNAME=DBUS_INTERFACE

#
# hmi service
#
class HMIService(dbus.service.Object):
    def __init__(self):
        self.bus = dbus.SessionBus()
        self.bus.add_signal_receiver(self.update_state_changed,
                                     signal_name="update_state_changed",
                                     dbus_interface=DBUS_INTERFACE,
                                     bus_name=DBUS_BUSNAME)

        # Locate the Software Loading Manager bus object
        proxy = self.bus.get_object(DBUS_BUSNAME,
                                    "/org/genivi/software_loading_manager")
        self._slm = dbus.Interface(proxy, DBUS_INTERFACE)
        self.update_state_changed(self._slm.update_state(), self._slm.update_count())

    def update_state_changed(self, state_enum, updates):
        print "HMI: Update state has changed to %s (%d)" % (
                        update_states_desc[state_enum], state_enum)
        if state_enum == AWAITING_APPROVAL:
            print "HMI: %d Updates are available" % updates
            print
            print "DIALOG:"
            print "DIALOG: Available update"
            print "DIALOG:"
            resp = raw_input("DIALOG: Install? (yes/no): ")
            print
            if resp.startswith(('Y','y')):
                self._slm.approve()

if __name__ == "__main__":
    print
    print "HMI Simulator"
    print "Please enter package installation approval when prompted"
    print


    DBusGMainLoop(set_as_default=True)
    pkg_mgr = HMIService()

    loop = gobject.MainLoop()
    loop.run()
# vim: set expandtab tabstop=4 shiftwidth=4:
