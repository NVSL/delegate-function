from delegate_function import *
import os
import pytest
import pwd
import shutil

def TestTrivialDelegate(**kwargs):
    def r(subdelegate=None, **morekwargs):
        return TrivialDelegate(subdelegate=subdelegate, **kwargs,
                                **morekwargs)
    r.__name__ = "TestTrivialDelegateFactory"
    return r

def TestSubProcessDelegate(**kwargs):
    def r(subdelegate=None, **morekwargs):
        return SubprocessDelegate(subdelegate=subdelegate, **kwargs, **morekwargs)
    r.__name__ = "TestSubProcessDelegateFactory"
    return r

def TestDockerDelegate(**kwargs):
    def r(subdelegate=None, **morekwargs):
        return DockerDelegate("cfiddle-slurm:21.08.6.1",
                            temporary_file_root='/cfiddle_scratch/',
                            delegate_executable_path=shutil.which('delegate-function-run'),
                            docker_cmd_line_args=['--entrypoint', '/usr/local/bin/docker-entrypoint.sh', '--mount', f'type=volume,dst=/cfiddle_scratch,source=delegate-function_cfiddle_scratch'],
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
                            delegate_executable_path=shutil.which('delegate-function-run'),
                            subdelegate=subdelegate,
                            **kwargs,
                            **morekwargs
                            )
    r.__name__ = "TestSudoDelegateFactory"
    return r

def TestSlurmDelegate(**kwargs):
    def r(subdelegate=None, **morekwargs):
        return SlurmDelegate(temporary_file_root="/cfiddle_scratch/", 
                            delegate_executable_path=shutil.which('delegate-function-run'),
                            subdelegate=subdelegate,
                            **kwargs,
                            **morekwargs
                            )
    r.__name__ = "TestSlurmDelegateFactory"
    return r

def TestSSHDelegate(**kwargs):
    def r(subdelegate=None, **morekwargs):
        return SSHDelegate("test_fiddler", 
                        platform.node(), 
                        subdelegate=subdelegate,
                            **kwargs,
                            **morekwargs
                            )
    r.__name__ = "TestSSHDelegateFactory"
    return r

@pytest.fixture(scope="module",
                params=[TestTrivialDelegate(),
                        TestSubProcessDelegate(),
                        TestSlurmDelegate(),
                        TestSudoDelegate(),
                        TestSSHDelegate(),
                        TestDockerDelegate(),
                        DelegateChain(TestTrivialDelegate(),
                                      TestTrivialDelegate()),
                        DelegateChain(TestSubProcessDelegate(),
                                      TestTrivialDelegate()),
                        DelegateChain(TestTrivialDelegate(),
                                      TestSubProcessDelegate(),
                                      TestTrivialDelegate()),
                        DelegateChain(TestSSHDelegate(),
                                      TestDockerDelegate()),
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
                        DelegateChain(TestSlurmDelegate(),
                                      TestSlurmDelegate(),
                                      ),
#                        DelegateChain(TestSlurmDelegate(),
#                                      TestSSHDelegate(),
#                                      ),
                       ])
def ADelegate(request):
    return request.param

def test_basic(ADelegate):
    sd = ADelegate()
    f = TestClass()
    r = sd.invoke(f, "hello")
#    assert r != os.getpid()

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

                     
