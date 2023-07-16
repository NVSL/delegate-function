from delegate_function import *
import os
import pytest
import pwd

def TestTrivialDelegate(**kwargs):
    return TrivialDelegate()

def TestTrivialNestedDelegate(**kwargs):
    return TrivialDelegate(subdelegate=TrivialDelegate(subdelegate=TrivialDelegate()))

def TestSubProcessDelegate(**kwargs):
    return SubprocessDelegate()

def TestSubprocessNestedDelegate(**kwargs):
    return SubprocessDelegate(subdelegate=SubprocessDelegate(subdelegate=SubprocessDelegate()))

def TestMixedNestedDelegate(**kwargs):
    return SubprocessDelegate(subdelegate=TrivialDelegate(subdelegate=SubprocessDelegate()))

def TestAlternateDirectorySubprocessDelegate(**kwargs):
    os.makedirs(".testing", exist_ok=True)
    return SubprocessDelegate(temporary_file_root=".testing")

def TestDockerDelegate(**kwargs):
    return DockerDelegate("cfiddle-slurm:21.08.6.1",
                          #("/cse142L","/home/swanson/CSE141pp-Root"),
                          temporary_file_root='/cfiddle_scratch/',
                          **kwargs
                          )

def TestSudoDelegate(**kwargs):
    return SudoDelegate(user=pwd.getpwuid(os.getuid()).pw_name)

def TestSlurmDelegate(**kwargs):
    return SlurmDelegate()

import platform

def TestSSHDelegate(**kwargs):
    return SSHDelegate("test_fiddler", 
                       platform.node(), 
                       interactive = kwargs.get("interactive", False),
                       subdelegate=TrivialDelegate(subdelegate=TrivialDelegate()))

def TestSSHSudoDockerDelegate(**kwargs):
    return SSHDelegate(user="test_fiddler", 
                       host=platform.node(), 
                       interactive = kwargs.get("interactive", False),
                       subdelegate=SudoDelegate(user="cfiddle", 
                                                subdelegate=TestDockerDelegate(#debug_pre_hook=(ShellCommandClass(['bash']), "run", [], {}), 
                                                                               **kwargs)))

def TestSSHDockerDelegate(**kwargs):
    return SSHDelegate(user="test_fiddler", 
                       host=platform.node(), 
                       interactive = kwargs.get("interactive", False),
                       #debug_pre_hook=(ShellCommandClass(['bash']), "run", [], {}),
                       #debug_pre_hook=(PDBClass(), "run", [], {}),
                       subdelegate=TestDockerDelegate(
        #debug_pre_hook=(ShellCommandClass(['bash']), "run", [], {}), 
        **kwargs))

def TestSSHSSHDelegate(**kwargs):
    return SSHDelegate(user="test_fiddler", 
                       host=platform.node(), 
                       interactive = kwargs.get("interactive", False),
                       debug_pre_hook=(ShellCommandClass(['bash']), "run", [], {}),
                       #debug_pre_hook=(PDBClass(), "run", [], {}),
                       subdelegate=SSHDelegate(user="test_fiddler",
                                                host=platform.node(),
                                                debug_pre_hook=(ShellCommandClass(['bash']), "run", [], {}),   
                                                **kwargs))


@pytest.fixture(scope="module",
                params=[TestTrivialDelegate,
                        TestSubProcessDelegate,
                        TestTrivialNestedDelegate,
                        TestSubprocessNestedDelegate,
                        TestMixedNestedDelegate,
                        TestAlternateDirectorySubprocessDelegate,
                        TestSlurmDelegate,
                        TestDockerDelegate,
                        TestSudoDelegate,
                        TestSSHDelegate,
                        TestSSHDockerDelegate,        
                        TestSSHSudoDockerDelegate,
                        TestSSHSSHDelegate      
                        ])
def ADelegate(request):
    return request.param

def test_basic(ADelegate):
    if ADelegate in [TestTrivialDelegate, TestTrivialNestedDelegate]:
        pytest.skip("TrivialDelegate doesn't run in a different process")
    sd = ADelegate()
    f = TestClass()
    r = sd.invoke(f, "hello")
    assert r != os.getpid()

@pytest.mark.slow
def test_shell(ADelegate):
    sd = ADelegate(interactive=True)
    f = ShellCommandClass(["bash"])
    sd.invoke(f, "run")



def test_mutable(ADelegate):
    sd = ADelegate()
    f = TestClass()
    sd.invoke(f, "set_value", 4)
    assert f._value == 4

    
