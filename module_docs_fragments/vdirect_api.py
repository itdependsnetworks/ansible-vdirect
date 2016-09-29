# Copyright (c) 2016 Radware LTD.
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.


class ModuleDocFragment(object):
    # general base vdirect documentation
    DOCUMENTATION = """
    options:
        vdirect_ip:
          description:
            - IP address for vDirect instance.
          required: true
          default: None
          version_added: "2.1"
        secondary_vdirect_ip:
          description:
            - IP address for secondary vDirect instance, if vDirect HA is configured.
          required: false
          default: ""
          version_added: "2.1"
        username:
          description:
            - vDirect admin user account.
          required: true
          aliases: ['user','admin']
          version_added: "2.1"
        password:
          description:
            - vDirect admin password.
          required: true
          aliases: ['pwd','pass']
          version_added: "2.1"
        port:
          description:
            - vDirect port.
          required: false
          default: 2189
          version_added: "2.1"
        scheme:
          description:
            - Protocol to use.
          required: false
          default: https
          choices: ['http','https']
          version_added: "2.1"
        timeout:
          description:
            - Connection timeout for vDirect REST API.
          required: false
          default: 180
          version_added: "2.1"
        validate_certs:
          description:
            - Validate SSL certificate when connecting to vDirect's web interface. Must be set to False to work with self-signed certificates.
          required: false
          default: no
          version_added: "2.1"
        device_name:
          description:
            - Name of device to be managed.
          required: true
          aliases: ['device']
          version_added: "2.1"
        device_type:
          description:
            - Type of device to be managed.
          required: false
          default: alteon
          version_added: "2.1"
        help:
          description:
            - When set to true, the module provides help about the action about to be performed.
            - For example, when used with the vdirect_template plugin it provides information about the required template parameters.
          required: false
          default: no
          version_added: "2.1"
"""