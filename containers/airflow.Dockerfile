FROM apache/airflow:2.10.2

ADD requirements/local.txt .
RUN pip install --no-cache-dir "apache-airflow==2.10.2" -r local.txt
# RUN pip install -r local.txt