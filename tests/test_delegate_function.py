from delegate_function import *
import os
import pytest
import pwd
def TrivialNestedDelegate():
    return TrivialDelegate(subdelegate=TrivialDelegate(subdelegate=TrivialDelegate()))

def SubprocessNestedDelegate():
    return SubprocessDelegate(subdelegate=SubprocessDelegate(subdelegate=SubprocessDelegate()))

def MixedNestedDelegate():
    return SubprocessDelegate(subdelegate=TrivialDelegate(subdelegate=SubprocessDelegate()))

def AlternateDirectorySubprocessDelegate():
    os.makedirs(".testing", exist_ok=True)
    return SubprocessDelegate(temporary_file_root=".testing")

def TestDockerDelegate():
    return DockerDelegate("cfiddle-slurm:21.08.6.1",
                          ("/cse142L","/home/swanson/CSE141pp-Root"))

def SudoTestDelegate():
    return SudoDelegate(pwd.getpwuid(os.getuid()).pw_name)

def SSHTestDelegate():
    return SSHDelegate(pwd.getpwuid(os.getuid()).pw_name, "some host")

@pytest.fixture(scope="module",
                params=[TrivialDelegate,
                        SubprocessDelegate,
                        TrivialNestedDelegate,
                        SubprocessNestedDelegate,
                        MixedNestedDelegate,
                        AlternateDirectorySubprocessDelegate,
                        SlurmDelegate,
                        TestDockerDelegate,
                        SudoTestDelegate,
                        #SSHTestDelegate,
                        
                        ])
def ADelegate(request):
    return request.param

def test_basic(ADelegate):
    if ADelegate in [TrivialDelegate, TrivialNestedDelegate]:
        pytest.skip("TrivialDelegate doesn't run in a different process")
    sd = ADelegate()
    f = TestClass()
    r = sd.invoke(f, "hello")
    assert r != os.getpid()

def test_mutable(ADelegate):
    sd = ADelegate()
    f = TestClass()
    sd.invoke(f, "set_value", 4)
    assert f._value == 4

    
