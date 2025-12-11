#!/bin/bash

# Activates the user Python Virtual Environment
if [[ ! $VIRTUAL_ENV ]]; then
    if [[ -f "$HOME/.env/bin/activate" ]]; then
        source $HOME/.env/bin/activate 1>/dev/null 2>&1
    fi
fi

# Run the GUI
python3 ~/DRC/DRC-GUI.py

