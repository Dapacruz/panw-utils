==========
panw-utils
==========


.. image:: https://img.shields.io/pypi/v/panw_utils.svg
        :target: https://pypi.python.org/pypi/panw_utils

.. image:: https://img.shields.io/travis/dapacruz/panw_utils.svg
        :target: https://travis-ci.org/dapacruz/panw_utils

.. image:: https://readthedocs.org/projects/panw-utils/badge/?version=latest
        :target: https://panw-utils.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status




Palo Alto Networks Utilities


* Free software: MIT license
* Documentation: https://panw-utils.readthedocs.io.


Features
--------

panw-utils

* Returns a list of available commands

get-panw-api-key

* Returns the current API key, suitable for piping to pbcopy (macOS) or clip.exe (Windows)
* Command line options
* Platform independent
* Save default user and firewall
* Update saved settings
* Receives pipeline input (stdin)
* Uses a default firewall if one not provided
* Prompts for required parameters if none provided
* Multi-processing

get-panw-firewalls

* Returns a list of firewalls including management address and serial number
* Output can be pasted directly into Excel
* Terse output option for piping to other commands
* Command line options
* Platform independent
* Save API key and default Panorama host
* Update saved settings
* Override/supply API key on the command line

get-panw-interfaces

* Returns a list of firewalls interfaces
* Output can be pasted directly into Excel
* Terse output option for piping to other commands
* Command line options
* Platform independent
* Save API key and default firewall
* Update saved settings
* Override/supply API key on the command line
* Filter on interface properties
* Multi-processing

get-panw-config

* Returns the firewall configuration (set/XML format)
* Command line options
* Platform independent
* Save key based auth preference, default user and default firewall
* Update saved settings
* Multi-processing


Usage
=====

To return a list of firewalls use the ``get-panw-firewalls`` command::

    $ get-panw-firewalls
    Host                          	MgmtIP         	Serial      	Model   	Uptime              	SwVersion
    ==============================	===============	============	========	====================	=========
    fw01.domain.com                     1.1.1.1  	013999999999	PA-5220 	208 days, 6:49:53   	8.0.9
    fw01.domain.com                     1.1.1.2  	013999999998	PA-5220 	208 days, 7:27:28   	8.0.9

To return a list of firewall hostnames use the ``get-panw-firewalls`` command (suitable for piping to other commands)::

    $ get-panw-firewalls -t
    fw01.domain.com
    fw01.domain.com

To return a list of firewall interfaces use the ``get-panw-interfaces`` command::

    $ get-panw-interfaces fw01.domain.com
    Firewall                 	Interface           	State	IpAddress
    =========================	====================	=====	====================
    fw01.domain.com      	ethernet1/1         	up   	N/A
    fw01.domain.com      	ethernet1/12        	up   	N/A
    fw01.domain.com      	ethernet1/2         	up   	172.17.111.251/24
    fw01.domain.com      	ethernet1/21        	up   	N/A
    fw01.domain.com      	ethernet1/22        	up   	N/A
    fw01.domain.com      	ethernet1/5         	up   	172.19.222.206/28
    fw01.domain.com      	ethernet1/7         	up   	N/A
    fw01.domain.com      	ha1-a               	up   	1.1.1.1/30
    fw01.domain.com      	ha1-b               	up   	1.1.1.9/30
    fw01.domain.com      	hsci-a              	up   	1.1.1.5/30
    fw01.domain.com      	hsci-b              	up   	N/A
    fw01.domain.com      	tunnel              	up   	N/A
    fw01.domain.com      	tunnel.1800         	up   	N/A
    fw01.domain.com      	vlan                	up   	N/A

    $ get-panw-firewalls -t | get-panw-interfaces
    Firewall                 	Interface           	State	IpAddress
    =========================	====================	=====	====================
    fw01.domain.com      	ethernet1/1         	up   	N/A
    fw01.domain.com      	ethernet1/12        	up   	N/A
    fw01.domain.com      	ethernet1/2         	up   	172.17.111.251/24
    fw01.domain.com      	ethernet1/21        	up   	N/A
    fw01.domain.com      	ethernet1/22        	up   	N/A
    fw01.domain.com      	ethernet1/5         	up   	172.19.222.206/28
    fw01.domain.com      	ethernet1/7         	up   	N/A
    fw02.domain.com      	ethernet1/1         	up   	N/A
    fw02.domain.com      	ethernet1/12        	up   	N/A
    fw02.domain.com      	ethernet1/2         	up   	172.17.111.251/24
    fw02.domain.com      	ethernet1/21        	up   	N/A
    fw02.domain.com      	ethernet1/22        	up   	N/A
    fw02.domain.com      	ethernet1/5         	up   	172.19.222.206/28
    fw02.domain.com      	ethernet1/7         	up   	N/A

To return the firewall configuration use the ``get-panw-config`` command::

    $ get-panw-config
    ============================
    = fw01.domain.com =
    ============================
    <response status="success"><result><config version="8.0.0" urldb="paloaltonetworks">
      <mgt-config>
        <users>
          <entry name="admin">
            <phash>xxxxx</phash>
            <permissions>
              <role-based>
                <superuser>yes</superuser>
              </role-based>
            </permissions>
          </entry>
          <entry name="user1">
            <permissions>
              <role-based>
                <superuser>yes</superuser>
              </role-based>
            </permissions>
            <phash>xxxxx</phash>
          </entry>
    <--- Output truncated --->

To return the configuration of multiple firewalls pipe the output of ``get-panw-firewalls -t`` to the ``get-panw-config`` command::

    $ get-panw-firewalls -t | get-panw-config
    ============================
    = fw01.domain.com =
    ============================
    <response status="success"><result><config version="8.0.0" urldb="paloaltonetworks">
      <mgt-config>
        <users>
          <entry name="admin">
            <phash>xxxxx</phash>
            <permissions>
              <role-based>
                <superuser>yes</superuser>
              </role-based>
            </permissions>
          </entry>
          <entry name="user1">
            <permissions>
              <role-based>
                <superuser>yes</superuser>
              </role-based>
            </permissions>
            <phash>xxxxx</phash>
          </entry>
    <--- Output truncated --->

    ============================
    = fw02.domain.com =
    ============================
    <response status="success"><result><config version="8.0.0" urldb="paloaltonetworks">
      <mgt-config>
        <users>
          <entry name="admin">
            <phash>xxxxx</phash>
            <permissions>
              <role-based>
                <superuser>yes</superuser>
              </role-based>
            </permissions>
          </entry>
          <entry name="user1">
            <permissions>
              <role-based>
                <superuser>yes</superuser>
              </role-based>
            </permissions>
            <phash>xxxxx</phash>
          </entry>
    <--- Output truncated --->

To return a portion of the firewall configuration use the ``get-panw-config`` command with the ``--xpath`` option::

    get-panw-config --xpath "/config/mgt-config/users"
    ============================
    = fw01.domain.com =
    ============================
    <response status="success"><result><users>
      <entry name="admin">
        <phash>xxxxx</phash>
        <permissions>
          <role-based>
            <superuser>yes</superuser>
          </role-based>
        </permissions>
      </entry>
    </users></result></response>

To return the set configuration of multiple firewalls pipe the output of ``get-panw-firewalls -t`` to the ``get-panw-config`` command::

    $ get-panw-firewalls -t | get-panw-config --format set | egrep "^=|virtual-router"
    Collecting set configuration via ssh ...
    ============================
    = fw01.domain.com =
    ============================
    set network virtual-router default protocol bgp enable no
    set network virtual-router default protocol bgp dampening-profile default cutoff 1.25
    set network virtual-router default protocol bgp dampening-profile default reuse 0.5
    set network virtual-router default protocol bgp dampening-profile default max-hold-time 900
    set network virtual-router default protocol bgp dampening-profile default decay-half-life-reachable 300
    set network virtual-router default protocol bgp dampening-profile default decay-half-life-unreachable 900
    set network virtual-router default protocol bgp dampening-profile default enable yes
    set network virtual-router default interface [ ethernet1/1 ]
    set network virtual-router default routing-table ip static-route "Default Route" nexthop ip-address 192.168.197.254
    set network virtual-router default routing-table ip static-route "Default Route" path-monitor enable no
    set network virtual-router default routing-table ip static-route "Default Route" path-monitor failure-condition any
    set network virtual-router default routing-table ip static-route "Default Route" path-monitor hold-time 2
    set network virtual-router default routing-table ip static-route "Default Route" metric 10
    set network virtual-router default routing-table ip static-route "Default Route" destination 0.0.0.0/0
    set network virtual-router default routing-table ip static-route "Default Route" route-table unicast
    ============================
    = fw02.domain.com =
    ============================
    set network virtual-router default protocol bgp enable no
    set network virtual-router default protocol bgp dampening-profile default cutoff 1.25
    set network virtual-router default protocol bgp dampening-profile default reuse 0.5
    set network virtual-router default protocol bgp dampening-profile default max-hold-time 900
    set network virtual-router default protocol bgp dampening-profile default decay-half-life-reachable 300
    set network virtual-router default protocol bgp dampening-profile default decay-half-life-unreachable 900
    set network virtual-router default protocol bgp dampening-profile default enable yes
    set network virtual-router default interface [ ethernet1/1 ]
    set network virtual-router default routing-table ip static-route "Default Route" nexthop ip-address 10.69.26.62
    set network virtual-router default routing-table ip static-route "Default Route" path-monitor enable no
    set network virtual-router default routing-table ip static-route "Default Route" path-monitor failure-condition any
    set network virtual-router default routing-table ip static-route "Default Route" path-monitor hold-time 2
    set network virtual-router default routing-table ip static-route "Default Route" metric 10
    set network virtual-router default routing-table ip static-route "Default Route" destination 0.0.0.0/0
    set network virtual-router default routing-table ip static-route "Default Route" route-table unicast
