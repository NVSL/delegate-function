import subprocess
import click
import tempfile
import logging as log
import pickle
import os

class BaseDelegate:

    """
    The basic delegate algorithm is:
    
    1.  If I have sub-delegate
        a.  Execute the step of invoking the sub-delegate in my particular way.
    2.  No sub-delegate?
        a.  Then execute the function in my particular way.
    
    As a consequence this means that the only delegate that should ever access or need the original invocation's arguments is the last delegate in the the chain.
    
    """
    def __init__(self, subdelegate=None):
        self._subdelegate = subdelegate
        
    def delegated_invoke(self):
        return getattr(self._obj, self._method)(*self._argc, **self._kwargs)

    def invoke(self, obj, method, *argc, **kwargs):
        self._obj = obj
        self._method = method
        self._argc = argc
        self._kwargs = kwargs
        self.do_invoke()

    def do_invoke(self):
        raise NotImplemented()
        

class TrivialDelegate(BaseDelegate):

    def delegated_invoke(self):
        if self._subdelegate:
            log.debug(f"Delegating to subdelegate: {self._subdelegate}")
            return self._subdelegate.invoke(self._obj, self._method, *self._argc, **self._kwargs)
        else:
            log.debug(f"Invoking method locally")
            return getattr(self._obj, self._method)(*self._argc, **self._kwargs)

    def do_invoke(self):
        self.delegated_invoke()

        
class SubprocessDelegate(BaseDelegate):

    def __init__(self, *argc, temporary_file_root=None, **kwargs):
        super().__init__(*argc, **kwargs)
        self._temporary_file_root = temporary_file_root

    def _run_function_in_external_process(self):
        log.debug(f"SubprocessDelegate running {self._command}")
        self._invoke_shell(self._command)
        
    def do_invoke(self):
        with tempfile.NamedTemporaryFile(dir=self._temporary_file_root) as delegate_before:
            pickle.dump(self, delegate_before)
            delegate_before.flush()
            with tempfile.NamedTemporaryFile(dir=self._temporary_file_root) as delegate_after:
                            
                self._command = ["delegate-function-run",
                                 "--delegate-before", delegate_before.name,
                                 "--delegate-after", delegate_after.name,
                                 "--log-level", str(log.root.level)]
                
                self._run_function_in_external_process()
                after = pickle.load(delegate_after)

                self._obj.__dict__.update(after['delegate']._obj.__dict__)
                return after['return_value']

    def _invoke_shell(self, cmd):
        try:
            log.debug(f"Executing {' '.join(cmd)=}")
            r = subprocess.run(cmd, check=True, capture_output=True)
            log.debug(f"{r.stdout.decode()}")
            log.debug(f"{r.stderr.decode()}")
        except subprocess.CalledProcessError as e:
            raise DelegateFunctionException(f"Delegate subprocess execution failed: {e} {e.stdout.decode()} {e.stderr.decode()}")

        
class SlurmDelegate(SubprocessDelegate):
    def __init__(self):
        super().__init__(temporary_file_root=".")

    def _run_function_in_external_process(self):
        command = ['salloc', 'srun'] + self._command
        log.debug(f"SlurmDelegateDelegate running {command}")
        self._invoke_shell(command)


class DockerDelegate(SubprocessDelegate):
    def __init__(self, docker_image, root_replacement):
        super().__init__(temporary_file_root=".")
        self._root_replacement = root_replacement
        self._docker_image = docker_image

    def _replace_root(self, path):
        return path.replace(*self._root_replacement)
        
    def _run_function_in_external_process(self):
        
        command = ['docker', 'run',
                   '--workdir', '/delegate',
                   '--mount', f'type=bind,source={self._replace_root(os.getcwd())},dst={os.getcwd()}',
                   self._docker_image] + self._command
        log.debug(f"SubprocessDelegate running {command}")
        log.debug(f"SubprocessDelegate running {' '.join(command)}")
        self._invoke_shell(command)


class DelegateFunctionException(Exception):
    pass

@click.command()
@click.option('--delegate-before', required=True, type=click.File("rb"), help="File with the initial state of the delegate.")
@click.option('--delegate-after', required=True, type=click.File("wb"), help="File with delegate state after execution")
@click.option('--log-level', default=None, type=int, help="Verbosity level for logging.")
def delegate_function_run(delegate_before, delegate_after, log_level):
    import platform
    if log_level is not None:
        log.root.setLevel(log_level)
    print(f"Executing in delegate process on {platform.node()}")
    do_delegate_function_run(delegate_before, delegate_after)
    
def do_delegate_function_run(delegate_before, delegate_after):
    try:
        delegate_object = pickle.load(delegate_before)
    except Exception as e:
        raise DelegateFunctionException(f"Failed to load picked delegate: {e}")
    r = delegate_object.delegated_invoke()
    pickle.dump(dict(delegate=delegate_object, return_value=r), delegate_after)

        
class TestClass():

    def __init__(self):
        self._value = 0
        
    def hello(self):
        print(f"hello world.  I'm in process {os.getpid()}")
        return os.getpid()

    def set_value(self, v):
        self._value = v
