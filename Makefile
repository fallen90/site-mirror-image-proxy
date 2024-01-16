.PHONY: setup run

setup:
    # Set up the virtual environment
	python3 -m venv venv
    # Activate the virtual environment (replace with appropriate command for your OS)
	. venv/bin/activate && pip install --upgrade pip
    # Install project dependencies
	. venv/bin/activate && pip install -r requirements.txt

run:
    # Run the Flask application
	. venv/bin/activate && flask --app app.py --debug run