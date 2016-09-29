#!/usr/bin/python
# (c) 2016, Radware LTD.

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

DOCUMENTATION = """
---
module: vdirect_commit
short_description: Commit pending changes to non-volatile memory on device
description:
    - This module uses the vDirect REST API to run the 'Commit' action on a managed device.
version_added: "2.1"
extends_documentation_fragment: vdirect_api
notes:
    - vDirect executes a Commit action on the device only if there are changes to commit.
    - When changed == True, changes were committed. When 'changed' == False there were no changes to commit.
    - If executing commit results in a sync operation (for example, between an HA pair of Alteon devices)
      this action may take a long time to finish even if there are no pending changes.
    - Check mode is supported. Check mode connects to vDirect and verifies that the vDirect version is supported, but does not commit changes or report anything.
"""

EXAMPLES = """
# commit pending changes
- vdirect_commit:
    vdirect_ip: 127.0.0.1
    username: user
    password: password
    device_name: alteon1
"""

RETURN = """
changed:
    description: Indicates whether or not the Commit action was performed on uncommitted changes.
    returned: always
    type: boolean
    sample: "{ 'changed': true }"
"""


def _create_ansible_module(arg_spec, check_invalid_args=True):
    """
    create AnsibleModule instance
    :param arg_spec:
    :param check_invalid_args:
    :return:
    """
    module = AnsibleModule(
        arg_spec,
        supports_check_mode=True,
        check_invalid_arguments=check_invalid_args,
    )
    return module


def main():

    argument_spec = vdirect_argument_spec()
    module = _create_ansible_module(argument_spec)

    vdirect = vDirect(module)
    show_help = vdirect.get_arg_subset('help')

    if show_help:
        module.exit_json(changed=False, usage="executes commit on the managed device")

    module.exit_json(changed=False if module.check_mode else vdirect.commit())

# standard ansible module imports
from ansible.module_utils.basic import *
from ansible.module_utils.vdirect_api import *

if __name__ == '__main__':
    main()
