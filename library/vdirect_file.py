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
module: vdirect_file
short_description: Upload template/workflow sources to vDirect
description:
    - This module uploads configuration template source or workflow archives to vDirect.
    - The module supports 'updates' (replacing existing code) or 'uploads' (creating new templates).
    - By default the module assumes it's creating a new template (configuration or workflow).
    - The user can choose to replace an existing template by adding the overwrite=true parameter.
version_added: "2.1"
extends_documentation_fragment: vdirect_api
options:
  template_name:
    description:
      - The name of the configuration template source to update.
    required: False
    default: None
    aliases: [ 'template', 'tmpl' ]
    version_added: "2.1"
  template_file:
    description:
      - The file on disk containing the source to upload.
    required: false
    default: None
    choices: [ 'file' ]
    version_added: "2.1"
  overwrite:
    description:
      - When set to true, overwrites the provided file (template/workflow) if the file already exists.
    required: False
    default: False
    version_added: "2.1"
  workflow_archive:
    description:
      - Zip archive on disk containing workflow files.
    required: False
    default: None
    aliases: [ 'archive', 'zip' ]
    version_added: "2.1"
  device_name:
    description:
      - As template/workflows are uploaded to vDirect, a device_name is not required. However this argument
        is required by the base module (vdirect_api),
        so it is being overwritten to required=False
    required: False
    default: adc
    version_added: "2.1"
notes:
   - The module specification allows providing either template_name + template_file or workflow_archive, not both.
   - Check mode is supported. Check mode tests everything it can without actually uploading the file/archive to vDirect,
     meaning it can't validate the file's syntax.
"""

EXAMPLES = """
# upload template (will fail if already exists)
# (added base vdirect_api mandatory params)
- vdirect_file:
    vdirect_ip: 127.0.0.1
    username: user
    password: password
    device_name: alteon1
    template_name: tmpl1.vm
    template_file: "/tmp/tmpl.vm"

# upload template (will overwrite existing template)
# (added base vdirect_api mandatory params)
- vdirect_file:
    vdirect_ip: 127.0.0.1
    username: user
    password: password
    device_name: alteon1
    template_name: tmpl4.vm
    template_file: "/tmp/tmpl.vm"
    overwrite: true
"""

RETURN = """
changed:
    description: Indicates whether or not the update/upload succeeded.
    returned: always
    type: boolean
    sample: "{ 'changed': true }"
"""


def _augment_arg_spec(arg_spec):
    """
    add module arguments
    :param arg_spec:
    :return:
    """
    arg_spec.update(
        dict(
            template_name=dict(type='str', required=False, aliases=['template', 'tmpl']),
            template_file=dict(type='str', required=False, aliases=['file']),
            overwrite=dict(type='bool', required=False, defaultValue='no'),
            workflow_archive=dict(type='str', required=False, aliases=['archive', 'zip']),
            # overwriting device name. not needed for this module.
            device_name=dict(type='str', required=False, defaultValue='adc')
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
        required_together=(
            ['template_name', 'template_file'],
        ),
        mutually_exclusive=(
            ['template_name', 'workflow_archive'],
            ['template_file', 'workflow_archive']
        ),
        required_one_of=(
            ['template_name', 'workflow_archive'],
        ),
    )
    return module


def main():
    argument_spec = _augment_arg_spec(vdirect_argument_spec())

    module = _create_ansible_module(argument_spec)
    vdirect = vDirect(module)

    template_name, template_file, overwrite, workflow_archive, show_help = vdirect.get_arg_subset('template_name',
                                                                                                  'template_file',
                                                                                                  'overwrite',
                                                                                                  'workflow_archive',
                                                                                                  'help'
                                                                                                  )
    if show_help:
        module.exit_json(changed=False, usage="Uploads provided file/archive to vDirect")

    check_mode = module.check_mode

    if template_file and template_name:

        template_exists = vdirect.find_template(template_name)

        changed = False
        file_data = vdirect.read_file(template_file)
        if overwrite and template_exists:
            template_source = vdirect.download_template(template_name)

            if template_source == file_data:
                changed = False
            else:
                if not check_mode and vdirect.update_template(template_name, file_data):
                    changed = True
        elif not overwrite and template_exists:
            module.fail_json(msg="Failure creating template. template named %s already exists" % template_name)
        elif not template_exists:
            if not check_mode and vdirect.upload_template(template_name, file_data):
                changed = True

        module.exit_json(changed=changed)

    elif workflow_archive:

        changed = False
        workflow_template_name, archive_data = vdirect.read_file(workflow_archive, True)

        workflow_exists = vdirect.find_workflow_template(workflow_template_name)

        if check_mode:
            return False

        if workflow_exists and overwrite:
            changed = vdirect.update_workflow_template(workflow_template_name, archive_data)

        elif not overwrite and workflow_exists:
            module.fail_json(msg="Failure creating workflow template. template named %s already exists"
                                 % workflow_template_name)

        elif not workflow_exists:
            changed = vdirect.upload_workflow_template(archive_data)

        module.exit_json(changed=changed)

    else:
        module.exit_json(msg="invalid arguments supplied")

# standard ansible module imports
from ansible.module_utils.basic import *
from ansible.module_utils.vdirect_api import *

if __name__ == '__main__':
    main()
