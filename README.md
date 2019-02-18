# panw-utils
*Palo Alto Networks Utility Scripts*
</br>
</br>
## Features
**panw-utils**
* Returns a list of available commands

**get-panw-api-key**
* Returns the current API key, suitable for piping to pbcopy (macOS) or clip.exe (Windows)
* Command line options
* Platform independent
* Save default user and firewall
* Update saved settings
* Receives pipeline input (stdin)
* Uses a default firewall if one not provided
* Prompts for required parameters if none provided

**get-panw-firewalls**
* Returns a list of firewalls including management address and serial number
* Output can be pasted directly into Excel
* Terse output option for piping to other commands
* Command line options
* Platform independent
* Save API key and default Panorama host
* Update saved settings
* Override/supply API key on the command line

**get-panw-interfaces**
* Returns a list of firewalls interfaces
* Output can be pasted directly into Excel
* Terse output option for piping to other commands
* Command line options
* Platform independent
* Save API key and default firewall
* Update saved settings
* Override/supply API key on the command line
* Filter on interface properties
</br>

## Installation
$ pip install panw-utils
</br>
</br>

## Upgrade
$ pip install --upgrade panw-utils
