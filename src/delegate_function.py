from contextlib import contextmanager
import shutil
import subprocess
import sys
import click
import tempfile
import logging as log
import pickle
import os
import uuid 
import platform

class BaseDelegate:

    """
    The basic delegate algorithm is:
    
    1.  If I have sub-delegate
        a.  Execute the step of invoking the sub-delegate in my particular way.
    2.  No sub-delegate?
        a.  Then execute the function in my particular way.
    
    As a consequence this means that the only delegate that should ever access or need the original invocation's arguments is the last delegate in the the chain.

    :code:`debug_pre_hook` is a tuple with the same format as the arguments to :code:`invoke()`.  
    It'll be run before running the delegated function or invoking the delegate.  Passing 
    :code:`(ShellCommandClass(['bash']), "run", [], {})` will get you a shell running in the delegate context.  
    
    For some delegates, you may also need to pass :code:`interactive=True` to interact with the shell.
    
    """
    def __init__(self, subdelegate=None, debug_pre_hook=None, interactive=False):
        self._subdelegate = subdelegate
        self._debug_pre_hook = debug_pre_hook
        self._interactive = False
        if interactive:
            self.make_interactive()

    def make_interactive(self):
        self._make_chain_interactive()

    def invoke(self, obj, method, *argc, **kwargs):
        """ 
        The sole public method of this class exceutes :code:`obj.method(*argc, **kwargs)` using the supplied sub-delegates.

        If there is no sub-delegate, it will execute the function directly. 
        """
        self._obj = obj
        self._method = method
        self._argc = argc
        self._kwargs = kwargs
        self._execute_debug_pre_hook()
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

    def _execute_debug_pre_hook(self):

        if self._debug_pre_hook:
            log.debug(f"{self} Invoking debug_pre_hook: {self._debug_pre_hook}")
            obj, meth, argc, kwargs  = self._debug_pre_hook
            getattr(obj, meth)(*argc, **kwargs)
        else:
            log.debug(f"No pre_debug_hook for {self}")

    def _set_interactive(self, interactive):
        self._interactive = interactive

    def _make_chain_interactive(self):
        t = self
        while t is not None:
            t._set_interactive(True)
            t = t._subdelegate

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

        if self._temporary_file_root is None:
            #self._temp_directory_handle = tempfile.TemporaryDirectory() # keep the direcotry alive by holding a reference to it.
            #temporary_file_root = tempfile.TemporaryDirectory().name
            self._temporary_file_root = tempfile.mkdtemp()#tempfile.TemporaryDirectory() # keep the direcotry alive by holding a reference to it.


        with tempfile.NamedTemporaryFile(dir=self._temporary_file_root, suffix=".before.pickle") as delegate_before:
            os.chmod(delegate_before.name, 0o666)
            self._delegate_before_image_name = delegate_before.name
            pickle.dump(self, delegate_before)
            delegate_before.flush()
            with tempfile.NamedTemporaryFile(dir=self._temporary_file_root, suffix=".after.pickle") as delegate_after:
                self._delegate_after_image_name = delegate_after.name
                self._command = self._compute_command_line()
                self._run_function_in_external_process()
                after = pickle.load(delegate_after)

                self._obj.__dict__.update(after['delegate']._obj.__dict__)
                return after['return_value']


    def _compute_command_line(self):
        return [shutil.which("delegate-function-run"),
                            "--delegate-before", self._delegate_before_image_name,
                            "--delegate-after", self._delegate_after_image_name,
                            "--log-level", str(log.root.level)]


    def _execute_shell(self):
      #  breakpoint()
        subprocess.run("bash")


    def _run_function_in_external_process(self):
        self._invoke_shell(self._command)


    def _invoke_shell(self, cmd):
        try:
            log.debug(f"{type(self).__name__} Executing {' '.join(cmd)=}")
            r = subprocess.run(cmd, check=True)#, capture_output=True)
#            log.debug(f"{r.stdout.decode()}")
#            log.debug(f"{r.stderr.decode()}")
        except subprocess.CalledProcessError as e:
            raise DelegateFunctionException(f"Delegate subprocess execution failed ({type(self).__name__}): {e} {e.stdout and e.stdout.decode()} {e.stderr and e.stderr.decode()}")


class SudoDelegate(SubprocessDelegate):

    def __init__(self, *args, user=None, sudo_args=None, **kwargs):
        super().__init__(*args, temporary_file_root=".", **kwargs)
        
        if sudo_args is None:
            sudo_args = []
        self._sudo_args = sudo_args
        self._user = user

        if self._user is None:
            self._sudo_user_args = []
        else:
            self._sudo_user_args = ['-u', self._user]


    def _run_function_in_external_process(self):
        os.chmod(self._delegate_before_image_name, 0o444)
        os.chmod(self._delegate_after_image_name, 0o666)
        command = ["sudo"] + self._sudo_args + self._sudo_user_args + self._command
        self._invoke_shell(command)


class SSHDelegate(SubprocessDelegate):

    def __init__(self, user, host, *args, **kwargs):
        super().__init__(*args, temporary_file_root=".", **kwargs)
        self._user = user
        self._host = host

    def _run_function_in_external_process(self):
        try:
            self._prepare_remote_directory()
            self._copy_delegate_before_image()
            self._invoke_shell(self._compute_ssh_command_line() + self._command)
            self._copy_delegate_after_image()
        finally:
            self._cleanup_remote_directory()


    def _compute_command_line(self):
        self._compute_remote_file_names()
        return [shutil.which("delegate-function-run"),
                            "--delegate-before", self._remote_delegate_before_image_name,
                            "--delegate-after", self._remote_delegate_after_image_name,
                            "--log-level", str(log.root.level)]
    

    def _compute_ssh_command_line(self):
        return ["ssh", ("-t" if self._interactive else "-T"), f"{self._user}@{self._host}"]


    def _copy_delegate_before_image(self):
        command = ['scp', 
                   self._delegate_before_image_name, 
                   f"{self._user}@{self._host}:{self._remote_delegate_before_image_name}"]
        self._invoke_shell(command)
        
    def _copy_delegate_after_image(self):
        command = ['scp', 
                   f"{self._user}@{self._host}:{self._remote_delegate_after_image_name}", 
                   self._delegate_after_image_name]
        self._invoke_shell(command)

    def _compute_remote_file_names(self):
        self._remote_execution_id = str(uuid.uuid4())
        self._remote_temporary_directory = os.path.join("/tmp", self._remote_execution_id)
        self._remote_delegate_before_image_name = os.path.join(self._remote_temporary_directory, os.path.basename(self._delegate_before_image_name))
        self._remote_delegate_after_image_name  = os.path.join(self._remote_temporary_directory, os.path.basename(self._delegate_after_image_name))
        
    def _prepare_remote_directory(self):
        self._invoke_shell(self._compute_ssh_command_line() + ["mkdir","-p", self._remote_temporary_directory])

    def _cleanup_remote_directory(self):
        self._invoke_shell(self._compute_ssh_command_line() + ["rm","-rf", self._remote_temporary_directory])


class SlurmDelegate(SubprocessDelegate):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, temporary_file_root=".", **kwargs)

    def _run_function_in_external_process(self):
        breakpoint()
        command = ['salloc', 'srun'] + (["--pty"] if self._interactive else []) + self._command
        self._invoke_shell(command)


class DockerDelegate(SubprocessDelegate):

    def __init__(self, docker_image, *argc, **kwargs):
        super().__init__(*argc, **kwargs)
        self._docker_image = docker_image

    def _run_function_in_external_process(self):
        log.debug(f"{self._temporary_file_root=}")
#        self._root_replacement = root_replacement
        self._docker_command = ['docker', 'run',
                                '--workdir', '/tmp',
                                *(["-it"] if self._interactive else []),
                                '--entrypoint', '/usr/local/bin/docker-entrypoint.sh',                                
                                #'--mount', f'type=bind,source={self._replace_root(os.getcwd())},dst={os.getcwd()}',
                                #'--mount', f'type=bind,dst=/tmp,source={os.path.abspath(self._temporary_file_root)}',
                                '--mount', f'type=volume,dst=/cfiddle_scratch,source=cfiddle-slurm_cfiddle_scratch',
                                self._docker_image ]
        log.debug(f"{self._docker_command + self._command=}")
#        breakpoint()
        self._invoke_shell(self._docker_command + self._command)


    def _compute_command_line(self):
        self._compute_remote_file_names()
        return ["/opt/conda/bin/delegate-function-run",
#            shutil.which("delegate-function-run"),
                            "--delegate-before", self._docker_delegate_before_image_name,
                            "--delegate-after", self._docker_delegate_after_image_name,
                            "--log-level", str(log.root.level)]


    def _compute_remote_file_names(self):
#        self._docker_delegate_before_image_name = os.path.join(".", os.path.basename(self._delegate_before_image_name))
#        self._docker_delegate_after_image_name  = os.path.join(".", os.path.basename(self._delegate_after_image_name))
        self._docker_delegate_before_image_name = self._delegate_before_image_name
        self._docker_delegate_after_image_name  = self._delegate_after_image_name
        log.debug(f"{self._docker_delegate_before_image_name=}")        
        log.debug(f"{self._docker_delegate_after_image_name=}")        

class DelegateFunctionException(Exception):
    pass

@click.command()
@click.option('--delegate-before', required=True, help="File with the initial state of the delegate.")
@click.option('--delegate-after', required=True, help="File with delegate state after execution")
@click.option('--log-level', default=None, type=int, help="Verbosity level for logging.")
def delegate_function_run(delegate_before, delegate_after, log_level):
    import platform
    log.basicConfig(format='%(asctime)s %(levelname)s %(module)s - %(funcName)s: %(message)s')
#                    datefmt="%Y-%m-%d %H:%M:%S.%f")

    if log_level is not None:
        log.root.setLevel(log_level)

    log.info(f"Executing in delegate process on {platform.node()}")
    try:
        with open(delegate_before, "rb") as delegate_before_stream:
            with open(delegate_after, "wb") as delegate_after_stream:
                do_delegate_function_run(delegate_before_stream, delegate_after_stream)
    except DelegateFunctionException as e:
        log.error(e)
        sys.exit(1)
    except PermissionError as e:
        raise
        breakpoint()
        log.error(e)
        sys.exit(1)
     
def do_delegate_function_run(delegate_before, delegate_after):
    try:
        delegate_object = pickle.load(delegate_before)
    except Exception as e:
        raise DelegateFunctionException(f"Failed to load picked delegate: {e}")
    r = delegate_object._delegated_invoke()
    pickle.dump(dict(delegate=delegate_object, return_value=r), delegate_after)
#    os.chmod(delegate_after, 0o444)
#    breakpoint()


# These are for testing.  They are here because the need to install on the remote side, 
# and the classes in test_*.py don't get installed over there.
class TestClass():

    def __init__(self):
        self._value = 0
        
    def hello(self):
        print(f"hello world.  I'm in process {os.getpid()} running on {platform.node()}")
        return os.getpid()

    def set_value(self, v):
        self._value = v

class ShellCommandClass():
    def __init__(self, *args, **kwargs):
        self._args = args
        self._kwargs = kwargs

    def run(self):    
        subprocess.run(*self._args, **self._kwargs)

class PDBClass():
    def run(self):
        breakpoint()