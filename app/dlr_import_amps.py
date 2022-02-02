import os
import sys
import csv
import time
import json
import logging
import requests
from json import dumps
from datetime import datetime
from kafka import KafkaProducer

# Initialize log
log = logging.getLogger(__name__)

try:
    IP = os.environ.get('KAFKA_IP')
except KeyError:
    log.warning('Input on KAFKA_IP is not set')
    sys.exit(1)

try:
    ksql_host = os.environ.get('KSQL_HOST')
except KeyError:
    log.warning('Input on KSQL_HOST is not set')
    sys.exit(1)

try:
    ksql_table = os.environ.get('KSQL_TABLE')
except KeyError:
    log.warning('Input on KSQL_TABLE is not set')
    sys.exit(1)

try:
    topic_name = os.environ.get('KAFKA_TOPIC')
except KeyError:
    log.warning('Input on KAFKA_TOPIC is not set')
    sys.exit(1)

try:
    ksql_stream = os.environ.get('KSQL_STREAM')
except KeyError:
    log.warning('Input on KSQL_STREAM is not set')
    sys.exit(1)


# Function
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
    response = requests.post(f"http://{ksql_host}/ksql",json={"ksql": f"LIST STREAMS; LIST TABLES;", "streamsProperties": {}})
    if response.status_code == 200:
        # Create dict with list of known streams and tables
        ksql_existing_config = {"STREAM": [item['name'] for reply in response.json() if reply['@type'] == 'streams' for item in reply['streams']], "TABLE": [item['name'] for reply in response.json() if reply['@type'] == 'tables' for item in reply['tables']]}
        for ksql_item in ksql_config['config']:
            # Check if the item is in the lists returned by kSQL
            if ksql_item['NAME'] in ksql_existing_config[ksql_item['TYPE']]:
                # Found - log it, but do nothing
                log.info(f'{ksql_item["TYPE"].capitalize()} \'{ksql_item["NAME"]}\' was found.')
            else:
                # Not found - try creating it
                response = requests.post(f"http://{ksql_host}/ksql",json={"ksql": f"CREATE {ksql_item['TYPE']} {ksql_item['NAME']} {ksql_item['CONFIG']};", "streamsProperties": {}})
                if response.status_code == 200 and response.json().pop()['commandStatus']['status'] == 'SUCCESS':
                    log.info(f'{ksql_item["TYPE"].capitalize()} \'{ksql_item["NAME"]}\' created.')
                else:
                    log.error(f'Problem while trying to create {ksql_item["TYPE"].lower()}  \'{ksql_item["NAME"]}\'.')
                    return False
    else:
        log.error('Error while gettings streams and tables from kSQL.')
        return False
    
    log.info('kSQL setup validated/created.')
    return True



# Main loop
if __name__ == "__main__":

    # Setup logging for client output (__main__ should output INFO-level, everything else stays at WARNING)
    logging.basicConfig(format="%(levelname)s:%(asctime)s:%(name)s - %(message)s")
    logging.getLogger(__name__).setLevel(logging.INFO)

    # Variables and initialization
    file_path = '/data/DLR_kafka_out.IMP'
    json_data = json.loads('[]')
    csv_from_oag_time = 0
    cycle = 5

    ksql_config = {
        "config":[
            {"TYPE": "STREAM", "NAME": f"{ksql_stream}", "CONFIG": f"(MRID VARCHAR, VALUE DOUBLE, QUALITY INTEGER, TIME VARCHAR) WITH (KAFKA_TOPIC='{topic_name}', VALUE_FORMAT='JSON')"},
            {"TYPE": "TABLE", "NAME": f"{ksql_table}", "CONFIG": "AS SELECT MRID, LATEST_BY_OFFSET(VALUE) AS VALUE_LATEST, LATEST_BY_OFFSET(QUALITY) AS QUALITY_LATEST, LATEST_BY_OFFSET(TIME) AS TIME_LATEST FROM DLR_AMPS GROUP BY MRID EMIT CHANGES"}
        ]
    }

    # Trying kafka connection on first startup
    try:
        producer = KafkaProducer(bootstrap_servers=[IP],
                                value_serializer=lambda x: 
                                x.encode('utf-8'))
    except Exception:
        log.error("Connection to kafka have failed. Please check enviroment variable 'ip' and if needed recreate the container")
        sys.exit(1)

    while True:
        time.sleep(cycle)
        start = time.time()

        # Starting with checking that the ksql streams and tables needed for the DLR algorithm exist
        if not setup_ksql(ksql_host, ksql_config):
            continue
        
        log.info('Container running')

        # Check for if the given filepath exist
        if not os.path.isfile(file_path):
            log.error('File is missing')
            continue

        # Start importing data if the file have a new timestamp
        if os.stat(file_path).st_mtime > csv_from_oag_time:
            log.info('Import starting')

            # Update timestamp from file
            csv_from_oag_time = os.stat(file_path).st_mtime
            log.info(datetime.fromtimestamp(csv_from_oag_time))
            
            # Reading and shaping data
            with open(file_path, 'r', newline = '') as f:
                reader = csv.reader(f, delimiter = ',')
                for row in reader:
                    json_data.append({
                        "MRID":row[0],
                        "Value":float(row[1]), 
                        "Quality":int(row[2]), 
                        "Time":datetime.fromtimestamp(csv_from_oag_time).strftime('%Y-%m-%d %H:%M:%S')
                    })

            # Debug/data information if needed
            log.info(json.dumps(json_data,indent=4))

            # Sending data to the given topic name the container was created with
            for i in json_data:
                producer.send(topic_name, value=json.dumps(i))
            log.info('Import succesfull')

            # Clearing the cache of output data
            json_data = json.loads('[]')
            end = time.time()
            log.info(f'Runtime of the program is {end - start}')
