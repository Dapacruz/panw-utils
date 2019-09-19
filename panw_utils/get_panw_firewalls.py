#!/usr/bin/env python3

'''Get Panorama connected firewalls

get-panw-firewalls.py

Author: David Cruz (davidcruz72@gmail.com)

Python version >= 3.6

Required Python packages:
    None

Features:
    Returns a list of firewalls including management address and serial number
    Output can be pasted directly into Excel
    Terse output option for piping to other commands
    Command line options
    Platform independent
    Save API key and default Panorama host
    Update saved settings
    Override/supply API key on the command line
'''

import argparse
import json
import os
import os.path
import signal
import ssl
import sys
import urllib.request
import xml.dom.minidom as MD
import xml.etree.ElementTree as ET

def sigint_handler(signum, frame):
    sys.exit(1)

def query_api(args):
    # Disable certifcate verification
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    # Get connected firewalls
    if args.state == 'connected':
        cmd = '<show><devices><connected></connected></devices></show>'
    else:
        cmd = '<show><devices><all></all></devices></show>'
    params = urllib.parse.urlencode({
        'type': 'op',
        'cmd': cmd,
        'key': args.key,
    })
    url = f'https://{args.panorama}/api/?{params}'
    try:
        with urllib.request.urlopen(url, context=ctx) as response:
            xml = response.read().decode('utf-8')
    except OSError as err:
        raise SystemExit(f'{args.panorama}: Unable to connect to host ({err})')

    return xml

def parse_xml(args, root):
    results = {}
    for firewall in root.findall('./result/devices/entry'):
        connected = firewall.find('connected').text
        if args.terse and connected != 'yes':
            continue
        elif (args.state == 'disconnected' or args.state == 'not-connected') and connected == 'yes':
            continue

        try:
            hostname = f'{firewall.find("hostname").text.lower()}.wsgc.com'
        except AttributeError:
            hostname = 'n/a'
        try:
            serial = firewall.find('serial').text
        except AttributeError:
            serial = 'n/a'
        try:
            mgmt_ip = firewall.find('ip-address').text
        except AttributeError:
            mgmt_ip = 'n/a'
        try:
            model = firewall.find('model').text
        except AttributeError:
            model = 'n/a'
        try:
            uptime = firewall.find('uptime').text
        except AttributeError:
            uptime = 'n/a'
        try:
            sw_version = firewall.find('sw-version').text
        except AttributeError:
            sw_version = 'n/a'
        
        results.update({
            serial: {
                'hostname': hostname,
                'mgmt_ip': mgmt_ip,
                'model': model,
                'connected': connected,
                'uptime': uptime,
                'sw_version': sw_version,
            }
        })
    
    return results

def output(args, results):
    # Print header
    if not args.terse:
        print(f'{"Host" :30}\t{"MgmtIP" :15}\t{"Serial" :12}\t{"Model" :8}\t{"Connected" :9}\t{"Uptime" :20}\t{"SwVersion" :9}', file=sys.stderr)
        print(f'{"=" * 30 :30}\t{"=" * 15 :15}\t{"=" * 12 :12}\t{"=" * 8 :8}\t{"=" * 9 :9}\t{"=" * 20 :20}\t{"=" * 9 :9}', file=sys.stderr)

    for serial, attrib in results.items():
        if args.terse:
            print(attrib['hostname'])
        else:
            print(f'{attrib["hostname"] :30}\t{attrib["mgmt_ip"] :15}\t{serial :12}\t{attrib["model"] :8}\t{attrib["connected"] :9}\t{attrib["uptime"] :20}\t{attrib["sw_version"] :9}')

    return

def main():
    # Ctrl+C graceful exit
    signal.signal(signal.SIGINT, sigint_handler)

    parser = argparse.ArgumentParser(description='Returns a list of firewalls including management address and serial number')
    parser.add_argument('panorama', type=str, nargs='?', help='Panorama device to query')
    parser.add_argument('-k', '--key', metavar='', type=str, help='API key')
    parser.add_argument('-r', '--raw-output', action='store_true', help='Raw XML output')
    parser.add_argument('-s', '--state', choices=['connected', 'disconnected', 'not-connected', 'any', 'all'], default='all', help='Connection state')
    parser.add_argument('-t', '--terse', action='store_true', help='Output firewall names only')
    parser.add_argument('-U', '--update', action='store_true', help='Update saved settings')
    args = parser.parse_args()

    if 'USERPROFILE' in os.environ:
        settings_path = os.path.join(os.environ["USERPROFILE"], '.panw-settings.json')
    else:
        settings_path = os.path.join(os.environ["HOME"], '.panw-settings.json')

    # Import saved settings
    if os.path.exists(settings_path):
        with open(settings_path, 'r') as f:
            settings = json.load(f)

        # Check for the existence of settings and add if missing
        changed = False
        if not 'default_panorama' in settings:
            settings['default_panorama'] = input(f'Default Panorama Host: ')
            changed = True
        if not 'key' in settings:
            settings['key'] = input('API Key: ')
            changed = True
        if changed:
            with open(settings_path, 'w') as f:
                json.dump(settings, f, sort_keys=True, indent=2)
    else:
        settings = {
            'key': input('API Key: '),
            'default_panorama': input('Default Panorama Host: '),
        }
        with open(settings_path, 'w') as f:
            json.dump(settings, f, sort_keys=True, indent=2)
        os.chmod(settings_path, 0o600)

    # Update saved settings
    if args.update:
        print('\nUpdating saved settings ...\n')
        settings['key'] = input(f'New API Key [{settings["key"]}]: ') or settings['key']
        settings['default_panorama'] = input(f'New Default Panorama Host [{settings["default_panorama"]}]: ') or settings['default_panorama']
        with open(settings_path, 'w') as f:
            json.dump(settings, f, sort_keys=True, indent=2)
        print('\nSettings updated!')
        sys.exit(0)

    if not args.key:
        args.key = settings['key']
    if not args.panorama:
        args.panorama = settings['default_panorama']

    xml = query_api(args)

    # Pretty print XML
    if args.raw_output:
        print(MD.parseString(xml).toprettyxml(indent='  '))
        sys.exit(0)

    try:
        root = ET.fromstring(xml)
    except TypeError as err:
        raise SystemExit(f'Unable to parse XML! ({err})')

    firewalls = parse_xml(args, root)

    sorted_firewalls = dict(sorted(firewalls.items(), key=lambda i: (i[1]['hostname'] == 'n/a', i[1]['hostname'])))
    output(args, sorted_firewalls)

    sys.exit(0)


if __name__ == '__main__':
    main()
