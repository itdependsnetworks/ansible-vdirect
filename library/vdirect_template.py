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
module: vdirect_template
short_description: Execute vDirect configuration template 
description:
    - This module uses the vDirect REST API to execute a configuration_template on a supported device_type.
      The module dynamically determines the template parameters needed for the specified template,
      providing input validation to the user.
      The module connects to vDirect, verifies that the template_name exists, and reads the template properties
      so that it can verify that parameters required for template execution are supplied and then executes the template.
version_added: "2.1"
extends_documentation_fragment: vdirect_api
options:
  template_name:
    description:
      - The name of the configuration template to execute.
        The template should already exist on vDirect.
        M(vdirect_file) can be used to upload templates
        to vDirect in a previous task.
    required: True
    aliases: [ 'template', 'tmpl' ]
    version_added: "2.1"
  commit_changes:
    description:
      - A Boolean parameter to commit changes caused by executing the I(template_name).
    required: False
    default: False
    version_added: "2.1"
notes:
   - If supported by the device, the module determines whether or not the template execution made changes
     to the device's configuration by executing the 'diff' command before and
     after executing the template, and comparing the results.
   - Check mode is supported. Check mode will dry run the template against the device and will report errors, if any.
   - I(help) will provide information about the parameters required for executing the I(template_name)
"""

EXAMPLES = """
# execute the idle.vm configuration template (template with one parameter
#  called idle_time)
# (added base vdirect_api mandatory params)
- vdirect_template:
    vdirect_ip: 127.0.0.1
    username: user
    password: password
    device_name: alteon1
    template_name: idle.vm
    idle_time: 500

# failed execution of the idle.vm configuration template (template with
#  one parameter called idle_time). will complain about extra
# param being unknown
# (added base vdirect_api mandatory params)
- vdirect_template:
    vdirect_ip: 127.0.0.1
    username: user
    password: password
    device_name: alteon1
    template_name: idle.vm
    idle_time: 500
    extra: "ok"
"""


RETURN = """
facts:
    description: All output parameters that might be returned by the executed configuration template.
    returned: success, when changed
    type: json object
    sample: "{ 'facts': {'real_server': {'address': '...', 'name': '...', 'port': 80, 'weight': 1}}"
"""


def _augment_arg_spec(arg_spec):
    """
    add module arguments
    :param arg_spec:
    :return:
    """
    arg_spec.update(
        dict(
            template_name=dict(type='str', required=True, aliases=['template', 'tmpl']),
            commit_changes=dict(type='bool', required=False, default='false', aliases=['commit', 'apply', 'save'])
        )
    )
    return arg_spec


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
    # add template parameters
    argument_spec = _augment_arg_spec(vdirect_argument_spec())

    module = _create_ansible_module(argument_spec, False)
    vdirect = vDirect(module)

    template_name, device_name, show_help, commit_changes = vdirect.get_arg_subset('template_name',
                                                                                   'device_name',
                                                                                   'help',
                                                                                   'commit_changes')

    check_mode = module.check_mode

    template_argument_spec = vdirect.validate_template(template_name, show_help)

    if show_help:
        vdirect.module.exit_json(changed=False, usage=template_argument_spec)

    argument_spec.update(template_argument_spec)

    # with additional parameters
    module = vdirect.module = _create_ansible_module(argument_spec)

    template_args = {}
    for key in module.params:
        if key in template_argument_spec:
            template_args[key] = module.params[key]

    resp, info, data, changed = vdirect.execute_template(template_name, template_args, check_mode)

    result = dict()

    if module.check_mode:
        for di in ['cliOutput', 'generatedScript']:
            if di in resp:
                result[di] = resp[di]
        result['sent_params'] = data

    result.update(resp.get('parameters', dict()))

    if not check_mode and commit_changes:
        changed = vdirect.commit()

    output = dict(
        changed=changed,
    )

    if result:
        output.update(
            dict(
                facts=result
            )
        )

    module.exit_json(**output)


# standard ansible module imports
from ansible.module_utils.basic import *
from ansible.module_utils.vdirect_api import *

if __name__ == '__main__':
    main()
