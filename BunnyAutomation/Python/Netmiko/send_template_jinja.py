import yaml
from my_creds import *
from jinja2 import Environment, FileSystemLoader
from netmiko import ConnectHandler


def build_config():
    my_vars = yaml.safe_load(open("loopback_config_template.yml"))
    env = Environment(loader=FileSystemLoader("./JinjaTemplates"), trim_blocks=True, lstrip_blocks=True) #trim_blocks will trim white space and lstrip_blocks = trims spaces
    template = env.get_template("loopback_template.j2")
    loopback_configuration = template.render(my_vars)
    return loopback_configuration.splitlines()

def push_config_template(commands):
    with ConnectHandler(**my_device) as my_connection:
        create_loopback = my_connection.send_config_set(config_commands=commands)
        print(create_loopback)


if __name__ == "__main__":
    config = build_config()
    push_config_template(config)