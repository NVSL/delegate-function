from delegate_function import *
import os
import pytest
import pwd
import shutil

def TestTrivialDelegate():
    return TrivialDelegate()

def TestTrivialNestedDelegate():
    return TrivialDelegate(subdelegate=TrivialDelegate(subdelegate=TrivialDelegate()))

def TestSubProcessDelegate():
    return SubprocessDelegate()

def TestSubprocessNestedDelegate():
    return SubprocessDelegate(subdelegate=SubprocessDelegate(subdelegate=SubprocessDelegate()))

def TestMixedNestedDelegate():
    return SubprocessDelegate(subdelegate=TrivialDelegate(subdelegate=SubprocessDelegate()))

def TestAlternateDirectorySubprocessDelegate():
    os.makedirs(".testing", exist_ok=True)
    return SubprocessDelegate(temporary_file_root=".testing")

def TestDockerDelegate(**kwargs):
    return DockerDelegate("cfiddle-slurm:21.08.6.1",
                          temporary_file_root='/cfiddle_scratch/',
                          delegate_executable_path=shutil.which('delegate-function-run'),
                          **kwargs
                          )


def TestSudoDelegate():
    return SudoDelegate(user=pwd.getpwuid(os.getuid()).pw_name)


def TestSlurmDelegate():
    return SlurmDelegate(temporary_file_root="/cfiddle_scratch/")


def TestSSHSlurmDelegate():
    return SSHDelegate("test_fiddler", 
                       platform.node(), 
                       subdelegate=TestSlurmDelegate())

def TestSlurmDockerDelegate():
    return SlurmDelegate(#debug_pre_hook=(ShellCommandClass(['bash']), "run", [], {}), 
                         temporary_file_root="/cfiddle_scratch/",
                         delegate_executable_path=shutil.which('delegate-function-run'),
                         subdelegate=TestDockerDelegate(#debug_pre_hook=(ShellCommandClass(['bash']), "run", [], {}), 
                                                        ))

import platform

def TestSSHDelegate():
    return SSHDelegate("test_fiddler", 
                       platform.node(), 
                       #debug_pre_hook=(ShellCommandClass(['bash']), "run", [], {})
    )

def TestSSHSudoDelegate():
    return SSHDelegate(user="test_fiddler", 
                       host=platform.node(), 
                       subdelegate=SudoDelegate(user="cfiddle", #debug_pre_hook=(ShellCommandClass(['bash']), "run", [], {}),
                                                                               ))

def TestSSHSudoDockerDelegate():
    return SSHDelegate(user="test_fiddler", 
                       host=platform.node(), 
                       subdelegate=SudoDelegate(user="cfiddle", 
                                                subdelegate=TestDockerDelegate(#debug_pre_hook=(ShellCommandClass(['bash']), "run", [], {}),
                                                                               )))

def TestSudoDockerDelegate():
    return SudoDelegate(user="cfiddle", 
                   #     debug_pre_hook=(ShellCommandClass(['bash']), "run", [], {}),
                        subdelegate=TestDockerDelegate(#debug_pre_hook=(ShellCommandClass(['bash']), "run", [], {})
        ))

def TestSSHSudoTrivialDelegate():
    return SSHDelegate(user="test_fiddler", 
                       host=platform.node(), 
                       subdelegate=SudoDelegate(user="cfiddle", 
                                                subdelegate=TrivialDelegate()))

def TestSSHDockerDelegate():
    return SSHDelegate(user="test_fiddler", 
                       host=platform.node(), 
                       #debug_pre_hook=(ShellCommandClass(['bash']), "run", [], {}),
                       #debug_pre_hook=(PDBClass(), "run", [], {}),
                       subdelegate=TestDockerDelegate(
        #debug_pre_hook=(ShellCommandClass(['bash']), "run", [], {}),
        ))

def TestSSHSSHDelegate():
    return SSHDelegate(user="test_fiddler", 
                       host=platform.node(), 
                       #debug_pre_hook=(ShellCommandClass(['bash']), "run", [], {}),
                       #debug_pre_hook=(PDBClass(), "run", [], {}),
                       subdelegate=SSHDelegate(user="test_fiddler",
                                                host=platform.node(),
                                                #debug_pre_hook=(ShellCommandClass(['bash']), "run", [], {}),   
                                                ))

def TestSSHSudoSlurmDockerDelegate():
    return SSHDelegate(user="test_fiddler", 
                       host=platform.node(),
                       subdelegate=SudoDelegate(user="cfiddle", 
                                                sudo_args=["--preserve-env"],
                                                #debug_pre_hook=(ShellCommandClass(['bash']), "run", [], {}),   
                                                subdelegate=TestSlurmDockerDelegate()))



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
                        TestSudoDockerDelegate,
                        TestSSHSudoTrivialDelegate,
                        TestSSHSudoDelegate,
                        TestSSHSSHDelegate,
                        TestSSHSlurmDelegate,
                        TestSlurmDockerDelegate,
                        TestSSHSudoSlurmDockerDelegate
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

                     
