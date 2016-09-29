#Ansible vDirect integration

##Overview:
[vDirect](https://www.radware.com/Products/vDirect/) is a software-based automation and orchestration controller that integrates Radware's ADC and security products with networking virtualization and automation solutions. 
The Ansible vDirect modules allow using ansible to automate Radware solutions via vDirect and its REST API.
The following Radware solutions are supported:

 - [Alteon](https://www.radware.com/Products/Alteon/)
 - [DefensePro](https://www.radware.com/Products/DefensePro/)

### Note: 
Please be aware that Radware is working towards having these modules available with the ansible github repository.

##Available modules:

###vDirect_file:
Upload configuration templates or workflow archives to vDirect. Supports projects where configuration templates/workflows are kept in source control. Simply write an ansible play that pulls the files out of source control, uploads them to vDirect, and uses one of the other modules to execute them.

###vDirect_template:
Execute vDirect configuration templates. This dynamic module allows executing any configuration template found on vDirect. 
Flow:

1. Connect to vDirect.
2. Validate that the template exists and is in a valid state.
3. Pull template configuration (parameters and devices).
4. Verify that all parameters/devices were supplied to ansible.
5. Execute the configuration template.

###vDirect_workflow:
Allows creating workflows from workflow templates, executing workflow actions, or deleting workflows. 
The flow of this module is very similar to that of vDirect_template.

###vDirect_commit:
Multiple configuration templates can be used to manage the configuration of devices controlled by vDirect. Committing the changes one configuration template at a time not only wastes time, but requires that each template make a coherent change to the configuration.
Making all of the changes first and applying them once makes more sense (and saves time).
This module can be used to issue a commit (Apply + Save) instruction to the device managed by vDirect.
This allows writing playbooks that execute several configuration templates and issue a single commit as the last step at the end.

##Requirements:
1. Ansible (supported ansible version 2.1 release)
2. Radware vDirect instance 3.40
3. Radware Alteon 30.2.3

##Support:
These Ansible modules for vDirect are supported by Radware only if used with Radware’s vDirect product and only if the customer is under an active and fully paid support service contract. This means that only Radware customers who have purchased and fully paid for Radware’s support services are eligible for support to these Ansible modules.

##Installation
setup.yml is a playbook that copies the shared code to ansible/module_utils and the modules to ansible/modules/extras/network/radware.

1. Clone this repo to your ansible control machine.
2. Change into the cloned directory.
3. Run 
 
 ```ansible-playbook -v setup.yml.```

**Note**: The playbook copies files to ansible folders on the machine. Run the playbook with a user account that has write permissions to these locations.

##Testing
The samples folder contains a sample configuration template and a workflow, and a playbook that will upload them to vDirect, execute the template, create a workflow, update it, and finally delete it.
The configuration template and the workflow do not make changes to your Alteon configuration, but it's still a good idea to test the playbook in a test environment.

You need to supply the playbook with the vDirect IP address, login credentials, and an Alteon device name (as registered in vDirect).

To run the playbook:

```ansible-playbook -v simple_tests.yml -e "vdirect_username=USERNAME vdirect_password=PASSWORD vdirect_ip=IP alteon=ALTEON"```

Add the verbosity flag (-v) to see verbose output of template and workflow execution.




