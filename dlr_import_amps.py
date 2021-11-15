from time import sleep
import csv
import json
import os
from datetime import datetime
from json import dumps
from kafka import KafkaProducer

IP = os.environ['KAFKA_IP']

producer = KafkaProducer(bootstrap_servers=[IP],
                         value_serializer=lambda x: 
                         x.encode('utf-8'))

#--- Variables and initialization
#file_path = '/home/thomas/Desktop/workspace/data/test_out.IMP'
file_path = '/data/test_out.IMP'
json_data = json.loads('[]')
csv_from_oag_time = 0
cycle = 5
show_debug = True
show_data = True
topic_name = 'dlr_scada_amps_2'
#dlr_scada_amps er den rene data topic uden modifikation

while True:
    sleep(cycle)
    if show_debug: print('Container running')
    if os.stat(file_path).st_mtime > csv_from_oag_time:
        if show_debug: print('Import starting')

        #-- Check for if the given filepath exist
        if not os.path.isfile(file_path):
            print('File is missing')
            continue

        #-- Updatere timestamp på filen
        csv_from_oag_time = os.stat(file_path).st_mtime
        if show_debug: print(datetime.fromtimestamp(csv_from_oag_time))
        
        #-- Får nye datasæt
        csv_file_time = os.stat(file_path).st_mtime
        csv_file = open(file_path, "r")
        input_data = csv_file.read().splitlines()
        csv_file.close()

        #-- Opsplitning af datasættet
        for csv_line in input_data:
            obj_values = [x.strip() for x in csv_line.split(",")]
            json_data.append({"MRID":obj_values[0],"Value":float(obj_values[1]), 
            "Quality":int(obj_values[2]), "Time":datetime.fromtimestamp(csv_file_time).strftime('%Y-%m-%d %H:%M:%S')})

        #-- Print af datasæt til visualisering
        if show_data: print(json.dumps(json_data,indent=4))
        if show_debug: print(type(json_data))

        #-- Sender datasæts til kafka topic
        for i in json_data:
            producer.send(topic_name, value=json.dumps(i))
        if show_debug: print('Import succesfull')
        json_data = json.loads('[]')
