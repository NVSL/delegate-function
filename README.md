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
can make.  It also means it's not useful for things like parallel
execution.

# Motivation

This package grew out a very specific use case:  A user would write some untrusted code that needed to be run on the user's behalf in a
sandboxed environment.  The challenge was that the path to accessing the sandboxed environment was somewhat complex.  For instance, it might involve:

1.  Connecting to a remote machine via `ssh`
2.  Then using `sudo` to run a priviliged script that would...
3.  Submit a job to a batch runnning service (e.g., Slurm) that would...
4.  Create a sandboxed docker container that would...
5.  Run the user's code.

To handle thing, I built the notion of "delegate" objects that could be chained together.  There are delegates `ssh`, `docker`, `sudo`, and `slurm`, and implementing new ones is reasonably easy.
They can be "stacked" arbitrarily. 

# Limitations

The implementation is not super-sophisticated, so it
should really only modify the object's state.  

In particular, changes to files will not be preserved.  However, Python's `io.StringIO` and `io.BytesIO` objects are both picklable, 
which allows for some neat tricks.  For instance, you can create a zip archive in an `io.BytesIO` object, unpack it on the other side, 
run your code, and zip up the results. 


# Installation

```
pip install .
```

# How to Use It

Until I write some docs, checkout `tests/test_delegate_function.py`.

# Running The Tests

Testing everything is quite involved because it needs a slurm cluster that you can access, a couple of test accounts, and a ssh host.

A dockerized version of all of that is in `testing-setup`.

I assume you are developing from inside docker:

To get things going:

1. Create a docker volume called `shared_scratch` and mount it on your dev container at `/scratch`  make sure `/scratch` is readable/writeable by everyone.
2. `cd testing-setup; docker-compose build`
3. Run `testing-setup/setup_test.sh`.  This will create some users, and make it possible for your dev container to submit slurm jobs.
4. `cd testing-setup; SCRATCH=cse141pp-root_shared_scratch DEV_NETWORK=cse141pp-root_default docker-compose up --detach` -- 'DEV_NETWORK` should be network the slurm containers should connect to.  It should be accessible from your dev container.
5. `cd tests; pytest`

If the SSH tests fail due to host key issues, you can try running `testing-setup/fix_sh.sh`.
