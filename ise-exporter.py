#!/usr/bin/env python
# coding=utf-8
# Python linter configuration.
# pylint: disable=I0011
# pylint: disable=C0301
# pylint: disable=W0702
# I don't get W0702, I want to catch all exceptions..  so, disabling.
""" Prometheus Cisco ISE Exporter

    TODO:
    * Don't use globals!
    * Test / Travis
    * Custom UA string for requests

"""

import sys
import os
import logging
import datetime
from xml.etree import ElementTree


logging.basicConfig(format='[%(levelname)s] %(message)s', level=logging.INFO) # change WARNING to DEBUG if you are a ninja
logger = logging.getLogger("ise")
version = "0.1"

try:
    import yaml
except:
    logger.error("pyyaml not installed - http://pyyaml.org")
    logger.debug("Exception: %s", sys.exc_info()[0])
    sys.exit(1)

try:
    from flask import Flask, make_response
except:
    logger.error("Flask not installed - http://flask.pocoo.org/")
    logger.debug("Exception: %s", sys.exc_info()[0])
    sys.exit(1)

try:
    import requests
except:
    logger.error("Requests not installed - http://docs.python-requests.org/en/master/")
    logger.debug("Exception: %s", sys.exc_info()[0])
    sys.exit(1)

# Response variables
server = "ise-exporter/" + version
headers = {
    'Content-Type':'text/plain',
    'Cache-Control':'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0',
    'Last-Modified':datetime.datetime.now(),
    'Pragma':'no-cache',
    'Expires':'-1',
    'Server':server}


def display_error(msg):
    """ Print Error to Console as well as HTTP Response
    """
    global logger
    global version
    global headers
    logger.critical(msg)
    # 503 unailable, i.e. admin needs to fix something
    return make_response(msg, '503', headers)


app = Flask(__name__)
@app.route("/")
def route_root():
    """ Respond to requests :)
    """
    global logger
    global version
    global version
    global headers

    yfile = "/etc/ise-exporter/ise.yml"
    cafile = "/etc/ise-exporter/ca_bundle.pem"

    if os.path.isfile(yfile) is False:
        return display_error("Cannot find file: " + yfile)

    if os.path.isfile(cafile):
        r_ssl_verify = cafile
    else:
        logger.warning("Cannot find file: " + cafile + " SSL verification will be disabled")
        r_ssl_verify = False

    try:
        datastream = open(yfile, 'r') # Open the yaml file
        ciscoyaml = yaml.load(datastream)
    except:
        return display_error("Failed to load Yaml! | Exception: " + str(sys.exc_info()[1]))

    # Check to see if the YAML has eveything we need?
    yaml_vars = ['adm_node', 'rest_uid', 'rest_pw']
    for expected_var in yaml_vars:
        try:
            ciscoyaml[expected_var]
        except:
            return display_error("Variable " + expected_var + " not set in " + yfile)

    # Allow for the rest version to be change, default on version 2
    try:
        api_ver = str(ciscoyaml['rest_ver'])
    except:
        api_ver = '2'

    # Select Correct URLs
    if api_ver == '1':
        logger.info("ISE API Version set to " + api_ver)
        iseRestAPI = {"activecount":"/ise/mnt/Session/ActiveCount", "posturecount":"/ise/mnt/Session/PostureCount", "profilercount":"/ise/mnt/Session/ProfilerCount"}
    elif api_ver == '2':
        iseRestAPI = {"activecount":"/admin/API/mnt/Session/ActiveCount", "posturecount":"/admin/API/mnt/Session/PostureCount", "profilercount":"/admin/API/mnt/Session/ProfilerCount"}
    else:
        return display_error("Unexpected rest_ver in " + yfile)

    # Request some stats
    api_response = {}
    for key, value in iseRestAPI.items():
        logger.info("Counter: %s | Path: %s", key, value)
        r_url = "https://" + ciscoyaml['adm_node'] + value
        try:
            r = requests.get(r_url, verify=r_ssl_verify, auth=(ciscoyaml['rest_uid'], ciscoyaml['rest_pw']))
            root = ElementTree.fromstring(r.content)
            api_response[key] = root[0].text
        except:
            # strictly speaking this should have status code 502 bad gateway as this is an upstream/proxy error
            return display_error("Failed to Connect to ISE | Exception: " + str(sys.exc_info()[1]))

    logger.info(str(api_response)) # Quick summary of what we got back!
    prometheus_string = ""

    # build the text string (response)
    for key, value in api_response.items():
        prometheus_metric = "cisco_ise_" + key
        prometheus_string = prometheus_string + "# TYPE " + prometheus_metric + " gauge" + "\n"
        prometheus_string = prometheus_string + prometheus_metric + "{instance=\"" + ciscoyaml['adm_node'] + "\"}" + " " + value + "\n"

    return make_response(prometheus_string, '200', headers)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port="9123", debug=False)
