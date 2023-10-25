from delegate_function import *
import pytest
from util import env

@pytest.mark.parametrize("config", ["test1.yml"])
def test_yaml_file(config):
    sd = DelegateGenerator(filename=config)
    f = TestClass()
    sd.invoke(f, "hello")
    
chains_to_test = [
"""
version: 0.1
sequence:
  - type: TrivialDelegate
  - type: TrivialDelegate
""",
#################################
"""
version: 0.1
sequence: 
  - type: SubprocessDelegate
    delegate_executable_path: /opt/conda/bin/delegate-function-run
""",
#################################
"""
version: 0.1
sequence: 
  - type: DockerDelegate
    docker_image: cfiddle-slurm:21.08.6.1
    temporary_file_root: /scratch/
    delegate_executable_path: /opt/conda/bin/delegate-function-run
    docker_cmd_line_args: ['--entrypoint', '/usr/local/bin/docker-entrypoint.sh', '--mount', 'type=volume,dst=/scratch,source=cse141pp-root_shared_scratch']
""",
##################################
"""
version: 0.1
sequence:
  - type: SlurmDelegate 
    temporary_file_root: /scratch/
    delegate_executable_path: /opt/conda/bin/delegate-function-run
""",
##################################
"""
version: 0.1
sequence:
  - type: SSHDelegate
    user: test_fiddler
    host: ssh-host
    delegate_executable_path: /opt/conda/bin/delegate-function-run
    ssh_options: ["-o", "StrictHostKeyChecking=no"]
"""
,
##################################
#"""
#version: 0.1
#sequence: 
#  - type: SudoDelegate
#    user: cfiddle
#    delegate_executable_path: /opt/conda/bin/delegate-function-run
#"""
"""
version: 0.1
sequence:
  - type: SSHDelegate
    user: test_fiddler
    host: ssh-host
    delegate_executable_path: /opt/conda/bin/delegate-function-run
    ssh_options: ["-o", "StrictHostKeyChecking=no"]
  - type: SlurmDelegate 
    temporary_file_root: /scratch/
    delegate_executable_path: /opt/conda/bin/delegate-function-run
  - type: SSHDelegate
    user: test_fiddler
    host: ssh-host
    delegate_executable_path: /opt/conda/bin/delegate-function-run
    ssh_options: ["-o", "StrictHostKeyChecking=no"]
"""
,
"""
version: 0.1
sequence:
  - type: SuDockerDelegate
    docker_image: cfiddle-slurm:21.08.6.1
    docker_user: test_fiddler
    temporary_file_root: /scratch/
    delegate_executable_path: /opt/conda/bin/delegate-function-run
    docker_cmd_line_args: ["--entrypoint", "/usr/local/bin/docker-entrypoint.sh", "--mount", "type=volume,dst=/scratch,source=cse141pp-root_shared_scratch"]
"""
,
"""
version: 0.1
sequence:
  - type: YAMLDelegate
    configuration_file: trivial.yml
"""
,
"""
version: 0.1
sequence: 
  - type: SudoDelegate
    user: cfiddle
  - type: DockerDelegate
    docker_image: cfiddle-slurm:21.08.6.1
    temporary_file_root: /scratch/
    delegate_executable_path: /opt/conda/bin/delegate-function-run
    docker_cmd_line_args: ['--entrypoint', '/usr/local/bin/docker-entrypoint.sh', '--mount', 'type=volume,dst=/scratch,source=cse141pp-root_shared_scratch']
""",
]

def extract_ids(chains):
    r = []
    for c in chains:
        d = yaml.load(c, Loader=yaml.Loader)
        type_names = [x['type'] for x in d['sequence']]
        name = "_to_".join(type_names) 
        r.append(name)
    return r

@pytest.fixture(scope="module",
                params=chains_to_test,
                ids=extract_ids(chains_to_test))
def SomeYAML(request):
    return request.param

def test_yaml_string(SomeYAML):
    sd = DelegateGenerator(yaml=SomeYAML)
    f = TestClass()
    sd.invoke(f, "hello")

def test_late_binding():
  yaml = """
version: 0.1
sequence:
  - type: LateBoundYAMLDelegate
   # configuration_file: DELEGATE_FUNCTION_CONFIG
"""
  with env(DELEGATE_FUNCTION_CONFIG="trivial.yml"):
    sd = DelegateGenerator(yaml=yaml)
    f = TestClass()
    sd.invoke(f, "hello")

  with pytest.raises(DelegateFunctionException):
    sd = DelegateGenerator(yaml=yaml)
    f = TestClass()
    sd.invoke(f, "hello")

def test_env_vars():
    with env(DOCKER_IMAGE="cfiddle-slurm:21.08.6.1"):
        sd = DelegateGenerator(yaml=
"""
version: 0.1
sequence: 
  - type: DockerDelegate
    docker_image: $DOCKER_IMAGE
    temporary_file_root: /scratch/
    delegate_executable_path: /opt/conda/bin/delegate-function-run
    docker_cmd_line_args: ['--entrypoint', '/usr/local/bin/docker-entrypoint.sh', '--mount', 'type=volume,dst=/scratch,source=cse141pp-root_shared_scratch']
"""
)
        f = TestClass()
        assert sd._delegates[0]()._docker_image == os.environ['DOCKER_IMAGE']
        sd.invoke(f, "hello")

@pytest.mark.slow
def test_yaml_shell_hook():
    t = """
version: 0.1
sequence:
  - type: SubprocessDelegate
    delegate_executable_path: /opt/conda/bin/delegate-function-run
    debug_pre_hook: SHELL
"""
    with env(DELEGATE_FUNCTION_DEBUG_ENABLED='yes'):
      sd = DelegateGenerator(yaml=t)
      f = TestClass()
      sd.invoke(f, "hello")


def test_type_check():
    t = """
version: 0.1
sequence:
  - type: foo
"""
    with pytest.raises(DelegateFunctionException):
        sd = DelegateGenerator(yaml=t)
        f = TestClass()
        sd.invoke(f, "hello")
   