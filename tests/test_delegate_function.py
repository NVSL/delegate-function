from delegate_function import *
import os
import pytest
import pwd
import shutil

def TestTrivialDelegate(subdelegate=None):
    return TrivialDelegate(subdelegate=subdelegate)

def TestSubProcessDelegate(subdelegate=None):
    return SubprocessDelegate(subdelegate=subdelegate)

def TestDockerDelegate(subdelegate=None):
    return DockerDelegate("cfiddle-slurm:21.08.6.1",
                          temporary_file_root='/cfiddle_scratch/',
                          delegate_executable_path=shutil.which('delegate-function-run'),
                          subdelegate=subdelegate
                          )

def TestSudoDelegate(subdelegate=None):
    return SudoDelegate(user="cfiddle",
                        delegate_executable_path=shutil.which('delegate-function-run'),
                        subdelegate=subdelegate)

def TestSlurmDelegate(subdelegate=None):
    return SlurmDelegate(temporary_file_root="/cfiddle_scratch/", 
                         delegate_executable_path=shutil.which('delegate-function-run'),
                         subdelegate=subdelegate)

def TestSSHDelegate(subdelegate=None):
    return SSHDelegate("test_fiddler", 
                       platform.node(), 
                       subdelegate=subdelegate)

@pytest.fixture(scope="module",
                params=[TestTrivialDelegate,
                        TestSubProcessDelegate,
                        TestSlurmDelegate,
                        TestSudoDelegate,
                        TestSSHDelegate,
                        DelegateChain(TestTrivialDelegate,
                                      TestTrivialDelegate),
                        DelegateChain(TestSubProcessDelegate,
                                      TestTrivialDelegate),
                        DelegateChain(TestTrivialDelegate,
                                      TestSubProcessDelegate,
                                      TestTrivialDelegate),
                        DelegateChain(TestSSHDelegate,
                                      TestDockerDelegate),
                        DelegateChain(TestSudoDelegate,
                                      TestDockerDelegate),
                        DelegateChain(TestSSHDelegate, 
                                      TestSudoDelegate,
                                      TestDockerDelegate),
                        DelegateChain(TestSudoDelegate,
                                      TestDockerDelegate),
                        DelegateChain(TestSSHDelegate,
                                      TestSudoDelegate),
                        DelegateChain(TestSSHDelegate,
                                      TestSSHDelegate),
                        DelegateChain(TestSSHDelegate,
                                      TestSlurmDelegate),
                        DelegateChain(TestSlurmDelegate,
                                      TestDockerDelegate),
                        DelegateChain(TestSSHDelegate,
                                      TestSudoDelegate,
                                      TestSlurmDelegate,
                                      TestDockerDelegate
                                      ),
                        DelegateChain(TestSSHDelegate,
                                      TestDockerDelegate
                                      ),
                        DelegateChain(TestSlurmDelegate,
                                      TestSlurmDelegate,
                                      ),
#                        DelegateChain(TestSlurmDelegate,
#                                      TestSSHDelegate,
#                                      ),
                       ])
def ADelegate(request):
    return request.param

def test_basic(ADelegate):
    if ADelegate in [TestTrivialDelegate, TestTrivialNestedDelegate]:
        pytest.skip("TrivialDelegate doesn't run in a different process")
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
    sd = TestSSHSudoDockerDelegate()
    assert not sd._interactive
    assert not sd._subdelegate._interactive
    sd.make_interactive()
    assert sd._interactive
    assert sd._subdelegate._interactive

                     
