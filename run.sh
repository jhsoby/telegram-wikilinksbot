#!/bin/bash
python3 -m venv venv2 && source venv2/bin/activate &&
pip3 install --upgrade pip &&
pip3 install -r requirements.txt &&
python3 wikilinksbot.py
