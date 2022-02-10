# SCADA parser

A container that parses messages from a CSV file to a kafka topic.

## Description

This repository contains a python-script that will read a CSV-file, process the information and produce the data as messages to a kafka broker. The current version of the script is suited to a specific usecase and is not so versatile as the data/CSV file will have to fit a given format of data - and the output will fit the specific format needed for the application using the data. The script is intended to be run as part of a container/kubernetes, so a Dockerfile is provided as well, as is a set of helm charts.

### Exposed environment variables:

| Name | Description |
|--|--|
|KAFKA_IP|Host-name or IP+Port of the kafka-broker|
|KSQL_HOST|Host-name or IP+Port of the ksql server|
|KSQL_STREAM|Name of the stream created on the kSQL server|
|KSQL_TABLE|Name of the table created on the kSQL server|
|KAFKA_TOPIC|The topic the script will produce messages to on the kafka-broker|
|DEBUG|Default unset - set to anything to log everything to screen (not in helm-charts)|

### File handling / Input

Each 5 seconds the script will look for a file in the folder '/data/' named 'DLR_kafka_out.IMP'. If a file is present and it has not already been parsed (i.e. the file has been modified since last run), it will be processed by the script. The file has to follow the structure 'MRID,Value,Quality,'.

Example of how a file could look
````
askfdjgi666jgju,      30.584,0,
hkvhdufg6678kha,      89.522,0,
````

### Kafka messages / Output

When a file is parsed, the contents will be reshaped and sent to the Kafka-broker line by line.

Example of how the kafka-message could look
````json
{"MRID":"askfdjgi666jgju", "Value":30.584, "Quality":0, "Time":"2022-02-04 07:49:01"}
{"MRID":"hkvhdufg6678kha", "Value":89.522, "Quality":0, "Time":"2022-02-04 07:49:01"}
````

The first three pieces of information are taken directly from the file, while the time represents the time the input-file was last modified.

## Getting Started

The quickest way to have something running is through docker (see the section [Running container](#running-container)).

Feel free to either import the python-file as a lib or run it directly - or use HELM to spin it up as a pod in kubernetes. These methods are not documented and you will need the know-how yourself.

### Dependencies

* A kafka broker (with a writeable topic) must be available (use the 'KAFKA_IP' and 'KAFKA_TOPIC' environment variables).
* A KSQL server should be available, but the script will function without it.

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

3. Start the container in docker (change kafka-ip and kafka_topic to fit your environment - and drop or change ksql_host, ksql_table and ksql_stream to fit your environment)
````bash
docker run -v scada-files:/data/ -e KAFKA_IP=192.1.1.1:9092 -e KAFKA_TOPIC=test -e KSQL_HOST=192.1.1.1 -e KSQL_TABLE=test-table -e KSQL_STREAM=test-stream  -it --rm scada-parser:latest
````
The container will now be running interactively and you will be able to see the log output. To parse a file, it will have to be delivered to the root of the volume somehow. This can be done by another container mapped to the same volume, or manually from another bash-client by the use of sudo command (please verify volume-path is correct before trying this):
````bash
sudo cp testfile.csv /var/lib/docker/volumes/scada-files/_data/
````

## Help

* Be aware: There are at least two kafka-python-brokers available - make sure to use the correct one (see app/requirements.txt file).

For anything else, please submit an issue or ask the authors.

## Version History

* 1.1.3
    * Added standard python logging module
    * Created README.md
    * Set up structure of the repo

* 1.1.2:
    * First production-ready version
    <!---* See [commit change]() or See [release history]()--->

Older versions are not included in the README version history. For details on them, see the main-branch commit history, but beware: it was the early start and it was part of the learning curve, so it is not pretty. They are kept as to not disturb the integrity of the history.

## License

This project is licensed under the Apache-2.0 License - see the LICENSE.md file for details
