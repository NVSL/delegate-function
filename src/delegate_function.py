from contextlib import contextmanager
import shutil
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
        
    def invoke(self, obj, method, *argc, **kwargs):
        """ 
        The sole public method of this class exceutes :code:`obj.method(*argc, **kwargs)` using the supplied sub-delegates.

        If there is no sub-delegate, it will execute the function directly. 
        """
        self._obj = obj
        self._method = method
        self._argc = argc
        self._kwargs = kwargs
        return self._do_invoke()


    def _do_invoke(self):
        """
        Override this to implement your delegate's functionality.  This method should return the result of and cause the side-effects of
        :code:`self._delegated_inovke()`
        """
        return self._delegated_invoke()


    def _delegated_invoke(self):
        if self._subdelegate:
            log.debug(f"Delegating to subdelegate: {self._subdelegate}")
            return self._subdelegate.invoke(self._obj, self._method, *self._argc, **self._kwargs)
        else:
            log.debug(f"Invoking method locally")
            return getattr(self._obj, self._method)(*self._argc, **self._kwargs)

class TrivialDelegate(BaseDelegate):
    pass

@contextmanager
def working_directory(path):
    here = os.getcwd()
    try:
        os.chdir(path)
        yield path
    finally:
        os.chdir(here)

class TemporaryDirectoryDelegate(BaseDelegate):
    def _do_invoke(self):
        with tempfile.TemporaryDirectory() as d:
            with working_directory(d):
                super()._do_invoke()

class SubprocessDelegate(BaseDelegate):

    def __init__(self, *argc, temporary_file_root=None, **kwargs): 
        super().__init__(*argc, **kwargs)
        self._temporary_file_root = temporary_file_root

        
    def _do_invoke(self):
        with tempfile.NamedTemporaryFile(dir=self._temporary_file_root) as delegate_before:
            pickle.dump(self, delegate_before)
            delegate_before.flush()
            with tempfile.NamedTemporaryFile(dir=self._temporary_file_root) as delegate_after:
                            
                self._command = [shutil.which("delegate-function-run"),
                                 "--delegate-before", delegate_before.name,
                                 "--delegate-after", delegate_after.name,
                                 "--log-level", str(log.root.level)]
                
                self._run_function_in_external_process()
                after = pickle.load(delegate_after)

                self._obj.__dict__.update(after['delegate']._obj.__dict__)
                return after['return_value']

    def _run_function_in_external_process(self):
        log.debug(f"SubprocessDelegate running {self._command}")
        self._invoke_shell(self._command)

    def _invoke_shell(self, cmd):
        try:
            log.debug(f"{type(self).__name__} Executing {' '.join(cmd)=}")
            r = subprocess.run(cmd, check=True, capture_output=True)
            log.debug(f"{r.stdout.decode()}")
            log.debug(f"{r.stderr.decode()}")
        except subprocess.CalledProcessError as e:
            raise DelegateFunctionException(f"Delegate subprocess execution failed: {e} {e.stdout.decode()} {e.stderr.decode()}")


class SudoDelegate(SubprocessDelegate):

    def __init__(self, user=None, sudo_args=None):
        super().__init__(temporary_file_root=".")
        
        if sudo_args is None:
            sudo_args = []
        self._sudo_args = sudo_args
        self._user = user

        if self._user is None:
            self._sudo_user_args = []
        else:
            self._sudo_user_args = ['-u', self._user]


    def _run_function_in_external_process(self):
        command = ["sudo"] + self._sudo_args + self._sudo_user_args + self._command
        self._invoke_shell(command)


class SSHDelegate(SubprocessDelegate):

    def __init__(self, user, host):
        raise NotImplemented("Well, it's implemented but totally unrun and untested")
        super().__init__(temporary_file_root=".")
        self._user = user
        self._host = host

    def _run_function_in_external_process(self):
        command = ["ssh", f"{self._user}@{self._host}"] + self._command
        self._invoke_shell(command)



class SlurmDelegate(SubprocessDelegate):
    def __init__(self):
        super().__init__(temporary_file_root=".")

    def _run_function_in_external_process(self):
        command = ['salloc', 'srun'] + self._command
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
    r = delegate_object._delegated_invoke()
    pickle.dump(dict(delegate=delegate_object, return_value=r), delegate_after)

        
class TestClass():

    def __init__(self):
        self._value = 0
        
    def hello(self):
        print(f"hello world.  I'm in process {os.getpid()}")
        return os.getpid()

    def set_value(self, v):
        self._value = v
