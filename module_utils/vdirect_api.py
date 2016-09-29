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

# ==================================================================

ALLOWED_PARAM_TYPES = ['string', 'int', 'ip', 'bool', 'ipv4', 'ipv6', 'adcService']
STRING_PARAM_TYPES = ['ip', 'ipv4', 'ipv6', 'string', 'adcService']

try:
    import inspect
    import json
    import zipfile
    from xml.dom import minidom
    from xml.parsers.expat import ExpatError
    import time

    HAS_LIBS = True
except ImportError:
    HAS_LIBS = False

from ansible.module_utils.urls import fetch_url


def vdirect_argument_spec():
    """
    arguments definition for module
    :return:
    """
    return dict(
        vdirect_ip=dict(type='str', required=True),
        secondary_vdirect_ip=dict(type='str', required=False, default=""),
        username=dict(type='str', aliases=['user', 'admin'], required=True),
        password=dict(type='str', aliases=['pass', 'pwd'], required=True, no_log=True),
        port=dict(type='int', required=False, default=2189),
        scheme=dict(type='str', alias=['protocol'], default='https', choices=['http', 'https']),
        timeout=dict(type='int', required=False, default=180),
        validate_certs=dict(type='bool', default='yes'),
        device_type=dict(type='str', default='alteon'),
        device_name=dict(type='str', required=True, aliases=['device']),
        help=dict(type='bool', required=False, default='no')
    )


def vdirect_parse_arguments(module):

    def _get_param(param_name):
        return module.params.get(param_name, None)

    return(
        _get_param('vdirect_ip'),
        _get_param('secondary_vdirect_ip'),
        _get_param('username'),
        _get_param('password'),
        _get_param('port'),
        _get_param('scheme'),
        _get_param('timeout'),
        _get_param('validate_certs'),
        _get_param('device_type'),
        _get_param('device_name'),
        _get_param('help'),
    )


class vDirect(object):

    vdirect_version = ""
    min_vdirect_version = "3.40"

    primary_found = False

    class RequestMethods(object):
        get = 'GET'
        GET = 'GET'
        put = 'PUT'
        PUT = 'PUT'
        post = 'POST'
        POST = 'POST'
        delete = 'DELETE'
        DELETE = 'DELETE'

        def __init__(self):
            pass

    def __init__(self, module):

        self.module = module
        self.vdirect_ip, self.secondary_vdirect_ip, self.username, self.password, self.port, self.scheme, self.timeout,\
            self.validate_certs, self.device_type, self.device_name, self.show_help = vdirect_parse_arguments(module)

        self.device_parameter_name = ""

        self._get_primary_vdirect()

        self._check_version()

        if not HAS_LIBS:
            module.fail_json(msg="required python libraries (inspect|json|ZipFile|minidom|expatError|time) missing")

    def _get_primary_vdirect(self):

        if not vDirect.primary_found:

            error_status = {
                404: "Contacted secondary vDirect instance, primary not supplied",
                -1: "Error connecting to vDirect",
                500: "Error 500 connecting to vDirect"
            }

            url = "api/ha/active"
            resp, info = self._http_get_request(url, handle_errors=False, skip_auth=True)
            status_code = info.get('status')
            if status_code != 204:
                if self.secondary_vdirect_ip != "":
                    self.vdirect_ip, self.secondary_vdirect_ip = self.secondary_vdirect_ip, self.vdirect_ip
                    resp, info = self._http_get_request(url, handle_errors=False, skip_auth=True)
                    status_code = info.get('status')
                    if status_code != 204:
                        self.module.fail_json(msg="Failed to contact vdirect server")
                else:
                    self.module.fail_json(msg=error_status.get(status_code))

            vDirect.primary_found = True

    def _check_version(self):

        if not vDirect.vdirect_version:
            url = "api"
            resp, info = self._http_get_request(url, skip_auth=True, response_is_json=True)

            try:
                actual_version = resp.get('vDirectVersion')

                if '-SNAPSHOT' in actual_version:
                    vDirect.vdirect_version = actual_version[:actual_version.index('-')]
                else:
                    vDirect.vdirect_version = actual_version[:actual_version.index(' ')]

                minver_tuple = map(int, (vDirect.min_vdirect_version.split('.')))
                ver_tuple = map(int, (vDirect.vdirect_version.split('.')))

                if minver_tuple > ver_tuple:
                    self.module.fail_json(msg="vDirect version %s is not supported."
                                              % actual_version, resp=resp, info=info)

            except (KeyError, ValueError, TypeError) as ex:
                self.module.fail_json(msg="Error getting version", resp=resp, info=info, error=ex.message)

    def _add_auth_headers(self):

        self.module.params['force_basic_auth'] = True
        self.module.params['url_username'] = self.username
        self.module.params['url_password'] = self.password

    def _rem_auth_headers(self):

        self.module.params['force_basic_auth'] = False
        self.module.params.pop('url_username', None)
        self.module.params.pop('url_password', None)

    def _make_http_request(self, url, request_method=RequestMethods.get, data=None,
                           request_properties=None, handle_errors=True,
                           response_is_json=True, skip_auth=False,
                           url_is_actual=False):

        if skip_auth:
            self._rem_auth_headers()
        else:
            if not self.module.params.get('force_basic_auth', False):
                self._add_auth_headers()

        if url_is_actual:
            actual_url = url
        else:
            actual_url = "%s://%s:%s/%s" % (self.scheme, self.vdirect_ip, self.port, url)

        resp, info = fetch_url(self.module, actual_url, headers=request_properties, method=request_method, data=data,
                               timeout=self.timeout, force=True)

        status_code = info['status']

        if handle_errors and status_code != 200:
            try:
                resp = json.loads(info['body'])
                if 'body' in info:
                    del info['body']

                if 'message' in resp:
                    resp = resp['message']
            except Exception:
                pass

            self.module.fail_json(msg="%s [%d]" % (info['msg'], info['status']), resp=resp)

        if response_is_json:
            resp = _format_rest_response(resp)
        return resp, info

    def _http_get_request(self, url, request_properties=None, handle_errors=True,
                          response_is_json=True, skip_auth=False,
                          url_is_actual=False):

        return self._make_http_request(url, request_method=self.RequestMethods.get,
                                       request_properties=request_properties, handle_errors=handle_errors,
                                       response_is_json=response_is_json, skip_auth=skip_auth,
                                       url_is_actual=url_is_actual)

    def _http_get_request_simple(self, url):
        resp, info = self._http_get_request(url, handle_errors=False)

        if 'status' in info:
            if info.get('status') == 404:
                return False
            elif info.get('status') == 200:
                return True
            else:
                self._unknown_detailed_fail(info)
        else:
            self.module.fail_json(msg="http request handling failed", info=info, resp=resp)

    def _http_post_request(self, url, data=None, request_properties=None, handle_errors=True):

        return self._make_http_request(url, request_method=self.RequestMethods.post,
                                       data=data, request_properties=request_properties, handle_errors=handle_errors)

    def _http_put_request(self, url, data, request_properties=None, handle_errors=True):

        return self._make_http_request(url, request_method=self.RequestMethods.put,
                                       data=data, request_properties=request_properties, handle_errors=handle_errors)

    def _http_delete_request(self, url, handle_errors=False):
        return self._make_http_request(url, request_method=self.RequestMethods.delete,
                                       handle_errors=handle_errors)

    def _get_method(self, prefix):

        search_term = "%s_%s" % (prefix, self.device_type.lower())
        methods = [value for name, value in
                   inspect.getmembers(self, predicate=inspect.ismethod) if search_term in name]
        if len(methods) != 1:
            self.module.fail_json(msg="method not found. check device_type", methods=methods, search_term=search_term)

        return methods[0]

    def _handle_template_response(self, info, resp):

        error_status = {
            404: "error updating template. the requested template does not exist",
            400: "error updating template. the velocity source is invalid",
            409: "error updating template. a template already exists with the name specified"
        }

        ok_status = [200, 201, 204]

        if 'status' in info:
            status = info.get('status')
            if status in error_status:
                self.module.fail_json(msg=error_status[status])
            elif status in ok_status:
                return True
            else:
                self.module.fail_json(msg="http request handling failed", info=info, resp=resp)
        self.module.fail_json(msg="http request handling failed", info=info, resp=resp)

    def get_arg_subset(self, *args):
        """
        get a subset of module parameters
        :param args:
        :return: parameter tuple
        """
        parsed_args = ()

        for arg in args:
            parsed_args = parsed_args + (self.module.params.get(arg, None),)

        if len(args) == 1:
            return parsed_args[0]
        return parsed_args

    def read_file(self, file_name, binary=False):
        """
        read file from disk on ansible controller executing module
        used for uploading template/workflow source to vDirect
        :param file_name:
        :param binary:
        :return:
        """
        try:
            if binary:
                with open(file_name, 'rb') as r:
                    content = r.read()
                archive_name = self._get_workflow_name(file_name)
                return archive_name, content
            else:
                content = open(file_name, 'r').read()
                return content
        except IOError as ioex:
            self.module.fail_json(msg="error reading file", resp=ioex.strerror)

    def _get_workflow_name(self, archive_file):
        try:
            archive = zipfile.ZipFile(archive_file)
            if 'workflow.xml' not in archive.namelist():
                self.module.fail_json(msg="archive file '%s' not valid. must contain workflow.xml file" % archive_file)
            else:
                workflow_xml = archive.read('workflow.xml')
                xmldom = minidom.parseString(workflow_xml)
                workflow_name = xmldom.getElementsByTagName('workflow')[0].attributes['name'].value
                workflow_name = workflow_name.encode('ascii', 'ignore')
                archive.close()
                return workflow_name
        except zipfile.BadZipfile:
            self.module.fail_json(msg="archive file '%s' is not a valid zip file" % archive_file)
        except ExpatError:
            self.module.fail_json(msg="workflow.xml parsing failed")
        except (IndexError, KeyError):
            self.module.fail_json(msg="workflow.xml must contain name attribute")

    # workflow template methods
    def find_workflow_template(self, workflow_template_name):
        """
        :param workflow_template_name:
        :return: boolean
        """
        url = "api/workflowTemplate/%s" % workflow_template_name
        return self._http_get_request_simple(url)

    def upload_workflow_template(self, workflow_archive_data):
        """
        create new workflow template
        :param workflow_archive_data:
        :return:
        """
        url = "api/workflowTemplate?failIfInvalid=true"
        props = {
            "Content-Type": "application/x-zip-compressed"
        }
        resp, info = self._http_post_request(url, workflow_archive_data, props, False)

        return self._handle_template_response(info, resp)

    def update_workflow_template(self, workflow_template_name, workflow_archive_data):
        """
        update workflow template source
        :param workflow_template_name:
        :param workflow_archive_data:
        :return:
        """
        url = "api/workflowTemplate/%s/archive?failIfInvalid=true" % workflow_template_name

        props = {
            "Content-Type": "application/x-zip-compressed"
        }

        resp, info = self._http_put_request(url, workflow_archive_data, props, False)

        return self._handle_template_response(info, resp)

    # workflow methods

    def delete_workflow(self, workflow_name, sync, async_delay):
        """
        run the delete action of the workflow
        :param workflow_name:
        :param sync:
        :param async_delay:
        :return:
        """
        url = "api/workflow/%s" % workflow_name
        resp, info = self._http_delete_request(url)

        if 'status' in info:
            if info.get('status') == 404:
                self.module.fail_json(msg="workflow (%s) not found. delete failed" % workflow_name)
            elif info.get('status') == 202:
                if not sync:
                    return False
                return self.async_execute(async_delay, resp)

            else:
                self._unknown_detailed_fail(info)
        else:
            self.module.fail_json(msg="http request handling failed", info=info, resp=resp)

    def _unknown_detailed_fail(self, info):
        json_body = ""
        if 'body' in info:
            try:
                json_body = json.loads(info['body'])
            except Exception:
                json_body = info['body']
            if 'message' in json_body:
                json_body = json_body.get('message')
        self.module.fail_json(msg="%s [%d]" % (info['msg'], info['status']), err_body=json_body)

    def async_execute(self, async_delay, resp):
        complete = resp.get('complete')
        uri = resp.get('uri')
        count = 0
        while not complete:
            resp, info = self._http_get_request(url=uri, handle_errors=False, url_is_actual=True)
            count += 1
            if info.get('status', -1) != 200:
                self.module.fail_json(msg="workflow operation failed.", info=info, count=count, resp=resp)
            else:
                complete = resp.get('complete')
                uri = resp.get('uri')
                if not complete:
                    time.sleep(async_delay)

        success = resp.get('success')
        messages = resp.get('messages', [])
        duration = resp.get('duration')
        return success, messages, duration

    def get_workflow_params(self, object_name, action_name='createWorkflow', raw=False):
        """
        get parameter definition for workflow action
        :param object_name:
        :param action_name:
        :param raw:
        :return:
        """
        if action_name == 'createWorkflow':
            url = "api/workflowTemplate/%s/action/createWorkflow" % object_name
        else:
            url = "api/workflow/%s/action/%s" % (object_name, action_name)

        resp, info = self._http_get_request(url, handle_errors=False)

        status = info.get('status', -1)

        if status == 204:
            info = dict(
                status=404,
                body=dict(message="workflow action not found"),
                msg="HTTP Error 404: Not Found [404]"
            )
            status = 404

        if status != 200:
            self._unknown_detailed_fail(info)

        if raw:
            return resp
        else:
            return self._map_wfcreate_params_to_args(resp)

    def execute_workflow_action(self, workflow_name, action_name, params, sync, async_delay):
        """
        run workflow action
        :param workflow_name:
        :param action_name:
        :param params:
        :param sync:
        :param async_delay:
        :return:
        """
        vdirect_params = self.get_workflow_params(workflow_name, action_name, raw=True)

        url = "api/workflow/%s/action/%s" % (workflow_name, action_name)

        resp, info = self._post_execute(url, vdirect_params, params)

        if 'status' in info:
            if info.get('status') == 404:
                self.module.fail_json(msg="workflow (%s) not found. execute failed" % workflow_name)
            if info.get('status') == 400:
                body = info.get('body', {})
                body = json.loads(body)
                msg = body.get('message', '')
                self.module.fail_json(
                    msg="The inputs provided are invalid or do not include all the required inputs for the action",
                    msg_detail=msg)

            elif info.get('status') == 202:
                if not sync:
                    return False
                return self.async_execute(async_delay, resp)
            else:
                self._unknown_detailed_fail(info)
        else:
            self.module.fail_json(msg="http request handling failed", info=info, resp=resp)

    def execute_create_workflow(self, workflow_template_name, workflow_name, params, sync, async_delay):
        """
        run createWorkflow action - creates a workflow from the template
        :param workflow_template_name:
        :param workflow_name:
        :param params:
        :param sync:
        :param async_delay:
        :return:
        """
        vdirect_params = self.get_workflow_params(workflow_template_name, raw=True)

        url = "api/workflowTemplate/%s?name=%s" % (workflow_template_name, workflow_name)

        resp, info = self._post_execute(url, vdirect_params, params)
        if 'status' in info:
            if info.get('status') == 404:
                self.module.fail_json(msg="workflow template (%s) not found. create failed" % workflow_template_name)
            if info.get('status') == 409:
                self.module.fail_json(msg="workflow with name (%s) already exists. create failed" % workflow_name)
            if info.get('status') == 400:
                body = info.get('body', {})
                body = json.loads(body)
                msg = body.get('message', '')
                self.module.fail_json(msg="The specified parameters are invalid or incomplete. create failed",
                                      msg_detail=msg)

            elif info.get('status') == 202:
                if not sync:
                    return False
                return self.async_execute(async_delay, resp)
            else:
                self._unknown_detailed_fail(info)
        else:
            self.module.fail_json(msg="http request handling failed", info=info, resp=resp)

    def _post_execute(self, url, vdirect_params, ansible_params):

        props = {
            "Content-Type": "application/vnd.com.radware.vdirect.template-parameters+json"
        }

        data = {
            "parameters": {},
            "deviceConnections": {}
        }

        device_connections = {}

        if 'devices' in vdirect_params:
            for device_definition in vdirect_params['devices']:
                device_connections[device_definition['name']] = {}
                if device_definition['maxLength'] == 1:
                    device_connections[device_definition['name']] = \
                        [{"deviceId": {"name": ansible_params[device_definition['name']]}}]
                else:
                    device_connections[device_definition['name']] = []
                    for device in ansible_params[device_definition['name']]:
                        device_connections[device_definition['name']].append({"deviceId": {"name": device}})
            data['deviceConnections'].update(device_connections)

        for key in device_connections:
            del ansible_params[key]

        data['parameters'] = ansible_params

        resp, info = self._http_post_request(url, data=json.dumps(data), request_properties=props, handle_errors=False)

        return resp, info

    # template methods
    def find_template(self, template_name):
        """
        :param template_name:
        :return: boolean
        """
        url = "api/template/%s" % template_name
        return self._http_get_request_simple(url)

    def update_template(self, template_name, template_file_data):
        """
        replace template source
        :param template_name:
        :param template_file_data:
        :return:
        """
        url = "api/template/%s/source?failIfInvalid=true" % template_name
        props = {
            "Content-Type": "text/x-velocity"
        }

        resp, info = self._http_put_request(url, template_file_data, props, False)

        return self._handle_template_response(info, resp)

    def upload_template(self, template_name, template_file_data):
        """
        create new template from source
        :param template_name:
        :param template_file_data:
        :return:
        """
        url = "api/template?name=%s&failIfInvalid=true" % template_name
        props = {
            "Content-Type": "text/x-velocity"
        }

        resp, info = self._http_post_request(url, template_file_data, props, False)

        return self._handle_template_response(info, resp)

    def validate_template(self, template_name, show_help=False):
        """
        check if template is valid, configured for one device, and matches the device type argument
        :param template_name:
        :param show_help:
        :return:
        """
        url = "api/template/%s" % template_name
        resp, info = self._http_get_request(url)

        try:
            if not resp['valid']:
                self.module.fail_json(msg="Requested template is not valid", validation_error=resp['message'])

            device_count = len(resp['info']['devices'])

            if device_count > 1:
                self.module.fail_json(msg="Multi device template not supported", info=resp['info'])
            else:
                template_device_type = resp['info']['devices'][0]['type']
                self.device_parameter_name = resp['info']['devices'][0]['name']

                if template_device_type != self.device_type and not show_help:
                    self.module.fail_json(msg="Device type mismatch", info=resp['info'], device_user=self.device_type,
                                          device_template=template_device_type)
                params = self._map_params_to_args(resp, show_help)

                if show_help:
                    params['device_type'] = template_device_type

                return params
        except (IndexError, KeyError):
            self.module.fail_json(msg="Unable to parse response", info=resp['info'])

    def download_template(self, template_name):
        """
        get template source
        :param template_name:
        :return:
        """
        url = "api/template/%s/source" % template_name
        resp, info = self._http_get_request(url, response_is_json=False)
        if resp:
            resp = resp.read()
        return resp

    def execute_template(self, template_name, template_args, check_mode):
        """

        :param template_name:
        :param template_args:
        :param check_mode:
        :return: template output parameters
        """
        method = self._get_method("execute_template")
        return method(template_name, template_args, check_mode)

    def diff(self):

        method = self._get_method("diff")
        return method()

    def commit(self):
        """
        apply + save of uncommitted changes
        :return: boolean
        """
        method = self._get_method("commit")
        return method()

    def _execute_template_alteon(self, template_name, template_args, check_mode):

        diff_before = self.diff()
        resp, info, data = self._execute_template(template_name, template_args, self.device_parameter_name, check_mode)
        diff_after = self.diff()
        changed = diff_before != diff_after

        return resp, info, data, changed

    def _execute_template_defensepro(self, template_name, template_args, check_mode):

        return self._execute_template(
            template_name,
            template_args,
            self.device_parameter_name,
            check_mode
        ) + (not check_mode,)

    def _execute_template_appwall(self, template_name, template_args, check_mode):

        self.module.fail_json(msg="AppWall no supported in template module")

    def _execute_template(self, template_name, template_args, device_arg, check_mode):

        url = "api/template/" + template_name
        props = {
            "Content-Type": "application/vnd.com.radware.vdirect.template-parameters+json"
        }

        data = {
            "parameters": template_args,
            "deviceConnections": {
                device_arg: [{
                    "deviceId": {
                        "name": self.device_name
                    }
                }]
            }
        }

        if check_mode:
            data['dryRun'] = True

        resp, info = self._http_post_request(url, data=json.dumps(data), request_properties=props)

        return resp, info, data


    def _commit_alteon(self):

        uri = "api/adc/%s/device?action=commit"
        return self._commit(uri)

    def _commit_defensepro(self):

        uri = "api/defensePro/%s/device?action=commit"
        return self._commit(uri)

    def _commit_appwall(self):

        uri = "api/appWall/%s/device?action=commit"
        return self._commit(uri)

    def _commit(self, uri):

        url = uri % self.device_name
        resp, info = self._http_post_request(url=url, handle_errors=False)
        if 'status' in info:
            if info['status'] == 200:
                changed = resp['commitNeeded']
                return changed
            else:
                self._unknown_detailed_fail(info)
        self.module.fail_json(msg="http request handling failed", info=info, resp=resp)

    def _diff_alteon(self):

        uri = "api/adc/%s/config?diff=cur"
        return self._diff(uri)

    def _diff_defensepro(self):

        self.module.fail_json(msg="diff unsupported for this device type")

    def _diff_appwall(self):

        self.module.fail_json(msg="diff unsupported for this device type")

    def _diff(self, uri):

        url = uri % self.device_name
        resp, info = self._http_get_request(url=url, response_is_json=False)
        resp = resp.read()
        return resp

    def _map_wfcreate_params_to_args(self, api_resp):

        try:
            params = {}
            for device in api_resp.get('devices', []):
                params[device['name']] = {}
                if device['maxLength'] == 1:
                    params[device['name']]['type'] = 'str'
                else:
                    params[device['name']]['type'] = 'list'
                params[device['name']]['required'] = True

            for param in api_resp.get('properties', []):
                if 'direction' not in param or param['direction'] in ['in', 'inout']:
                    params[param['name']] = {}

                    new_param = params[param['name']]
                    if param['type'] not in ALLOWED_PARAM_TYPES:
                        if param['type'].endswith('[]'):
                            new_param['type'] = 'list'
                        else:
                            new_param['type'] = 'dict'
                    elif param['type'] in STRING_PARAM_TYPES:
                        new_param['type'] = 'str'
                    else:
                        _copy_param_to_dict(param, new_param, 'type')

                    if 'defaultValue' in param:
                        new_param['default'] = param['defaultValue']
                        new_param['required'] = False
                    else:
                        new_param['required'] = True

                    if 'values' in param:
                        new_param['choices'] = param['values']

            return params
        except KeyError as kex:
            self.module.fail_json(msg="Error parsing response", e=kex.message)

    def _map_params_to_args(self, api_resp, with_help=False):

        try:
            new_params = {}
            if 'parameters' not in api_resp['info']:
                return new_params

            params = api_resp['info']['parameters']
            for param in params:
                if 'direction' not in param or param['direction'] in ['in', 'inout']:
                    new_params[param['name']] = {}
                    new_param = new_params[param['name']]
                    if param['type'] not in ALLOWED_PARAM_TYPES:
                        if param['type'].endswith('[]'):
                            new_param['type'] = 'list'
                        else:
                            new_param['type'] = 'dict'
                    elif param['type'] in STRING_PARAM_TYPES:
                        new_param['type'] = 'str'
                    else:
                        _copy_param_to_dict(param, new_param, 'type')

                    if 'defaultValue' in param:
                        new_param['default'] = param['defaultValue']
                        new_param['required'] = False
                    else:
                        new_param['required'] = True

                    if 'values' in param:
                        new_param['choices'] = param['values']

                    if with_help:
                        for key in ('prompt', 'pattern', 'separator', 'min', 'max', 'maxCharLength', 'minCharLength'):
                            _copy_param_to_dict(param, new_param, key)
            if with_help:
                for par in new_params:
                    if new_params[par]['type'] == 'dict':
                        for old_param in api_resp['info']['parameters']:
                            if old_param['name'] == par:
                                for utype in api_resp['info']['userTypes']:
                                    if utype['name'] == old_param['type']:
                                        new_params[par]['definition'] = utype['fields']

            return new_params
        except KeyError as kex:
            self.module.fail_json(msg="Error parsing response", e=kex.message)


def _format_rest_response(resp):

    try:
        resp = resp.read()
        resp = json.loads(resp)
        return resp
    except Exception:
        return None


def _copy_param_to_dict(src_dict, dst_dict, key_name, new_key_name=None):

    if key_name in src_dict:
        if new_key_name is None:
            dst_dict[key_name] = src_dict[key_name]
        else:
            dst_dict[new_key_name] = src_dict[key_name]
