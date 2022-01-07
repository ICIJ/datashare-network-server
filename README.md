# Datashare network server [![CircleCI](https://circleci.com/gh/ICIJ/datashare-network-server/tree/main.svg?style=svg&circle-token=0300188508c6ff4f496775b9fb7697f72102c9e6)](https://circleci.com/gh/ICIJ/datashare-network-server/tree/main)

This is the http server for the protocol described in the EPFL paper:

[DATASHARENETWORK A Decentralized Privacy-Preserving Search Engine for Investigative Journalists](https://arxiv.org/pdf/2005.14645.pdf)

This is a work in progress.
# Requirements
`psycopg2` requires the installation of `python3-dev` ([see psycopg prerequisites here](https://www.psycopg.org/docs/install.html#build-prerequisites))

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

# Developing

We use [pipenv](https://pipenv.pypa.io) to package/develop the server. We will use it to install all dependencies :

```shell
$ make install
```

## Database 

You need to create first the database. You can bootstrap it with : 

```shell
$ psql  -U <admin_user> -h <psql_host> < bootstrap_db.sql
```

Then to run the migrations :

```shell
$ /path/to/alembic upgrade head 
```

## Testing

```shell
$ make test
```