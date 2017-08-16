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
module: vdirect_workflow
short_description: Create/Delete Workflow or Execute workflow Action
description:
    - This module uses the vDirect REST API to either create a workflow from a workflow_template, delete a workflow,
      or execute a workflow action of a given workflow.
      The module dynamically determines the template parameters needed for the specified operation,
      providing input validation to the user.
version_added: "2.1"
extends_documentation_fragment: vdirect_api
options:
  operation:
    description:
      - The operation type you want the module to perform.
      - action - Executes an action provided by the workflow.
      - create - Creates a workflow from a (pre-existing) workflow template.
      - delete - Deletes an existing workflow.
    required: False
    default: action
    choices: ['action', 'create', 'delete']
    version_added: "2.1"
  workflow_template_name:
    description:
      - The name of the workflow template to use.
        The template should already exist on vDirect.
        M(vdirect_file) can be used to upload the template
        to vDirect in a previous task.
        Must be supplied for a 'create' operation.
    required: False
    aliases: [ 'template', 'tmpl' ]
    version_added: "2.1"
  workflow_name:
    description:
      - The name of workflow to create/delete/run action with.
    required: True
    aliases: ['wf']
    version_added: "2.1"
  action:
    description:
      - Workflow action to be executed.
    required: False
    version_added: "2.1"
  sync:
    description:
      - True - Wait for the operation to finish (default).
      - False - Fire and forget mode.
    default: True
    required: False
    version_added: "2.1"
  async_delay:
    description:
      - Length of delay between status checks on synchronous operations, in seconds.
    required: False
    default: 2
    version_added: "2.1"
notes:
   - Workflow operations can be quite lengthy (depending on the workflow sequences).
   - The module is not idempotent. Rerunning the module will attempt to performe the action requested again.
   - Check_mode is supported. It does not change the device's configuration and will try to validate the input
     provided by the user. It will not performe a "dry run" execution on the device like the vdirect_template module does.
   - I(help) is not yet supported for this module
"""

EXAMPLES = """
# create the idle workflow from the idle workflow template
# (added base vdirect_api mandatory params)
- vdirect_workflow:
    vdirect_ip: 127.0.0.1
    username: user
    password: password
    operation: create
    workflow_name: idle
    workflow_template_name: idle
    adc: alteon1
    idle_time: 500

# execute the update_idle workflow action from the idle workflow
# (added base vdirect_api mandatory params)
- vdirect_workflow:
    vdirect_ip: 127.0.0.1
    username: user
    password: password
    operation: action
    action: update_idle
    workflow_name: idle
    idle_time: 500

# delete the idle workflow from vDirect
# (added base vdirect_api mandatory params)
- vdirect_workflow:
    vdirect_ip: 127.0.0.1
    username: user
    password: password
    operation: delete
    workflow_name: idle

"""


RETURN = """
facts:
    description: status, duration and log entries for the requested operation.
    returned: on successful execution.
    type: json object
    sample: "{ 'facts': { 'changed': true, 'duration': ss, 'log': ['...', '...']}}"
"""


def _augment_arg_spec(arg_spec):
    """
    add module arguments
    :param arg_spec:
    :return:
    """
    arg_spec.update(
        dict(
            operation=dict(type='str', required=False, default='action', choices=['create', 'delete', 'action']),
            action=dict(type='str', required=False),
            workflow_template_name=dict(type='str', required=False, aliases=['template', 'tmpl']),
            workflow_name=dict(type='str', required=True, aliases=['wf']),
            sync=dict(type='bool', required=False, default='true'),
            async_delay=dict(type='int', required=False, default=2),
            # overwriting device name. not needed for this module.
            device_name = dict(type='str', required=False, defaultValue='adc')
        )
    )
    return arg_spec


def _create_ansible_module(arg_spec, check_invalid_args=False):
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
        mutually_exclusive=(
            ['workflow_template_name', 'action'],
        ),
    )
    return module


def validate_arg_spec(module, operation, action, workflow_template_name, sync, async_delay):
    """
    check module arguments.
    :param module:
    :param operation:
    :param action:
    :param workflow_template_name:
    :param sync:
    :param async_delay:
    """
    if operation == 'create' and not workflow_template_name:
        module.fail_json(msg="operation: create requires value for workflow_template_name")

    if operation == 'action' and workflow_template_name:
        module.fail_json(msg="operation: action (the default) is mutually exclusive with workflow_template_name")

    if operation == 'action' and not action:
        module.fail_json(msg="operation: action requires value for action")

    if operation != 'action' and action:
        module.fail_json(msg="operation: create|delete are mutually exclusive with action")

    if async_delay and sync is False:
        module.fail_json(msg="async_delay affect synchronous operations only. set sync: true and try again")

def main():
    argument_spec = _augment_arg_spec(vdirect_argument_spec())

    module = _create_ansible_module(argument_spec, False)
    vdirect = vDirect(module)

    operation, action, workflow_template_name, workflow_name, sync, async_delay= vdirect.get_arg_subset(
        'operation',
        'action',
        'workflow_template_name',
        'workflow_name',
        'sync',
        'async_delay')

    validate_arg_spec(module, operation, action, workflow_template_name, sync, async_delay)

    check_mode = module.check_mode

    if operation == 'delete':
        module = vdirect.module = _create_ansible_module(argument_spec)
        if check_mode:
            module.exit_json(changed=False)
        success, messages, duration = vdirect.delete_workflow(workflow_name, sync=sync, async_delay=async_delay)

    if operation == 'create':
        ansible_workflow_arg_spec = vdirect.get_workflow_params(workflow_template_name)
        argument_spec.update(ansible_workflow_arg_spec)
        module = vdirect.module = _create_ansible_module(argument_spec)

        if check_mode:
            module.exit_json(changed=False)

        workflow_args = {}
        for key in module.params:
            if key in ansible_workflow_arg_spec:
                workflow_args[key] = module.params[key]
        success, messages, duration = vdirect.execute_create_workflow(workflow_template_name, workflow_name,
                                                                      workflow_args, sync=sync, async_delay=async_delay)

    if operation == 'action':
        ansible_workflow_arg_spec = vdirect.get_workflow_params(workflow_name, action)
        argument_spec.update(ansible_workflow_arg_spec)
        module = vdirect.module = _create_ansible_module(argument_spec)

        if check_mode:
            module.exit_json(changed=False)

        action_args = {}
        for key in module.params:
            if key in ansible_workflow_arg_spec:
                action_args[key] = module.params[key]
        success, messages, duration = vdirect.execute_workflow_action(workflow_name, action,
                                                                      action_args, sync=sync, async_delay=async_delay)

    if success:
        output = dict(changed=success, duration=duration)
        if len(messages):
            output.update(dict(log=messages))
        module.exit_json(**output)
    else:
        output = dict(msg="operation failed", duration=duration)
        if len(messages):
            output.update(dict(log=messages))
        module.fail_json(**output)




# standard ansible module imports
from ansible.module_utils.basic import *
from ansible.module_utils.vdirect_api import *

if __name__ == '__main__':
    main()
