#!/usr/bin/env bash

DS_DATABASE_URL=postgresql://dsnet:dsnet@postgres/dsnet uvicorn dsnetserver.main:app