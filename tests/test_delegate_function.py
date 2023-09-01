from delegate_function import *
import pytest

def TestTrivialDelegate(**kwargs):
    def r(subdelegate=None, **morekwargs):
        return TrivialDelegate(subdelegate=subdelegate, **kwargs,
                                **morekwargs)
    r.__name__ = "TestTrivialDelegateFactory"
    return r

def TestSubProcessDelegate(**kwargs):
    def r(subdelegate=None, **morekwargs):
        return SubprocessDelegate(subdelegate=subdelegate, 
                                  delegate_executable_path="/opt/conda/bin/delegate-function-run",
                                  **kwargs, **morekwargs)
    r.__name__ = "TestSubProcessDelegateFactory"
    return r

def TestDockerDelegate(**kwargs):
    def r(subdelegate=None, **morekwargs):
        return DockerDelegate("cfiddle-slurm:21.08.6.1",
                            temporary_file_root='/scratch/',
                            delegate_executable_path="/opt/conda/bin/delegate-function-run",                                                          
                            docker_cmd_line_args=['--entrypoint', '/usr/local/bin/docker-entrypoint.sh', '--mount', f'type=volume,dst=/scratch,source=cse141pp-root_shared_scratch'],
                            subdelegate=subdelegate,
                            **kwargs,
                            **morekwargs
                            )
    r.__name__ = "TestDockerDelegateFactory"
    return r
#GCCToolchain.is_toolchain_available(x)
#from cfiddle.Toolchain.GCC import GCCToolchain

def TestSudoDelegate(**kwargs):
    def r(subdelegate=None, **morekwargs):
        return SudoDelegate(user="cfiddle",
                            delegate_executable_path="/opt/conda/bin/delegate-function-run",
                            subdelegate=subdelegate,
                            **kwargs,
                            **morekwargs
                            )
    r.__name__ = "TestSudoDelegateFactory"
    return r

def TestSlurmDelegate(**kwargs):
    def r(subdelegate=None, **morekwargs):
        return SlurmDelegate(temporary_file_root="/scratch/", 
                            delegate_executable_path="/opt/conda/bin/delegate-function-run",
                            subdelegate=subdelegate,
                            **kwargs,
                            **morekwargs
                            )
    r.__name__ = "TestSlurmDelegateFactory"
    return r

def TestSSHDelegate(**kwargs):
    def r(subdelegate=None, **morekwargs):
        return SSHDelegate("test_fiddler", 
                        "ssh-host", 
                        delegate_executable_path="/opt/conda/bin/delegate-function-run",
                        ssh_options=["-o", "StrictHostKeyChecking=no"],
                        subdelegate=subdelegate,
                            **kwargs,
                            **morekwargs
                            )
    r.__name__ = "TestSSHDelegateFactory"
    return r

chains_to_test = [TestTrivialDelegate(),
                  TestSubProcessDelegate(),#debug_pre_hook=(ShellCommandClass(['bash']), "run", [], {}), interactive=True),
                  TestSlurmDelegate(),#debug_pre_hook=(ShellCommandClass(['bash']), "run", [], {}), interactive=True),
                  # Sudo requires you to intstall delegate_function without -e.
                  TestSudoDelegate(),#debug_pre_hook=(ShellCommandClass(['bash']), "run", [], {}), interactive=True),
                  TestSSHDelegate(),#debug_pre_hook=(ShellCommandClass(['bash']), "run", [], {}), interactive=True),
                  TestDockerDelegate(),#debug_pre_hook=(ShellCommandClass(['bash']), "run", [], {}), interactive=True),
                  DelegateChain(TestTrivialDelegate(),
                                TestTrivialDelegate()),
                  DelegateChain(TestSubProcessDelegate(),
                                TestTrivialDelegate()),
                DelegateChain(TestTrivialDelegate(),
                                TestSubProcessDelegate(),
                                TestTrivialDelegate()),
                DelegateChain(TestSSHDelegate(),#interactive=True),#debug_pre_hook=(ShellCommandClass(['bash']), "run", [], {}), interactive=True),
                                TestDockerDelegate()),#debug_pre_hook=(ShellCommandClass(['bash']), "run", [], {}), interactive=True)),
                DelegateChain(TestSudoDelegate(),
                                TestDockerDelegate()),
                DelegateChain(TestSSHDelegate(), 
                                TestSudoDelegate(),
                                TestDockerDelegate()),
                DelegateChain(TestSudoDelegate(),
                                TestDockerDelegate()),
                DelegateChain(TestSSHDelegate(),
                                TestSudoDelegate()),
                DelegateChain(TestSSHDelegate(),
                                TestSSHDelegate()),
                DelegateChain(TestSSHDelegate(),
                                TestSlurmDelegate()),
                DelegateChain(TestSlurmDelegate(),
                                TestDockerDelegate()),
                DelegateChain(TestSSHDelegate(),
                                TestSudoDelegate(),
                                TestSlurmDelegate(),
                                TestDockerDelegate()
                                ),
                DelegateChain(TestSSHDelegate(),
                                TestSlurmDelegate(),
                                TestSudoDelegate(),
                                TestDockerDelegate()
                                ),
                DelegateChain(TestSSHDelegate(),
                                TestDockerDelegate()
                                ),
                DelegateChain(TestSlurmDelegate(),#interactive=True),#debug_pre_hook=(ShellCommandClass(['bash']), "run", [], {}), interactive=True),
                                TestSlurmDelegate()#debug_pre_hook=(ShellCommandClass(['bash']), "run", [], {}), interactive=True),
                                ),
                DelegateChain(TestSlurmDelegate(),#interactive=True),
                                TestSSHDelegate()#debug_pre_hook=(ShellCommandClass(['bash']), "run", [], {}), interactive=True),
                                ),
                DelegateChain(TestSlurmDelegate(),
                                TestSSHDelegate(),
                                TestSudoDelegate(),
                                TestDockerDelegate()
                                ),
                       ]

@pytest.fixture(scope="module",
                params=chains_to_test,
                ids=map(lambda x: x.pytest_name if hasattr(x,"pytest_name") else str(x.__name__), chains_to_test))
def ADelegate(request):
    return request.param

def test_basic(ADelegate):
    sd = ADelegate()
    f = TestClass()
    r = sd.invoke(f, "hello")

@pytest.mark.slow
def test_shell(ADelegate):
    sd = ADelegate()
    sd.make_interactive()
    f = ShellCommandClass(["bash"])
    sd.invoke(f, "run")

def test_mutable(ADelegate):
    sd = ADelegate()
    f = TestClass()
    sd.invoke(f, "set_value", 4)
    assert f._value == 4

def test_interactive():
    sd = DelegateChain(TestTrivialDelegate(), TestTrivialDelegate())()
    assert not sd._interactive
    assert not sd._subdelegate._interactive
    sd.make_interactive()
    assert sd._interactive
    assert sd._subdelegate._interactive

