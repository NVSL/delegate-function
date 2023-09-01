from contextlib import contextmanager
import copy
import json
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

import yaml

def is_debug_enabled():
    return os.environ.get("DELEGATE_FUNCTION_DEBUG_ENABLED") == "yes"

if is_debug_enabled():
    print("""
##########################################################################
#  WARNING: You have debugging hooks enabled.  This should not be done   #
#  in production because it allows arbitrary execution of code anywhere  #
#  along the chain of delegates.                                         #
#                                                                        #
#  To disable it, make sure the DELEGATE_FUNCTION_DEBUG_ENABLED          #
#  environment variable is not set.                                      #
##########################################################################
          """)
class BaseDelegate:

    """
    The basic delegate algorithm is:
    
    1.  If I have sub-delegate
        a.  Execute the step of invoking the sub-delegate in my particular way.
    2.  No sub-delegate?
        a.  Then execute the function in my particular way.
    
    As a consequence this means that the only delegate that should ever access or need the original invocation's arguments is the last delegate in the chain.

    :code:`debug_pre_hook` is a tuple with the same format as the arguments to :code:`invoke()`.  
    It'll be run before running the delegated function or invoking the delegate.  Passing 
    :code:`"SHELL"` will get you a shell running in the delegate context.

    For some delegates, you may also need to pass :code:`interactive=True` to interact with the shell.
    """
    def __init__(self, subdelegate=None, debug_pre_hook=None, interactive=False):
        self._subdelegate = subdelegate

        self._debug_pre_hook = debug_pre_hook
        if self._debug_pre_hook == "SHELL":
            self._debug_pre_hook = (ShellCommandClass(['bash']), "run", [], {})
        self._interactive = interactive or self._debug_pre_hook

    def set_subdelegate(self, subdelegate):
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
        self._execute_debug_pre_hook()
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
            if not is_debug_enabled():
                print("Executing debugging hooks is disabled in {self}.  Set 'DELEGATE_FUNCTION_DEBUG_ENABLED=yes' to allow it.  But beware the security consequences.")
                return
            log.debug(f"{self} Invoking debug_pre_hook: {self._debug_pre_hook}")
            obj, meth, argc, kwargs  = self._debug_pre_hook
            getattr(obj, meth)(*argc, **kwargs)
        else:
            log.debug(f"No pre_debug_hook for {self}")

class TrivialDelegate(BaseDelegate):
    pass

def DelegateChain(*argc, **kwargs):
    
    """
    A convenience function for building chains of delegates.

    It returns a factory function that returns delegate objects that you can use to make delegated function invocations.

    :code:`argc` is the list of delegate factories to use to produce the delegate chain.

    :code:`**kwargs` is passed to all the factories.
    """
    def DelegateChainFactory():
        next_delegate = None
        for d_class in reversed(argc):
            if next_delegate and next_delegate._interactive:
                kwargs["interactive"] = True

            next_delegate = d_class(subdelegate=next_delegate, **kwargs)
        return next_delegate
    name = "".join(map(lambda x: x.__name__.replace("Delegate", ""), argc))
    DelegateChainFactory.__name__ = name
    DelegateChainFactory.pytest_name = "_to_".join(map(lambda x:x.__name__, argc))
    return DelegateChainFactory

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

    def __init__(self, *argc, temporary_file_root=None, delegate_executable_path=None, **kwargs): 
        super().__init__(*argc, **kwargs)
        self._temporary_file_root = temporary_file_root
        self._delegate_executable_path = delegate_executable_path 
    
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
                delegate_after.close()
                self._delegate_after_image_name = delegate_after.name
                self._run_function_in_external_process()
                with open(delegate_after.name, "rb") as da:
                    after = pickle.load(da)
                self._obj.__dict__.update(after['delegate']._obj.__dict__)
                return after['return_value']


    def _compute_command_line(self):    
        return [self._find_delegate_function_executable(),
                "--delegate-before", self._delegate_before_image_name,
                "--delegate-after", self._delegate_after_image_name,
                "--log-level", str(log.root.level)]


    def _run_function_in_external_process(self):
        command = self._compute_command_line()
        self._invoke_shell(command)


    def _invoke_shell(self, cmd):
        try:
            os.environ['DELEGATE_FUNCTION_COMMAND'] = " ".join(cmd)
            self._execute_debug_pre_hook()
        finally:
            del os.environ['DELEGATE_FUNCTION_COMMAND']

        try:
            log.debug(f"{type(self).__name__} Executing {' '.join(cmd)=}")
            r = subprocess.run(cmd, check=True)#, capture_output=True)
#            log.debug(f"{r.stdout.decode()}")
#            log.debug(f"{r.stderr.decode()}")
        except subprocess.CalledProcessError as e:
            raise DelegateFunctionException(f"Delegate subprocess execution failed ({type(self).__name__}): {e} {e.stdout and e.stdout.decode()} {e.stderr and e.stderr.decode()}")

    def _execute_debug_pre_hook(self):
        if self._debug_pre_hook:
            print(f"{self} trying to execute '{os.environ['DELEGATE_FUNCTION_COMMAND']}'")
        super()._execute_debug_pre_hook()

    def _find_delegate_function_executable(self):
        if self._delegate_executable_path is not None:
            return self._delegate_executable_path
        exe = shutil.which("delegate-function-run")
        if exe is None:
            raise DelegateFunctionException(f"Delegate {self} on {platform.node()} can't find `delegate-function-run` executable in $PATH.")
        return exe
    

class SudoDelegate(SubprocessDelegate):

    """
    Delegate a function to another user with :code:`sudo`.

    Pitfalls:

    1.  :code:`sudo` removes much of the environment by default.
    2.  The delegate use access control lists to make the files it uses  (and the directories leading to them) readable, writable, and searchable by the target user.
    
    """
    def __init__(self, *args, user=None, sudo_args=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        if sudo_args is None:
            sudo_args = []
        self._sudo_args = sudo_args
        self._user = user

        if self._user is None:
            self._sudo_user_args = []
        else:
            self._sudo_user_args = ['-u', self._user]

    def _compute_command_line(self):
        return ["sudo"] + self._sudo_args + self._sudo_user_args + super()._compute_command_line()

    def _run_function_in_external_process(self):
        self._invoke_shell(['setfacl', '-R', '-m', f'u:{self._user}:rwX', self._temporary_file_root])
        command = self._compute_command_line()
        self._invoke_shell(command)


class SSHDelegate(SubprocessDelegate):
    """
    Pitfalls:

    1.  Ideally, ssh should work without a password.
    2.  It uses :code:`scp` to create a randomly named temporary directory on the remote host in :code:`/tmp` by default.  It attempts to clean up after itself, but there are no guarantees.

    """
    def __init__(self, user, host, *args, ssh_options=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._user = user
        self._host = host
        if ssh_options is None:
            ssh_options = []
        self._ssh_options = ssh_options


    def _run_function_in_external_process(self):
        try:
            self._compute_remote_file_names()
            self._prepare_remote_directory()
            self._copy_delegate_before_image()
            #breakpoint()
            self._invoke_shell(self._compute_command_line())
            self._copy_delegate_after_image()
        finally:
            self._cleanup_remote_directory()


    def _compute_command_line(self):
        return self._compute_ssh_command_line() + [self._find_delegate_function_executable(),
                            "--delegate-before", self._remote_delegate_before_image_name,
                            "--delegate-after", self._remote_delegate_after_image_name,
                            "--log-level", str(log.root.level)]
    

    def _compute_ssh_command_line(self):
        return ["ssh", *self._ssh_options, ("-t" if self._interactive else "-T"), f"{self._user}@{self._host}"]


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

    """
    Pitfalls:

    1.  Slurm requires a shared file system, and the :code:`temporary_file_root` needs to live in that file system.

    """
    def __init__(self, *args, temporary_file_root=None, **kwargs):
        if temporary_file_root is None:
            raise Exception("SlurmDelegate needs 'temporary_file_root' to point to directory in a file system shared between the executing host and Slurm cluster")
        kwargs['temporary_file_root'] = temporary_file_root
        super().__init__(*args, **kwargs)

    def _compute_command_line(self):
        return ['salloc', 'srun', '--export=ALL'] + (["--pty"] if self._interactive else []) + super()._compute_command_line()
    
    def _run_function_in_external_process(self):
        command = self._compute_command_line()
        self._invoke_shell(command)


class DockerDelegate(SubprocessDelegate):

    """
    Pitfalls:

    1.  Docker delegate requires a shared file system.  The :code:`temporary_file_root` needs to be reachable at the same location from outside and inside the docker container.
    2.  `docker_cmd_line_args` is a big security problem. as are any other constructor arguments that control how docker executes.  We probably need a trusted configuration file 
        somewhere that we load to determine how docker should be run.  How do we specify where the config file should live?

    """

    def __init__(self, docker_image, *argc, temporary_file_root=None, docker_cmd_line_args = None, **kwargs):
        if temporary_file_root is None:
            raise Exception("DockerDelegate needs 'temporary_file_root' to point to directory visible at the same location inside and outside the docker container")
        kwargs['temporary_file_root'] = temporary_file_root
        super().__init__(*argc, **kwargs)
        self._docker_image = docker_image

        if docker_cmd_line_args is None:
            docker_cmd_line_args = []

        self._docker_cmd_line_args = docker_cmd_line_args

    def get_docker_cmd_line_args(self):
        return self._docker_cmd_line_args
    
    def _compute_command_line(self):
        self._compute_remote_file_names()
        return ['docker', 'run',
                '--workdir', '/tmp',
                *(["-it"] if self._interactive else []),
                *self.get_docker_cmd_line_args(),
                self._docker_image] +  [self._find_delegate_function_executable(), #"/opt/conda/bin/delegate-function-run",
                "--delegate-before", self._docker_delegate_before_image_name,
                "--delegate-after", self._docker_delegate_after_image_name,
                "--log-level", str(log.root.level)]


    def _run_function_in_external_process(self):
        log.debug(f"{self._temporary_file_root=}")
#        self._root_replacement = root_replacement
#        self._docker_command =         log.debug(f"{self._docker_command + self._command=}")
#        breakpoint()p
        command = self._compute_command_line()
        self._invoke_shell(command)


    def _compute_remote_file_names(self):
#        self._docker_delegate_before_image_name = os.path.join(".", os.path.basename(self._delegate_before_image_name))
#        self._docker_delegate_after_image_name  = os.path.join(".", os.path.basename(self._delegate_after_image_name))
        self._docker_delegate_before_image_name = self._delegate_before_image_name
        self._docker_delegate_after_image_name  = self._delegate_after_image_name
        log.debug(f"{self._docker_delegate_before_image_name=}")        
        log.debug(f"{self._docker_delegate_after_image_name=}")        


class DelegateFunctionException(Exception):
    pass

class DelegateGenerator(BaseDelegate):

    def __init__(self, filename=None, yaml=None):
        if filename is not None and yaml is not None:
            raise Exception("You can't specify both filename and yaml")
        if filename is not None:
            self._load_spec_from_file(filename)
        elif yaml is not None:
            self._load_spec_from_string(yaml)
        else:
            raise Exception("You must specify either filename or yaml")
        
        self._delegates = [self._load_delegate(x) for x in self._spec['sequence']]


        self._wrapped_delegate = DelegateChain(*self._delegates)()

    def set_subdelegate(self, subdelegate):
        self._wrapped_delegate._set_subdelegate(subdelegate)

    def invoke(self, obj, method, *argc, **kwargs):
        self._wrapped_delegate.invoke(obj,method,*argc, **kwargs)
        
    def _do_invoke(self, *argc, **kwargs):
        return self._wrapped_delegate._do_invoke(*argc, **kwargs)

    def _delegated_invoke(self, *argc, **kwargs):
        return self._wrapped_delegate._delegated_invoke(*argc, **kwargs)

    def _load_delegate(self, delegate_spec):
        c = eval(delegate_spec['type'])
        def Factory(*argc, **kwargs):
            args = copy.copy(delegate_spec)
            del args['type']
            return c(*argc, **args, **kwargs)
        return Factory
    
    def _load_spec_from_file(self, filename):
        self._spec_file = filename
        with open(filename) as f:
            d = f.read()
            self._load_spec_from_string(d)

    def _load_spec_from_string(self, string):
        self._spec = yaml.load(string, Loader=yaml.Loader)
    

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
        raise DelegateFunctionException(f"Failed to load pickled delegate: {e}")
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
        log.debug(f"ShellComandClass executing {self._args} {self._kwargs}")
        subprocess.run(*self._args, **self._kwargs)

class PDBClass():
    def run(self):
        breakpoint()

def shell_hook():
    """
    Convenience function for passing as :code:`debug_pre_hook` to the constructor of a subclass of :class:`SubProcessDelegate`.   

    It'll give you a shell before the delegate executes each command.
    """
    return (ShellCommandClass(['bash']), "run", [], {})
