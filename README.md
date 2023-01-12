# Delegate Function

Delegate Function is a simple Python package that lets you invoke a
method on an object but have the code run in a different process.

It differs from Python's `multiprocess`  modules in two ways:

1. It allows much more flexibilty in how the delegate process is created and run.
2. It doesn't support shared state between the current process and subprocess.

#1 means that you can, for instance, run the method over `ssh`,
through a batch system like `slurm`, in a different directory, under
`sudo`, etc.

You can also easily compose these methods, so you run a method in a
docker container started on a remote machine via a batch system.

#2 means there are quite a few restrictions in what changes the method
can make.  The implementation is not super-sophisticated, so it
should really only modify the object's state.

# Installation

```
pip install .
```

# How to Use It

Until I write some docs, checkout `tests/test_delegate_function.py`.
