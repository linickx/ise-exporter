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

"""

import sys
import os
import logging
import datetime
from xml.etree import ElementTree


logging.basicConfig(format='[%(levelname)s] %(message)s', level=logging.INFO) # change WARNING to DEBUG if you are a ninja
logger = logging.getLogger("ise")
version = "0.2"

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
    global version
    global headers
    string = '<html><head><title>Cisco ISE Exporter</title></head>\
<body><h1>Cisco ISE Exporter for Prometheus v{}</h1><p><a href="/metrics">Metrics</a></p></body>\
</html>'.format(version)
    return string

@app.route("/metrics")
def route_metrics():
    """ print metrics
    """
    global logger
    global server
    global version
    global headers

    yfile = os.getenv('ISE_FILE', "/etc/ise-exporter/ise.yml")
    cafile = os.getenv('CA_FILE',"/etc/ise-exporter/ca_bundle.pem")

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

    # Things to request:
    the_https_requests = []
    for key, value in iseRestAPI.items():
        logger.debug("Mnt Counter: %s | Path: %s", key, value)
        url = "https://" + ciscoyaml['adm_node'] + value
        auth=(ciscoyaml['rest_uid'], ciscoyaml['rest_pw'])
        the_request = {"metric":key, "url":url, "auth":auth, "type":"mnt"}
        the_https_requests.append(the_request)

    # ERS support
    try:
        ers_enabled = str(ciscoyaml['ers_enabled'])
    except:
        ers_enabled = 'False'


    if ers_enabled == 'True':
        logger.info('External RESTful Services (ERS) Enabled')

        ersAPI = {"internaluser":"/ers/config/internaluser", "networkdevice":"/ers/config/networkdevice"}
        accept_headers = {
            "internaluser":"application/vnd.com.cisco.ise.identity.internaluser.1.0+xml", "networkdevice":"application/vnd.com.cisco.ise.network.networkdevice.1.1+xml",
            "activeguestaccounts":"application/vnd.com.cisco.ise.identity.guestuser.2.0+xml"
            }

        for key, value in ersAPI.items():
            logger.debug("ERS Counter: %s | Path: %s", key, value)
            url = "https://" + ciscoyaml['adm_node'] + ":9060" + value
            auth=(ciscoyaml['rest_uid'], ciscoyaml['rest_pw'])
            the_request = {"metric":key, "url":url, "auth":auth, "type":"ers", "accept_headers":accept_headers[key]}
            the_https_requests.append(the_request)

        # Look for Guest ERS API Credentials
        try:
            ers_guest_uid = ciscoyaml['ers_guest_uid']
            ers_guest_pw = ciscoyaml['ers_guest_pw']
            #
            # ers_guest = True
            # MANUALLY DISABLING
            # ------------------
            # This doesn't work as expected.
            # Status=ACTIVE returns all accounts
            # based on query size
            ers_guest = False
        except:
            ers_guest = False

        if ers_guest:
            try:
                ers_guest_qsize = ciscoyaml['ers_guest_qsize']
            except:
                ers_guest_qsize = '100'

            logger.info("ERS Guest Enabled, Query Size: %s", ers_guest_qsize)
            url = "https://" + ciscoyaml['adm_node'] + ":9060/ers/config/guestuser?status=ACTIVE&size=" + ers_guest_qsize
            auth=(ers_guest_uid, ers_guest_pw)
            metric = "activeguestaccounts"
            the_request = {"metric":metric, "url":url, "auth":auth, "type":"ers", "accept_headers":accept_headers[metric]}
            the_https_requests.append(the_request)


    # Request some stats
    api_response = {}
    for each_https_request in the_https_requests:
        logger.info(each_https_request['url'])
        metric = str(each_https_request['metric'])
        request_headers = {'user-agent':server} # Reset the headers each time
        try:
            if each_https_request['type'] == "mnt":
                r = requests.get(each_https_request['url'], verify=r_ssl_verify, auth=each_https_request['auth'])
                root = ElementTree.fromstring(r.content)
                api_response[metric] = root[0].text
            if each_https_request['type'] == "ers":
                request_headers['ACCEPT'] = each_https_request['accept_headers'] # update header
                r = requests.get(each_https_request['url'], verify=r_ssl_verify, auth=each_https_request['auth'], headers=request_headers)
                root = ElementTree.fromstring(r.content)
                logger.debug(r.content)
                no_of_xmls = len(root[0]) # count the number of entries in the XML
                api_response[metric] = str(no_of_xmls)

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
