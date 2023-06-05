
import yaml, os
import qoa4ml.utils as utils
from jinja2 import Environment, FileSystemLoader



temporary_folder = utils.get_parent_dir(__file__,1)+"/temp"
template_folder = utils.get_parent_dir(__file__,2)+"/templates"
jinja_env = Environment(loader=FileSystemLoader(template_folder))


def kube_generator(nodes, service):
    jinja_var = {}
    deployment = jinja_env.get_template("deployment_templates.yaml")
    folder_path = temporary_folder+"/"+service.name
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    for node in service.node_list:
        jinja_var["node_name"] = nodes[node].name
        jinja_var["task_name"] = service.name
        jinja_var["image_name"] = service.image
        jinja_var["service_replica"] = service.replicas
        jinja_var["ports"] = service.ports
        jinja_var["port_mapping"] = service.port_mapping
        file_path = folder_path+"/"+nodes[node].name+".yaml"
        with open(file_path, "w") as f:
            f.write(deployment.render(jinja_var))