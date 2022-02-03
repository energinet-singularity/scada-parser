# SCADA parser

A container that parses messages from a CSV file to a kafka topic.

## Description

This repository contains a python-script that will produce messages to a kafka broker. The data will be shaped into a specific format needed for the application it is delivering messages for. The script is intended to be run as part of a container/kubernetes, so a Dockerfile is provided as well, as is a set of helm charts.

### Exposed environment variables:

| Name | Description |
|--|--|
|KAFKA_IP|Host-name or IP+Port of the kafka-broker|
|KSQL_HOST|Host-name or IP+Port of the ksql server|
|KSQL_STREAM|Name of the stream created on the kSQL server|
|KSQL_TABLE|Name of the table created on the kSQL server|
|KAFKA_TOPIC|The topic the script will produce messages to on the kafka-broker|

### Kafka messages / Output

As default the system will be configured to shape data for DLR. However it is possible to disable shaping of data and take any list of json, to utilize the generel functionality use environment variable 'shape_data' and set it to 'False'.
If shaping of data is disabled, any message consisting of a list with json formatted structure will work. See below for an example of such a list:

[{"Name":"John", "age":30, "Years to service":1, "Production year":2010, "Color":"Blue"},\
 {"Name":"Jesper", "age":42, "Years to service":4, "Production year":2022, "Color":"Black"},\
 ....,\
]

### File handling / Input

The input will be a file located on the volume in the folder /data/'file_name.xxx'. The usecase is very specific to the format of the file provided and therefore there is no option to specify another file/folder to the script. It would have been easy to give the option to do so but since you would have to rewrite the shape of the input data in the script anyways it have been choosen to not give the filepath as an environment variable.

## Getting Started

The quickest way to have something running is through docker (see the section [Running container](#running-container)).

Feel free to either import the python-file as a lib or run it directly - or use HELM to spin it up as a pod in kubernetes. These methods are not documented and you will need the know-how yourself.

### Dependencies

* To run the script a kafka broker must be available (use the 'KAFKA_IP' environment variable).
* A kafka topic with input data. An example of this data can be taken from tests/test_export_data.py variable "data".

#### Python (if not run as part of the container)

The python script can probably run on any python 3.9+ version, but your best option will be to check the Dockerfile and use the same version as the container. Further requirements (python packages) can be found in the app/requirements.txt file.

#### Docker

Built and tested on version 20.10.7.

#### HELM (only relevant if using HELM for deployment)

Built and tested on version 3.7.0.

### Running container

1. Clone the repo to a suitable place
````bash
git clone https://github.com/energinet-singularity/scada-parser.git
````

2. Build the container and create a volume
````bash
docker build scada-parser/ -t scada-parser:latest
docker volume create scada-files
````

3. Start the container in docker (change kafka-ip, kafka_topic, ksql_host, ksql_table, and ksql_stream to fit your environment)
````bash
docker run -v scada-files:/data/ -e KAFKA_IP=192.1.1.1:9092 -e KAFKA_TOPIC=test -e KSQL_HOST=192.1.1.1 -e KSQL_TABLE=test-table -e KSQL_STREAM=test-stream  -it --rm scada-parser:latest
````
The container will now be running interactively and you will be able to see the log output. To parse a forecast, it will have to be delivered to the volume somehow. This can be done by another container mapped to the same volume, or manually from another bash-client.

## Help

* Be aware: There are at least two kafka-python-brokers available - make sure to use the correct one (see app/requirements.txt file).

For anything else, please submit an issue or ask the authors.

## Version History

* 1.1.3:
    * First production-ready version
    <!---* See [commit change]() or See [release history]()--->

Older versions are not included in the README version history. For details on them, see the main-branch commit history, but beware: it was the early start and it was part of the learning curve, so it is not pretty. They are kept as to not disturb the integrity of the history.

## License

This project is licensed under the Apache-2.0 License - see the LICENSE.md file for details
