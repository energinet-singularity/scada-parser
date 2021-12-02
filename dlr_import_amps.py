from time import sleep
import csv
import json
import os
import sys
import requests
from datetime import datetime
from json import dumps
from kafka import KafkaProducer

IP = os.environ['KAFKA_IP']
topic_name = os.environ['KAFKA_TOPIC']
ksql_host = os.environ.get('KSQL_HOST', "kafka-cp-ksql-server")
ksql_stream = os.environ.get('KSQL_STREAM')
ksql_table = os.environ.get('KSQL_TABLE')

#--- Variables and initialization
file_path = '/data/test_out.IMP'
json_data = json.loads('[]')
csv_from_oag_time = 0
cycle = 5
show_debug = True
show_data = True

ksql_config = {
    "config":[
        {"TYPE": "STREAM", "NAME": f"{ksql_stream}", "CONFIG": f"(MRID VARCHAR, VALUE DOUBLE, QUALITY INTEGER, TIME VARCHAR) WITH (KAFKA_TOPIC='{topic_name}', VALUE_FORMAT='JSON')"},
        {"TYPE": "TABLE", "NAME": f"{ksql_table}", "CONFIG": "AS SELECT MRID, LATEST_BY_OFFSET(VALUE) AS VALUE_LATEST, LATEST_BY_OFFSET(QUALITY) AS QUALITY_LATEST, LATEST_BY_OFFSET(TIME) AS TIME_LATEST FROM DLR_AMPS GROUP BY MRID EMIT CHANGES"}
    ]
}

#-- Function
def setup_ksql(ksql_host: str, ksql_config: json):
    #-- Verifying connection
    print(f"Validating kSQLdb setup on host '{ksql_host}'..")
    
    try:
        response = requests.get(f"http://{ksql_host}/info")
    except Exception:
        print(f"Rest API on 'http://{ksql_host}/info' did not respond as expected. Make sure environment variable 'KSQL_HOST' is correct.")
        return False
    
    if response.status_code == 200:
        print('Host responded in an orderly fashion..')
    else:
        print(f"Rest API on 'http://{ksql_host}/info' did not respond as expected. Make sure environment variable 'KSQL_HOST' is correct.")
        return False

    #Verifying streams and tables
    response = requests.post(f"http://{ksql_host}/ksql",json={"ksql": f"LIST STREAMS; LIST TABLES;", "streamsProperties": {}})
    if response.status_code == 200:
        #Create dict with list of known streams and tables
        ksql_existing_config = {"STREAM": [item['name'] for reply in response.json() if reply['@type'] == 'streams' for item in reply['streams']], "TABLE": [item['name'] for reply in response.json() if reply['@type'] == 'tables' for item in reply['tables']]}
        for ksql_item in ksql_config['config']:
            #Check if the item is in the lists returned by kSQL
            if ksql_item['NAME'] in ksql_existing_config[ksql_item['TYPE']]:
                #Found - log it, but do nothing
                print(f'{ksql_item["TYPE"].capitalize()} \'{ksql_item["NAME"]}\' was found.')
            else:
                #Not found - try creating it
                response = requests.post(f"http://{ksql_host}/ksql",json={"ksql": f"CREATE {ksql_item['TYPE']} {ksql_item['NAME']} {ksql_item['CONFIG']};", "streamsProperties": {}})
                if response.status_code == 200 and response.json().pop()['commandStatus']['status'] == 'SUCCESS':
                    print(f'{ksql_item["TYPE"].capitalize()} \'{ksql_item["NAME"]}\' created.')
                else:
                    print(f'Problem while trying to create {ksql_item["TYPE"].lower()}  \'{ksql_item["NAME"]}\'.')
                    return False
    else:
        print('Error while gettings streams and tables from kSQL.')    
        return False
    
    print('kSQL setup has been validated.')
    return True

# Function call
if setup_ksql(ksql_host, ksql_config):
    print("kSQL setup validated/created.")
else:
    print("kSQL setup could not be validated/created.")

#-- Main function
try:
    producer = KafkaProducer(bootstrap_servers=[IP],
                            value_serializer=lambda x: 
                            x.encode('utf-8'))
except Exception:
    print("Connection to kafka have failed. Please check enviroment variable 'IP' and recreate the container")
    sys.exit(1)

while True:
    sleep(cycle)
    if show_debug: print('Container running')
    #-- Check for if the given filepath exist
    if not os.path.isfile(file_path):
        print('File is missing')
        continue
    #-- Start importing data if the file have a new timestamp
    if os.stat(file_path).st_mtime > csv_from_oag_time:
        if show_debug: print('Import starting')

        #-- Update timestamp on file
        csv_from_oag_time = os.stat(file_path).st_mtime
        if show_debug: print(datetime.fromtimestamp(csv_from_oag_time))
        
        #-- Get the new data
        csv_file_time = os.stat(file_path).st_mtime
        csv_file = open(file_path, "r")
        input_data = csv_file.read().splitlines()
        csv_file.close()

        #-- Shaping data
        for csv_line in input_data:
            obj_values = [x.strip() for x in csv_line.split(",")]
            json_data.append({"MRID":obj_values[0],"Value":float(obj_values[1]), 
            "Quality":int(obj_values[2]), "Time":datetime.fromtimestamp(csv_file_time).strftime('%Y-%m-%d %H:%M:%S')})

        #-- Debug/data information if needed
        if show_data: print(json.dumps(json_data,indent=4))
        if show_debug: print(type(json_data))

        #-- Sending data to the given topic name the container was created with
        for i in json_data:
            producer.send(topic_name, value=json.dumps(i))
        if show_debug: print('Import succesfull')
        #-- clearing the cache of output data
        json_data = json.loads('[]')
