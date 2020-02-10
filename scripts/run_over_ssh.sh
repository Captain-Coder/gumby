#!/bin/bash

export

ssh root@node$GUMBY_PROCESS_ID  "cd \$PWD; export PATH=$PATH ; launch_scenario.py"
