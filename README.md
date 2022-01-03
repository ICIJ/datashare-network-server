# datashare network server [![CircleCI](https://circleci.com/gh/ICIJ/datashare-network-server/tree/main.svg?style=svg&circle-token=4114eed623f62c2c3896785aceee50af0457e4ce)](https://circleci.com/gh/ICIJ/datashare-network-server/tree/main)

This is the http server for the protocol described in the EPFL paper:

[DATASHARENETWORK A Decentralized Privacy-Preserving Search Engine for Investigative Journalists](https://arxiv.org/pdf/2005.14645.pdf)

This is a work in progress.

# Running the server locally

```shell
$ make install
$ make run
pipenv run uvicorn dsnetserver.main:app
INFO:     Started server process [9120]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

# developing

We use [pipenv](https://pipenv.pypa.io) to package/develop the server

```shell
$ make install
$ make test
```