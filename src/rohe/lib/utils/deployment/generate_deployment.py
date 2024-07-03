"""
This illustrates how to generate a deployment from a template
Running as an example:
python utilities/generate_deployment.py -i deployment_templates.yaml -d templates -o aa.yaml
"""

import argparse

from jinja2 import Environment, FileSystemLoader, select_autoescape

"""
Input data could be a lot, here is just one example. the information should be obtained from users
"""
deployment_name = "test_deployment"
task_name = "bts_task_name"
image_repo = "tringuyenbts:latest"
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input_file", help="input template")
    parser.add_argument("-o", "--output_file", help="output")
    parser.add_argument("-d", "--template_dir", help="template dir")

    args = parser.parse_args()
    input_file = args.input_file
    output_file = args.output_file
    template_dir = args.template_dir

    env = Environment(
        loader=FileSystemLoader(template_dir), autoescape=select_autoescape()
    )

    template = env.get_template(input_file)
    rendered_deployment = template.render(
        deployment_name=deployment_name, task_name=task_name, image_repo=image_repo
    )
    with open(output_file, "w", encoding="utf-8") as deployment_yaml_file:
        deployment_yaml_file.write(rendered_deployment)
