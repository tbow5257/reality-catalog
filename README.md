Future Reality Catalog Application
=============

###Built with Flask backend and Sqlite3 database

####Running the project:

1. Setup the database first by running `database_setup.py` located in the root folder.
2. Add the pre-written database entries by running `preload_data.py` 
3. Begin the web server by running `catalog.py`
4. Using a web browser of your choice, navigate to `localhost:8000` to see the website

####Using JSON Endpoints

JSON endpoints are available for all DB objects, including groups.

Simply define whether AR or VR, then Experience or Headset to receive a list:
`localhost:8000/VR/experience/JSON/`
`localhost:8000/AR/headset/JSON/`

For individual items, use the ID number followed by `/JSON/`
`localhost:8000/VR/experience/3/JSON`
`localhost:8000/AR/headset/2/JSON`

