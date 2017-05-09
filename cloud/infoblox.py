#!/usr/bin/python
#
# Copyright 2014 "Igor Feoktistov" <ifeoktistov@yahoo.com>
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import re
import requests
import json
import os
class InfobloxNotFoundException(Exception):
    pass

class InfobloxNoIPavailableException(Exception):
    pass

class InfobloxGeneralException(Exception):
    pass

class InfobloxBadInputParameter(Exception):
    pass

class Infoblox_jnpr(object):
    """ Implements the following subset of Infoblox IPAM API via REST API

    """

    def __init__(self, iba_ipaddr, iba_user, iba_password, iba_wapi_version, iba_dns_view, iba_network_view, iba_verify_ssl=True):
        '''Class initialization method
        :param iba_ipaddr: IBA IP address of management interface
        :param iba_user: IBA user name
        :param iba_password: IBA user password
        :param iba_wapi_version: IBA WAPI version (example: 1.0)
        :param iba_dns_view: IBA default view
        :param iba_network_view: IBA default network view
        :param iba_verify_ssl: IBA SSL certificate validation (example: False)
        '''
        self.iba_host = iba_ipaddr
        self.iba_user = iba_user
        self.iba_password = iba_password
        self.iba_wapi_version = iba_wapi_version
        self.iba_dns_view = iba_dns_view
        self.iba_network_view = iba_network_view
        self.iba_verify_ssl = iba_verify_ssl

    def get_next_available_ips(self,network,number='10'):
        """ Implements IBA next_available_ip REST API call
        Returns IP v4 address
        :param network: network in CIDR format
        """
        rest_url = 'https://' + self.iba_host + '/wapi/v' + self.iba_wapi_version + '/network?network=' + network + '&network_view=' + self.iba_network_view
        try:
            r = requests.get(url=rest_url, auth=(self.iba_user, self.iba_password), verify=self.iba_verify_ssl)
            r_json = r.json()
            if r.status_code == 200:
                if len(r_json) > 0:
                    net_ref = r_json[0]['_ref']
                    #Changed the num 1 to 10 for gettting 10 free ips
                    rest_url = 'https://' + self.iba_host + '/wapi/v' + self.iba_wapi_version + '/' + net_ref + '?_function=next_available_ip&num='+number
                    r = requests.post(url=rest_url, auth=(self.iba_user, self.iba_password), verify=self.iba_verify_ssl)
                    r_json = r.json()
                    if r.status_code == 200 :
                        ip_v4 = r_json['ips']
                        return ip_v4
                    else:
                        if 'text' in r_json:
                            if 'code' in r_json and r_json['code'] == 'Client.Ibap.Data':
                                raise InfobloxNoIPavailableException(r_json['text'])
                            else:
                                raise InfobloxGeneralException(r_json['text'])
                        else:
                            r.raise_for_status()
                else:
                    raise InfobloxNotFoundException("No requested network found: " + network)
            else:
                if 'text' in r_json:
                    raise InfobloxGeneralException(r_json['text'])
                else:
                    r.raise_for_status()
        except ValueError:
            raise Exception(r)
        except Exception:
            raise
    def add_host_alias(self, host_fqdn, alias_fqdn):
        """ Implements IBA REST API call to add an alias to IBA host record
        :param host_fqdn: host record name in FQDN
        :param alias_fqdn: host record name in FQDN
        """
        rest_url = 'https://' + self.iba_host + '/wapi/v' + self.iba_wapi_version + '/record:host?name=' + host_fqdn + '&view=' + self.iba_dns_view + '&_return_fields=name,aliases'
        try:
            r = requests.get(url=rest_url, auth=(self.iba_user, self.iba_password), verify=False)
            r_json = r.json()
            if r.status_code == 200:
                if len(r_json) > 0:
                    host_ref = r_json[0]['_ref']
                    if host_ref and re.match("record:host\/[^:]+:([^\/]+)\/", host_ref).group(1) == host_fqdn:
                        if 'aliases' in r_json[0]:
                            aliases = r_json[0]['aliases']
                            aliases.append(alias_fqdn)
                            payload = '{"aliases": ' + json.JSONEncoder().encode(aliases) + '}'
                        else:
                            payload = '{"aliases": ["' + alias_fqdn + '"]}'
                        rest_url = 'https://' + self.iba_host + '/wapi/v' + self.iba_wapi_version + '/' + host_ref
                        r = requests.put(url=rest_url, auth=(self.iba_user, self.iba_password), verify=False, data=payload)
                        if r.status_code == 200:
                            return
                        else:
                            if 'text' in r_json:
                                raise InfobloxGeneralException(r_json['text'])
                            else:
                                r.raise_for_status()
                    else:
                        raise InfobloxGeneralException("Received unexpected host reference: " + host_ref)
                else:
                    raise InfobloxNotFoundException("No requested host found: " + host_fqdn)
            else:
                if 'text' in r_json:
                    raise InfobloxGeneralException(r_json['text'])
                else:
                    r.raise_for_status()
        except ValueError:
            raise Exception(r)
        except Exception:
            raise

    def get_host_by_search(self, fqdn):
        """ Implements IBA REST API call to retrieve host records by fqdn regexp filter
        Returns array of host names in FQDN matched to given regexp filter
        :param fqdn: hostname in FQDN or FQDN regexp filter
        """
        rest_url = 'https://' + self.iba_host + '/wapi/v' + self.iba_wapi_version + '/record:host?name~=' + fqdn + '&view=' + self.iba_dns_view
        hosts = []
        try:
            #print rest_url
            #print self.iba_user
            #print self.iba_verify_ssl

            #r = requests.get(url=rest_url, auth=(self.iba_user, self.iba_password), verify=self.iba_verify_ssl)
            r = requests.get(url=rest_url, auth=(self.iba_user, self.iba_password), verify=False)
            r_json = r.json()
            if r.status_code == 200:
                if len(r_json) > 0:
                    for host in r_json:
                        hosts.append(host['name'])
                    return hosts
                else:
                    raise InfobloxNotFoundException("No hosts found for regexp filter: " + fqdn)
            else:
                if 'text' in r_json:
                    raise InfobloxGeneralException(r_json['text'])
                else:
                    r.raise_for_status()
        except ValueError:
            raise Exception(r)
        except Exception:
            raise
    def get_next_available_ip(self,network):
        """ Implements IBA next_available_ip REST API call
        Returns IP v4 address
        :param network: network in CIDR format
        """
        rest_url = 'https://' + self.iba_host + '/wapi/v' + self.iba_wapi_version + '/network?network=' + network + '&network_view=' + self.iba_network_view
        try:
            r = requests.get(url=rest_url, auth=(self.iba_user, self.iba_password), verify=self.iba_verify_ssl)
            r_json = r.json()
            if r.status_code == 200:
                if len(r_json) > 0:
                    net_ref = r_json[0]['_ref']
                    #Changed the num 1 to 10 for gettting 10 free ips
                    rest_url = 'https://' + self.iba_host + '/wapi/v' + self.iba_wapi_version + '/' + net_ref + '?_function=next_available_ip&num=5'
                    r = requests.post(url=rest_url, auth=(self.iba_user, self.iba_password), verify=self.iba_verify_ssl)
                    r_json = r.json()
                    if r.status_code == 200:
                        ip_v4 = r_json['ips']
                        for i in range(len(ip_v4)):
                           ip_v4 = r_json['ips'][i]
                           response = os.system("ping -c 1 -w2 " + ip_v4 + " > /dev/null 2>&1")
                           if response != 0:
                              print ip_v4,'free and down'
                              return ip_v4
                    else:
                        if 'text' in r_json:
                            if 'code' in r_json and r_json['code'] == 'Client.Ibap.Data':
                                raise InfobloxNoIPavailableException(r_json['text'])
                            else:
                                raise InfobloxGeneralException(r_json['text'])
                        else:
                            r.raise_for_status()
                else:
                    raise InfobloxNotFoundException("No requested network found: " + network)
            else:
                if 'text' in r_json:
                    raise InfobloxGeneralException(r_json['text'])
                else:
                    r.raise_for_status()
        except ValueError:
            raise Exception(r)
        except Exception:
            raise
    def create_host_record(self, address, fqdn):
        """ Implements IBA REST API call to create IBA host record
        Returns IP v4 address assigned to the host
        :param address: IP v4 address or NET v4 address in CIDR format to get next_available_ip from
        :param fqdn: hostname in FQDN
        """
        if re.match("^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+\/[0-9]+$", address):
            #ipv4addr = 'func:nextavailableip:' + address
            ipv4addr =  self.get_next_available_ip(address)
            ipv4addr = str(ipv4addr)
            print ipv4addr
        else:
            if re.match("^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$", address):
                ipv4addr = address
            else:
                raise InfobloxBadInputParameter('Expected IP or NET address in CIDR format')
        rest_url = 'https://' + self.iba_host + '/wapi/v' + self.iba_wapi_version + '/record:host' + '?_return_fields=ipv4addrs'
        payload = '{"ipv4addrs": [{"configure_for_dhcp": false,"ipv4addr": "' + ipv4addr + '"}],"name": "' + fqdn + '","view": "' + self.iba_dns_view + '"}'
        try:
            #r = requests.post(url=rest_url, auth=(self.iba_user, self.iba_password), verify=self.iba_verify_ssl, data=payload)
            r = requests.post(url=rest_url, auth=(self.iba_user, self.iba_password), verify=False, data=payload)
            r_json = r.json()
            if r.status_code == 200 or r.status_code == 201:
                return r_json['ipv4addrs'][0]['ipv4addr']
            else:
                if 'text' in r_json:
                    raise InfobloxGeneralException(r_json['text'])
                else:
                    r.raise_for_status()
        except ValueError:
            raise Exception(r)
        except Exception:
            raise
    def delete_host_record(self, fqdn):
        """ Implements IBA REST API call to delete IBA host record
        :param fqdn: hostname in FQDN
        """
        rest_url = 'https://' + self.iba_host + '/wapi/v' + self.iba_wapi_version + '/record:host?name=' + fqdn + '&view=' + self.iba_dns_view
        try:
            r = requests.get(url=rest_url, auth=(self.iba_user, self.iba_password), verify=False)
            r_json = r.json()
            if r.status_code == 200:
                if len(r_json) > 0:
                    host_ref = r_json[0]['_ref']
                    if host_ref and re.match("record:host\/[^:]+:([^\/]+)\/", host_ref).group(1) == fqdn:
                        rest_url = 'https://' + self.iba_host + '/wapi/v' + self.iba_wapi_version + '/' + host_ref
                        r = requests.delete(url=rest_url, auth=(self.iba_user, self.iba_password), verify=False)
                        if r.status_code == 200:
                            return
                        else:
                            if 'text' in r_json:
                                raise InfobloxGeneralException(r_json['text'])
                            else:
                                r.raise_for_status()
                    else:
                        raise InfobloxGeneralException("Received unexpected host reference: " + host_ref)
                else:
                    raise InfobloxNotFoundException("No requested host found: " + fqdn)
            else:
                if 'text' in r_json:
                    raise InfobloxGeneralException(r_json['text'])
                else:
                    r.raise_for_status()
        except ValueError:
            raise Exception(r)
        except Exception:
            raise
    def get_network(self, network, fields=None):
        """ Implements IBA REST API call to retrieve network object fields
        Returns hash table of fields with field name as a hash key
        :param network: network in CIDR format
        :param fields: comma-separated list of field names
                        (optional, returns network in CIDR format and netmask if not specified)
        """
        if not fields:
            fields = 'network,netmask'
        #rest_url = 'https://' + self.iba_host + '/wapi/v' + self.iba_wapi_version + '/network?network=' + network + '&network_view=' + self.iba_network_view + '&_return_fields=' + fields
        rest_url = 'https://' + self.iba_host + '/wapi/v' + self.iba_wapi_version + '/ipv4address?network=' + network
        try:
            r = requests.get(url=rest_url, auth=(self.iba_user, self.iba_password), verify=False)
            r_json = r.json()
            if r.status_code == 200:
                if len(r_json) > 0:
                    return r_json[0]
                else:
                    raise InfobloxNotFoundException("No requested network found: " + network)
            else:
                if 'text' in r_json:
                    raise InfobloxNotFoundException(r_json['text'])
                else:
                    r.raise_for_status()
        except ValueError:
            raise Exception(r)
        except Exception:
            raise
def main():
    module = AnsibleModule(
        argument_spec = dict(
            state = dict(default='present'),
            iba_user = dict(required=True),
            iba_ipaddr = dict(required=True),
            iba_password = dict(required=True),
            iba_wapi_version = dict(required=True),
            iba_dns_view = dict(required=True),
            iba_network_view = dict(required=True),
            iba_verify_ssl = dict(required=True),
            iba_network = dict(required=False),
            fqdn = dict(required=False),
            address = dict(required=False),
            network = dict(required=False),
            host_fqdn = dict(required=False),
            alias_fqdn = dict(required=False)
        )
    )

    state = module.params['state']
    fqdn = module.params['fqdn']
    address = module.params['address']
    network = module.params['network']
    host_fqdn =  module.params['host_fqdn']
    alias_fqdn = module.params['alias_fqdn']
    infbl = Infoblox_jnpr(module.params['iba_ipaddr'], module.params['iba_user'], module.params['iba_password'], module.params['iba_wapi_version'], module.params['iba_dns_view'], module.params['iba_network_view'], module.params['iba_verify_ssl']);
    if state == 'present':
        infbl.get_network(network)
    elif state == 'add':
         infbl.create_host_record(address,fqdn)
    elif state == 'delete':
         infbl.delete_host_record(fqdn)
    elif state == 'alias':
         infbl.add_host_alias(host_fqdn,alias_fqdn)
    else:
        module.fail_json(msg="The state must be 'absent' or 'present' but instead we found '%s'" % (state))


# import module snippets
from ansible.module_utils.basic import *
main()
