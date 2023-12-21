#!/bin/bash


# Set up virtual environment and activate it
python3 -m venv venv
source venv/bin/activate

# Install required dependencies
pip install -r requirements.txt

# Set Flask app environment variables
export FLASK_APP=run.py
# Run Flask app
flask run
