# Spectral PyMG

## Installation

Python version: 3.12

On linux:
1. Install python3.12
```bash
    sudo apt-get install python3.12
```
2. Install virtualenvwrapper
```bash
    sudo apt-get install virtualenvwrapper
```
3. Add these lines to your .bashrc file
```bash
    export WORKON_HOME=$HOME/.virtualenvs
    export VIRTUALENVWRAPPER_PYTHON=/usr/bin/python3.12
    export VIRTUALENVWRAPPER_VIRTUALENV=~/.local/bin/virtualenv
    source /usr/local/bin/virtualenvwrapper.sh
```
4. Clone the spectral-pymg repository to your local machine. You can use the following command:
```bash
    git clone https://github.com/varrascaeta/spectral-pymg.git
```
5. Navigate to the directory where you cloned the repository:
```bash
    cd spectral-pymg
```
6. Create a virtual environment for your project. Open a terminal and navigate to the directory where you want to create the virtual environment. Then run the following command:
```bash
    mkvirtualenv -a . spectral --python=python3.12 
```

This will create a new virtual environment named 'spectral'.

7. Activate the virtual environment:
```bash
    workon spectral
```
8. Install the required dependencies.
```bash
    pip install -r requirements/local.txt
```
9. Install docker-compose
```bash
    sudo apt-get install docker-compose
```
10. Run the following command to start the database and the admin:
```bash
    docker-compose -f containers/app/docker-compose.yml up
```
Or, if you want to run only the database:
```bash
    docker-compose -f containers/app/docker-compose.yml up spectral-docker-db
```
11. Init the database
```bash
   python service/manage.py migrate
   python service/manage.py createsuperuser
```
12. Now you can access the admin at localhost:8000/admin
13. If you want to rebuild, it is only necessary to rebuild the app. DO NOT delete the volume, otherwise you will lose all the data. To rebuild the app image, run the following command:
```bash
    docker-compose -f containers/app/docker-compose.yml up --build --no-deps spectral
```
