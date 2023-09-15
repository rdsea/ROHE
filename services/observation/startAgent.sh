#!/bin/bash


curl --location --request POST 'localhost:5011/agent' -H 'Content-Type: application/json' -d @startAgent.json
