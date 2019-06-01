# VBIM

Video-Bitmovin-ITEC-MONROE (VBIM) is a measurement framework for evaluating video streaming QoE in broadband networks.

## Client Side

### Building the Docker Image

Run `bash build.sh <container name>`, making sure that the relevant Dockerfile is named `<container name>.docker`.

An example can be found in the vbim-client directory.

### Pushing the Docker Image

Run `bash push.sh <container name> <Dockerhub repository>`, making sure you have access rights to the repository.

An example can be found in the vbim-client directory.

### Readily Compiled Docker Image

A readily compiled Docker image, generated using the source files provided here, pointing towards an ITEC server can be found on [Dockerhub](https://hub.docker.com/r/cmidoglu/vbim-demo).

Pull by running `docker pull cmidoglu/vbim-demo`.

## Server Side

Update the `<player>.php` files with your Bitmovin Analytics key.
Update the `bitmovin.php` file with your Bitmovin Player key.
Upload the relevant `<player>.php` files to an HTTP server, to host the player landing pages.

## Configuring and Running an Experiment

Since the VBIM client is designed as a Docker container, it can be run on any machine supporting Docker virtualization, including MONROE measurement nodes.

### Configuration Parameters

A comprehensive list of all configuration parameters and their default values can be found on the [ITEC DASH page](http://demo.itec.aau.at/monroe/configuration.php).

A sample configuration file is provided under the vbim-client directory.

### Running on a Local Machine

An experiment can be started locally with the following command:
`sudo docker run --net=host -v <folder for results>:/monroe/results -v <configuration file>:/monroe/config cmidoglu/vbim-demo`

If a configuration file is not specified, the experiment uses the default values.
Experiment results will be stored in the local folder specified in the `docker` command.

### Running on the MONROE Platform

In order to run an experiment on deployed MONROE nodes, the [MONROE web scheduler](https://monroe-system.eu) can be used with a valid certificate.

The web scheduler allows for the container image and configuration parameters to be specified from the GUI, along with the country, number and type of nodes, data and traffic quotas, time and date of execution. Periodic measurement can also be scheduled from the interface using the "recurring" option. 

Experiment results can be retrieved from the same interface manually, or by automatized web requests to the corresponding URL using a valid certificate. An example script for automatically retrieving a range of measurements can be found under the vbim-utilities directory.

## Software Certificates and Keys

Bitmovin Player and Bitmovin Analytics keys can be acquired free of charge for a trial period, see [Bitmovin' signup] (https://bitmovin.com/dashboard/signup).

Parts of the MONROE platform can be used free of charge by researchers and developers, contact the [MONROE Alliance] (https://www.monroe-project.eu/contacts/).

