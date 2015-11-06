#!/bin/sh
#
# (c) 2015 - Jaguar Land Rover.
#
# Mozilla Public License 2.0
#
# Ubuntu Software Manager Loader launch script
#

# This version of the script launches Terminal instead of xterm, for running on OSX.

pwd=`pwd`
osascript -e 'tell app "Terminal" to do script "python '$pwd'/package_manager.py"'
osascript -e 'tell app "Terminal" to do script "python '$pwd'/partition_manager.py"'
osascript -e 'tell app "Terminal" to do script "python '$pwd'/ecu1_module_loader.py"'
osascript -e 'tell app "Terminal" to do script "python '$pwd'/software_loading_manager.py"'
osascript -e 'tell app "Terminal" to do script "python '$pwd'/hmi.py"'
echo "Please run"
echo
echo "   python sota_client.py"
echo
echo "to start package use case."
echo 