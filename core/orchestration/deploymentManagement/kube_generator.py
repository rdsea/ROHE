
import yaml, os
import qoa4ml.qoaUtils as qoaUtils
from jinja2 import Environment, FileSystemLoader
rohe_dir=os.getenv("ROHE_PATH")
if (rohe_dir is None):
    print(f'ROHE DIR is not set. Assume the current dir')
    rohe_dir="."
rohe_config_path=os.path.join(rohe_dir,"config","rohe.yaml")
rohe_conf=qoaUtils.load_config(rohe_config_path)
temporary_folder = rohe_conf["ROHE_TEMP_DIR"]##qoaUtils.get_parent_dir(__file__,3)+"/services/orchestration/temp"
template_folder = os.path.join(rohe_dir,"templates")#qoaUtils.get_parent_dir(__file__,3)+"/templates"
jinja_env = Environment(loader=FileSystemLoader(template_folder))
deployment = jinja_env.get_template("deployment_templates.yaml")


def kube_generator(serviceInstance):
    jinja_var = {}
    service = serviceInstance.service
    node = serviceInstance.node
    folder_path = temporary_folder
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    folder_path = temporary_folder+"/"+service.name
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    jinja_var["node_name"] = node.name
    jinja_var["task_name"] = service.name
    jinja_var["image_name"] = service.image
    jinja_var["service_replica"] = service.replicas
    jinja_var["ports"] = service.ports
    jinja_var["port_mapping"] = service.port_mapping
    file_path = folder_path+"/"+serviceInstance.id+".yaml"
    with open(file_path, "w") as f:
        f.write(deployment.render(jinja_var))