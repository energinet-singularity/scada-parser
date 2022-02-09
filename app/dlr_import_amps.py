import os
import sys
import csv
import time
import json
import logging
import requests
from datetime import datetime
from kafka import KafkaProducer

# Initialize log
log = logging.getLogger(__name__)


# Function to setup kSQL output
def setup_ksql(ksql_host: str, ksql_config: json):
    # Verifying connection
    log.info(f"Validating kSQLdb setup on host '{ksql_host}'..")

    try:
        response = requests.get(f"http://{ksql_host}/info")
        if response.status_code != 200:
            raise Exception('Host responded with error.')
    except Exception as e:
        log.exception(e)
        log.exception(f"Rest API on 'http://{ksql_host}/info' did not respond as expected." +
                      " Make sure environment variable 'KSQL_HOST' is correct.")

    # Verifying streams and tables
    response = requests.post(f"http://{ksql_host}/ksql", json={"ksql": f"LIST STREAMS; LIST TABLES;", "streamsProperties": {}})
    if response.status_code == 200:
        # Create dict with list of known streams and tables
        ksql_existing_config = {"STREAM": [item['name'] for reply in response.json() if reply['@type'] == 'streams'
                                for item in reply['streams']], "TABLE": [item['name'] for reply in response.json()
                                if reply['@type'] == 'tables' for item in reply['tables']]}
        for item in ksql_config['config']:
            # Check if the item is in the lists returned by kSQL
            if item['NAME'] in ksql_existing_config[item['TYPE']]:
                # Found - log it, but do nothing
                log.info(f'{item["TYPE"].capitalize()} \'{item["NAME"]}\' was found.')
            else:
                # Not found - try creating it
                response = requests.post(f"http://{ksql_host}/ksql",
                                         json={"ksql": f"CREATE {item['TYPE']} {item['NAME']} {item['CONFIG']};",
                                               "streamsProperties": {}})
                if response.status_code == 200 and response.json().pop()['commandStatus']['status'] == 'SUCCESS':
                    log.info(f'{item["TYPE"].capitalize()} \'{item["NAME"]}\' created.')
                else:
                    log.error(f'Problem while trying to create {item["TYPE"].lower()}  \'{item["NAME"]}\'.')
                    return False
    else:
        log.error('Error while gettings streams and tables from kSQL.')
        return False

    log.info('kSQL setup validated/created.')
    return True


def load_dlr_file(file_path: str) -> dict:
    log.debug(f"Trying to parse file '{file_path}'.")

    # Check if the file exist
    if not os.path.isfile(file_path):
        log.error('File not found')
        return

    # Reading and shaping data
    json_data = json.loads('[]')
    with open(file_path, 'r', newline='') as f:
        reader = csv.reader(f, delimiter=',')
        for row in reader:
            json_data.append({
                "MRID": row[0],
                "Value": float(row[1]),
                "Quality": int(row[2]),
                "Time": datetime.fromtimestamp(os.stat(file_path).st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            })

    return json_data


def get_kafka_setup() -> tuple:
    try:
        kafka_host = os.environ.get('KAFKA_IP')
    except KeyError:
        log.error('KAFKA_IP is required but has not been set')
        sys.exit(1)

    try:
        kafka_topic = os.environ.get('KAFKA_TOPIC')
    except KeyError:
        log.error('KAFKA_TOPIC is required but has not been set')
        sys.exit(1)

    try:
        producer = KafkaProducer(bootstrap_servers=[kafka_host],
                                 value_serializer=lambda x:
                                 x.encode('utf-8'))
    except Exception:
        log.error("Connection to kafka failed. Check enviroment variable 'KAFKA_IP' and restart the container.")
        sys.exit(1)

    return producer, kafka_topic


# Function that will load the ksql config
def get_ksql_setup(kafka_topic: str) -> tuple:
    ksql_host = ""

    try:
        ksql_host = os.environ.get('KSQL_HOST')
        ksql_stream = os.environ.get('KSQL_STREAM')
        ksql_table = os.environ.get('KSQL_TABLE')
    except KeyError:
        log.warning('KSQL configuration missing - skipping kSQL setup.')

    ksql_config = {
        "config": [
            {"TYPE": "STREAM",
             "NAME": f"{ksql_stream}",
             "CONFIG": ("(MRID VARCHAR, VALUE DOUBLE, QUALITY INTEGER, TIME VARCHAR) "
                        f"WITH (KAFKA_TOPIC='{kafka_topic}', VALUE_FORMAT='JSON')")},
            {"TYPE": "TABLE",
             "NAME": f"{ksql_table}",
             "CONFIG": ("AS SELECT MRID, LATEST_BY_OFFSET(VALUE) AS VALUE_LATEST, LATEST_BY_OFFSET(QUALITY) AS QUALITY_LATEST,"
                        f" LATEST_BY_OFFSET(TIME) AS TIME_LATEST FROM '{ksql_stream}' GROUP BY MRID EMIT CHANGES")}
        ]
    }

    return ksql_host, ksql_config


# Initialization for main
if __name__ == "__main__":
    # Setup logging for client output (__main__ should output INFO-level, everything else stays at WARNING)
    logging.basicConfig(format="%(levelname)s:%(asctime)s:%(name)s - %(message)s")
    logging.getLogger(__name__).setLevel(logging.INFO)

    # Load kafka and kSQL configuration
    producer, kafka_topic = get_kafka_setup()
    ksql_host, ksql_config = get_ksql_setup(kafka_topic)

    # Variables and initialization
    file_path = '/data/DLR_kafka_out.IMP'
    csv_from_oag_time = 0
    sleep_time = 5

    while True:
        # Check kSQL each run - hack because kSQL might loose its config
        if ksql_host != "":
            setup_ksql(ksql_host, ksql_config)

        if os.path.isfile(file_path):
            if os.stat(file_path).st_mtime > csv_from_oag_time:
                start = time.time()
                csv_from_oag_time = os.stat(file_path).st_mtime
                json_data = load_dlr_file(file_path)
                log.debug(json.dumps(json_data, indent=4))

                # Send data to Kafka
                for i in json_data:
                    producer.send(kafka_topic, value=json.dumps(i))

                log.debug(f'Runtime was {time.time() - start}')
            else:
                log.debug(f"File at '{file_path}' has not changed.")
        else:
            log.debug(f"No file found at '{file_path}'.")

        time.sleep(sleep_time)
