#!/bin/bash


curl --location --request POST 'localhost:5010/agent' -H 'Content-Type: application/json' -d @startAgent.json
