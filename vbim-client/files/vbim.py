#!/usr/bin/python
# -*- coding: utf-8 -*-

# Author: Cise Midoglu (based on a MONROE template)
# License: GNU General Public License v3
# Developed for use within the EU H2020 MONROE project

"""
Simple wrapper to run the VBIM client.
The script will execute one experiment batch for each of the enabled interfaces.
All default values are configurable from the scheduler.
The output will be formatted into a JSON object suitable for storage in the MONROE database.
"""

from collections import OrderedDict
import glob
import io
from itertools import product
import json
from multiprocessing import Process, Manager
import netifaces
import os
import pingparser
from random import shuffle
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import shutil
from subprocess import Popen, PIPE, STDOUT, call, check_output, CalledProcessError
import sys
import tarfile
from tempfile import NamedTemporaryFile
import time
import traceback
from traceroute_parser import parse_traceroute
import urllib
from urlparse import urlparse
import uuid
import zmq

# Configuration
CONFIGFILE = "/monroe/config"
CONTAINER_VERSION = "v0.5"
DEBUG = False
TAG = "[vbim.py] "

EXPCONFIG = {
  # The following are relevant to the MONROE platform
  "guid": "localGuid",                                                  # Should be overridden by scheduler
  "nodeid": "localNode",                                                # Node ID
  "ifup_interval_check": 5,                                             # Interval to check if interface is up
  "interfaces_without_metadata": ["eth0","wlan0"],                      # Do not wait for metadata on these interfaces
  "modeminterfacename": "InternalInterface",                            # Modem interface name
  "modem_metadata_topic": "MONROE.META.DEVICE.MODEM",                   # Modem metadata topic string
  "zmqport": "tcp://172.17.0.1:5556",                                   # ZeroMQ port
  "cnf_add_modem_metadata_to_result": False,                            # Set to True to save one captured modem metadata
  "cnf_enabled_interfaces": ["eth0","op0","op1","op2","nlw_1","nlw_2"], # Interfaces on which to run
  "cnf_exp_grace": 10000,                                               # Grace period before killing experiment
  "cnf_disabled_interfaces": ["lo","metadata","eth2","wlan0",           # Interfaces to NOT run on
                                 "wwan0","wwan1","wwan2","docker0"],
  "cnf_meta_grace": 120,                                                # Grace period to wait for interface metadata
  "cnf_save_metadata_resultdir": "/monroe/tmp/metadata",                # Set to a directory to enable saving the metadata stream
  "cnf_save_metadata_topic": "MONROE.META",                             # Metadata topic to be saved as a complete stream, e.g., "MONROE.META.DEVICE.MODEM"

  # The following are relevant to Bitmovin Analytics
  "cnf_cdnprovider": "testCdnProvider",                                 # CDN provider string
  "cnf_customdata1": "testCustomData1",                                 # Custom data string (1)
  "cnf_customdata2": "testCustomData2",                                 # Custom data string (2)
  "cnf_customdata3": "testCustomData3",                                 # Custom data string (3)
  "cnf_customdata4": "testCustomData4",                                 # Custom data string (4)
  "cnf_customdata5": "testCustomData5",                                 # Custom data string (5)
  "cnf_experimentname": "testExperimentName",                           # Experiment name string
  "cnf_sessionid": "testSessionId",                                     # Session ID string
  "cnf_title": "testTitle",                                             # Title string
  "cnf_userid": "testUserId",                                           # User ID string
  "cnf_videoid": "testVideoId",                                         # Video ID string

  # The following are generic parameters
  "cnf_abr": "abrDynamic",                                              # ABR algorithm string
  "cnf_dataid": "MONROE.EXP.VBIM",                                      # Identifier of experiment type
  "cnf_duration": 60,                                                   # Streaming duration
  "cnf_player": "bitmovin",                                             # Video player string
  "cnf_multiconfig_enabled": True,                                      # Whether or not multiple configuration is enabled
  "cnf_multiconfig_randomize": True,                                    # If enabled, whether or not to randomize the order of multiple configurations
  "cnf_multiconfig": [{"cnf_player": "bitmovin",                        # Multiple configurations as a JSON array
  "cnf_ping_target": "cdn.bitmovin.com"}, 
  {"cnf_player": "dashjs","cnf_abr": "abrBola", 
  "cnf_ping_target": "cdnjs.cloudflare.com"}, 
  {"cnf_player": "dashjs","cnf_abr": "abrDynamic", 
  "cnf_ping_target": "cdnjs.cloudflare.com"}, 
  {"cnf_player": "dashjs","cnf_abr": "abrThroughput", 
  "cnf_ping_target": "cdnjs.cloudflare.com"}, 
  {"cnf_player": "shaka", "cnf_ping_target": "cdnjs.cloudflare.com"}],
  "cnf_ping_count": 11,                                                 # Number of pings
  "cnf_ping_skip": False,                                               # Whether or not to skip ping
  "cnf_ping_target": "orf.at",                                          # Ping target, examples: "orf.at", "194.232.104.149"
  "cnf_ping_timeout": 2,                                                # Timeout setting for ping
  "cnf_resultdir": "/monroe/results/",                                  # Directory for saving results
  "cnf_stub": "",                                                       # URL stub for landing page
  "cnf_tag": None,                                                      # Tag string for measurement
  "cnf_time_between_runs": 5,                                           # Time to wait between different runs
  "cnf_traceroute_skip": True,                                          # Whether or not to skip traceroute
  "cnf_traceroute_target": "orf.at",                                    # Traceroute target
  "cnf_verbosity": 3,                                                   # Verbosity level: 0=mute, 1=error, 2=information, 3=verbose
  "timestamp": time.gmtime()                                            # Timestamp for the measurement (batch)
}

def get_url(stub, player, cdnprovider=None, experimentname=None, title=None, userid=None, videoid=None, customdata1=None, customdata2=None, customdata3=None, customdata4=None, customdata5=None):

    f = urllib.urlencode({"cdnProvider": str(cdnprovider), "experimentName": str(experimentname), "title": str(title), "userId": str(userid), "videoId": str(videoid), "customData1": str(customdata1), "customData2": str(customdata2), "customData3": str(customdata3), "customData4": str(customdata4), "customData5": str(customdata5)})

    return "{}/{}/index.php?{}".format(stub, player, f)

def get_filename(expconfig, postfix, ending, tstamp, interface):

    return "{}_NODE.{}_INTERFACE.{}_PLAYER.{}_TIME.{}{}.{}".format(expconfig["cnf_dataid"], expconfig["nodeid"], interface, expconfig["cnf_player"], tstamp, ("_" + postfix) if postfix else "", ending)

def save_output(expconfig, msg, postfix=None, ending="json", tstamp=time.time(), outdir="/monroe/results/", interface="interface"):
    if not os.path.exists(outdir):
        os.makedirs(outdir)
        print(TAG + "save_output function is creating a new folder")
    f = NamedTemporaryFile(mode="w+", delete=False, dir=outdir)
    f.write(msg)
    f.close()
    outfile = os.path.join(outdir, get_filename(expconfig, postfix, ending, tstamp, interface))
    move_file(f.name, outfile)

def move_file(f, t):
    try:
        shutil.move(f, t)
        os.chmod(t, 0o644)
    except:
        traceback.print_exc()

def copy_file(f, t):
    try:
        shutil.copyfile(f, t)
        os.chmod(t, 0o644)
    except:
        traceback.print_exc()

def get_config_combinations(expconfig):

    if "cnf_multiconfig" not in expconfig or not expconfig["cnf_multiconfig_enabled"]:
        expconfig.update({"summary_number_of_configurations":1})
        yield expconfig.copy()
        return

    configurations = expconfig["cnf_multiconfig"]
    
    if type(configurations) is list:
        do_rand = expconfig["cnf_multiconfig_randomize"] if "cnf_multiconfig_randomize" in expconfig else False
        if do_rand:
            shuffle(configurations)

    expconfig.update({"summary_number_of_configurations":len(configurations)})

    for configuration in configurations:
        out = expconfig.copy()
        out.update(configuration)
        yield out

def setup_chrome_options():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-quic")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--autoplay-policy=no-user-gesture-required")
    return chrome_options

def update_session_tag(expconfig):
    cfg = expconfig.copy()
    cfg.update({"cnf_tag": str(uuid.uuid4())})
    return cfg

def update_abr_algorithm(expconfig):
    cfg = expconfig.copy()
    abr_str=cfg["cnf_abr"]
    if "bitmovin" in cfg["cnf_player"] or "bitdash" in cfg["cnf_player"]:
        abr_str = "bitmovin"
    if "shaka" in cfg["cnf_player"]:
        abr_str = "shaka"
    cfg.update({"cnf_abr": abr_str})
    return cfg

def update_session_id(expconfig, sessionid):
    cfg = expconfig.copy()
    cfg.update({"cnf_sessionid": sessionid})
    return cfg

def update_custom_data_fields(expconfig):
    cfg = expconfig.copy()
    cfg.update({
    "cnf_customdata1": expconfig["cnf_cdnprovider"],
    "cnf_customdata2": expconfig["cnf_abr"],
    "cnf_customdata3": expconfig["cnf_experimentname"],
    "cnf_customdata4": CONTAINER_VERSION,
    "cnf_customdata5": expconfig["cnf_tag"],
    })
    return cfg

def traceroute(target, interface):

    cmd = ["traceroute", "-A"]
    if (interface):
        cmd.extend(["-i", interface])  
    cmd.append(target)
    
    if EXPCONFIG["cnf_verbosity"] > 1:
        print("\n" + TAG + "Running traceroute against..." + target)

    time_start = time.time()
    p = Popen(cmd, stdout=PIPE)
    data = p.communicate()[0]
    time_end = time.time()

    if EXPCONFIG["cnf_verbosity"] > 1:
        print(TAG + "Traceroute finished.")

    if EXPCONFIG["cnf_verbosity"] > 2:
        print(TAG + "Traceroute result: \n{}".format(data))

    try:
        traceroute = parse_traceroute(data)
    except Exception as e:
        traceroute = {"error": "could not parse traceroute"}
    if not traceroute:
        traceroute = {"error": "no traceroute output"}

    traceroute["time_start"] = time_start
    traceroute["time_end"] = time_end
    traceroute["raw"] = data.decode("ascii", "replace")
    return traceroute

def ping(target, num_pings, interface, ping_timeout):

    cmd = ["ping", "-c", str(num_pings), "-a", "-W", str(ping_timeout)]

    if (interface):
        cmd.extend(["-I", interface])
    cmd.append(target)

    if EXPCONFIG["cnf_verbosity"] > 1:
        print("\n" + TAG + "Running {} pings to {} ...".format(num_pings, target))

    time_start = time.time()
    p = Popen(cmd, stdout=PIPE)
    data = p.communicate()[0]
    time_end = time.time()

    if EXPCONFIG["cnf_verbosity"] > 1:
        print(TAG + "Ping finished.")

    if EXPCONFIG["cnf_verbosity"] > 2:
        print(TAG + "Ping result: \n{}".format(data))

    try:
        ping = pingparser.parse(data)
    except Exception as e:
        ping = {"error": "could not parse ping"}
    if not ping:
        ping = {"error": "no ping output"}

    ping["time_start"] = time_start
    ping["time_end"] = time_end
    ping["raw"] = data.decode("ascii", "replace")

    return ping

def metadata(meta_ifinfo, ifname, expconfig):
    """Seperate process that attach to the ZeroMQ socket as a subscriber.

        Will listen forever to messages with topic defined in topic and update
        the meta_ifinfo dictionary (a Manager dict).
    """
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.connect(expconfig["zmqport"])
    topic = expconfig["modem_metadata_topic"]
    do_save = False

    if not DEBUG and "cnf_save_metadata_topic" in expconfig and "cnf_save_metadata_resultdir" in expconfig and expconfig["cnf_save_metadata_resultdir"]:
        topic = expconfig["cnf_save_metadata_topic"]

        resultdir_metadata = expconfig["cnf_save_metadata_resultdir"]
        if not os.path.exists(resultdir_metadata):
            os.makedirs(resultdir_metadata)

        do_save = True

    socket.setsockopt(zmq.SUBSCRIBE, topic.encode("ASCII"))
    # End Attach

    while True:
        data = socket.recv_string()
        try:
            (topic, msgdata) = data.split(" ", 1)
            msg = json.loads(msgdata)

            if do_save and not topic.startswith("MONROE.META.DEVICE.CONNECTIVITY."):
                # Skip all messages that belong to connectivity as they are redundant
                # as we save the modem messages.

                msg["cnf_dataid"] = expconfig["cnf_dataid"]
                msg["cnf_player"] = expconfig["cnf_player"]
                msg["nodeid"] = expconfig["nodeid"]

                tstamp = time.time()
                if "Timestamp" in msg:
                    tstamp = msg["Timestamp"]

            if topic.startswith(expconfig["modem_metadata_topic"]):
                if (expconfig["modeminterfacename"] in msg and
                        msg[expconfig["modeminterfacename"]] == ifname):

                    save_output(expconfig=msg, msg=json.dumps(msg), postfix=None, tstamp=tstamp, outdir=resultdir_metadata, interface=ifname)

                    # In place manipulation of the reference variable
                    for key, value in msg.items():
                        meta_ifinfo[key] = value

        except Exception as e:
            if expconfig["cnf_verbosity"] > 0:
                print (TAG + "Cannot get metadata in container: {}"
                       ", {}").format(e, expconfig["guid"])
            pass

def check_if(ifname):
    """Check if interface is up and have got an IP address."""
    return (ifname in netifaces.interfaces() and
            netifaces.AF_INET in netifaces.ifaddresses(ifname))

def get_ip(ifname):
    """Get IP address of interface."""
    return netifaces.ifaddresses(ifname)[netifaces.AF_INET][0]["addr"]

def check_meta(info, graceperiod, expconfig):
    """Check if we have recieved required information within graceperiod."""
    if not (expconfig["modeminterfacename"] in info and
            "Operator" in info and
            "Timestamp" in info and
            time.time() - info["Timestamp"] < graceperiod):
        return False
    if not "require_modem_metadata" in expconfig:
        return True
    for k,v in expconfig["require_modem_metadata"].items():
        if k not in info:
            if expconfig["cnf_verbosity"] > 0:
                print(TAG + "Got metadata but key '{}' is missing".format(k))
            return False
        if not info[k] == v:
            if expconfig["cnf_verbosity"] > 0:
                print(TAG + "Got metadata but '{}'='{}'; expected: '{}'".format(k, info[k], v))
            return False
    return True

def add_manual_metadata_information(info, ifname, expconfig):
    """Only used for local interfaces that do not have any metadata information.

       Normally eth0 and wlan0.
    """
    info[expconfig["modeminterfacename"]] = ifname
    info["Operator"] = "localOperator"
    info["ICCID"] = "localIccid"
    info["Timestamp"] = time.time()

def create_meta_process(ifname, expconfig):
    meta_info = Manager().dict()
    process = Process(target=metadata,
                      args=(meta_info, ifname, expconfig, ))
    process.daemon = True
    return (meta_info, process)

def create_exp_process(meta_info, expconfig, ifname):
    process = Process(target=run_exp, args=(meta_info, expconfig, ifname))
    process.daemon = True
    return process

def run_exp(meta_info, expconfig, ifname):
    """Seperate process that runs the experiment and collects the ouput.
        Will abort if the interface goes down.
    """

    cfg = update_custom_data_fields(update_abr_algorithm(update_session_tag(expconfig.copy())))
    timestamp_run = time.strftime("%Y%m%d-%H%M%S",time.gmtime())

    try:

        # Run ping if requested
        if not cfg["cnf_ping_skip"]:
            towrite_ping = ping(cfg["cnf_ping_target"], cfg["cnf_ping_count"], ifname, cfg["cnf_ping_timeout"])

        # Run traceroute if requested
        if not cfg["cnf_traceroute_skip"]:
            towrite_traceroute = traceroute(cfg["cnf_traceroute_target"], ifname)

        if cfg["cnf_verbosity"] > 1:
            print("\n" + TAG + "Player..." + str(cfg["cnf_player"]))
            print(TAG + "ABR Algorithm..." + str(cfg["cnf_abr"]))

            # Can add further printouts, see examples below
            # print(TAG + "Title..." + str(cfg["cnf_title"]))
            # print(TAG + "User ID..." + str(cfg["cnf_userid"]))
            # print(TAG + "Video ID..." + str(cfg["cnf_videoid"]))
            # print(TAG + "Custom Data 1..." + str(cfg["cnf_customdata1"]))
            # print(TAG + "Custom Data 2..." + str(cfg["cnf_customdata2"]))
            # print(TAG + "Custom Data 3..." + str(cfg["cnf_customdata3"]))
            # print(TAG + "Custom Data 4..." + str(cfg["cnf_customdata4"]))
            # print(TAG + "Custom Data 5..." + str(cfg["cnf_customdata5"]))

        target_url = get_url(cfg["cnf_stub"], cfg["cnf_player"], cfg["cnf_cdnprovider"], cfg["cnf_experimentname"], cfg["cnf_title"], cfg["cnf_userid"], cfg["cnf_videoid"], cfg["cnf_customdata1"], cfg["cnf_customdata2"], cfg["cnf_customdata3"], cfg["cnf_customdata4"], cfg["cnf_customdata5"])

        desired_capabilities = DesiredCapabilities.CHROME
        desired_capabilities["loggingPrefs"] = { "browser":"ALL" }
        driver = webdriver.Chrome(chrome_options=setup_chrome_options(), desired_capabilities=desired_capabilities)
        driver.get(target_url)
        time.sleep(cfg["cnf_duration"])

        console_output = driver.get_log("browser")
        towrite_consoleoutput = console_output

        try:
            session_id = driver.find_element_by_id("sessionID").get_attribute("value")
            if session_id:
                print("\n" + TAG + "sessionID..."+session_id)
                cfg = update_session_id(cfg,session_id)

            else:
                cfg = update_session_id(cfg,"NA")
        except Exception as e:
            if cfg["cnf_verbosity"] > 0:
                print (TAG + "[Exception #3] Retrieving session ID failed for error: {}").format(e)
            cfg = update_session_id(cfg,"NA")
            pass

        try:
            if "cnf_add_to_result" not in cfg:
                cfg["cnf_add_to_result"] = {}

            cfg["cnf_add_to_result"].update({
                "summary_containerversion": CONTAINER_VERSION,
                "summary_debug": DEBUG,
                "monroe_guid": cfg["guid"],
                "monroe_nodeid": cfg["nodeid"],
                "monroe_modeminterfacename": cfg["modeminterfacename"],
                "cnf_save_metadata_topic": cfg["cnf_save_metadata_topic"],
                "cnf_cdnprovider": cfg["cnf_cdnprovider"],
                "cnf_customdata1": cfg["cnf_customdata1"],
                "cnf_customdata2": cfg["cnf_customdata2"],
                "cnf_customdata3": cfg["cnf_customdata3"],
                "cnf_customdata4": cfg["cnf_customdata4"],
                "cnf_customdata5": cfg["cnf_customdata5"],
                "cnf_experimentname": cfg["cnf_experimentname"],
                "cnf_sessionid": cfg["cnf_sessionid"],
                "cnf_title": cfg["cnf_title"],
                "cnf_userid": cfg["cnf_userid"],
                "cnf_videoid": cfg["cnf_videoid"],
                "cnf_abr": cfg["cnf_abr"],
                "cnf_dataid": cfg["cnf_dataid"],
                "cnf_duration": cfg["cnf_duration"],
                "cnf_player": cfg["cnf_player"],
                "cnf_stub": cfg["cnf_stub"],
                "cnf_tag": cfg["cnf_tag"],
                "cnf_time_between_runs": cfg["cnf_time_between_runs"],
                "cnf_verbosity": cfg["cnf_verbosity"],
                "summary_time_batch": time.strftime("%Y%m%d-%H%M%S",cfg["timestamp"]),
                "summary_time_run": timestamp_run
                })

            if "cnf_multiconfig_enabled" in cfg and cfg["cnf_multiconfig_enabled"]:
                cfg["cnf_add_to_result"].update({
                    "cnf_multiconfig_enabled": cfg["cnf_multiconfig_enabled"],
                    "cnf_multiconfig_randomize": cfg["cnf_multiconfig_randomize"],
                    "cnf_multiconfig": cfg["cnf_multiconfig"],
                    "summary_number_of_configurations": cfg["summary_number_of_configurations"]
                })

            if "cnf_ping_skip" in cfg and not cfg["cnf_ping_skip"]:
                cfg["cnf_add_to_result"].update({
                      "cnf_ping_count": cfg["cnf_ping_count"],
                      "cnf_ping_target": cfg["cnf_ping_target"],
                      "cnf_ping_timeout": cfg["cnf_ping_timeout"]
                })
            
            if "cnf_traceroute_skip" in cfg and not cfg["cnf_traceroute_skip"]:
                cfg["cnf_add_to_result"]["cnf_traceroute_target"] = cfg["cnf_traceroute_target"]

            if "ICCID" in meta_info:
                cfg["cnf_add_to_result"]["summary_iccid"] = meta_info["ICCID"]
            if "Operator" in meta_info:
                cfg["cnf_add_to_result"]["summary_operator"] = meta_info["Operator"]
            if "IMSIMCCMNC" in meta_info:
                cfg["cnf_add_to_result"]["summary_imsimccmnc"] = meta_info["IMSIMCCMNC"]
            if "NWMCCMNC" in meta_info:
                cfg["cnf_add_to_result"]["summary_nwmccmnc"] = meta_info["NWMCCMNC"]
            if "CID" in meta_info:
                cfg["cnf_add_to_result"]["summary_cid"] = meta_info["CID"]
            if "LAC" in meta_info:
                cfg["cnf_add_to_result"]["summary_lac"] = meta_info["LAC"]
            if "DEVICEMODE" in meta_info:
                cfg["cnf_add_to_result"]["summary_devicemode"] = meta_info["DEVICEMODE"]
            if "DEVICESUBMODE" in meta_info:
                cfg["cnf_add_to_result"]["summary_devicesubmode"] = meta_info["DEVICESUBMODE"]
            if "LATITUDE" in meta_info:
                cfg["cnf_add_to_result"]["summary_latitude"] = meta_info["LATITUDE"]
            if "LONGITUDE" in meta_info:
                cfg["cnf_add_to_result"]["summary_longitude"] = meta_info["LONGITUDE"]

            ifname = meta_info[cfg["modeminterfacename"]]
            cfg["cnf_add_to_result"]["summary_interface"] = ifname

            # Add metadata if requested
            if cfg["cnf_add_modem_metadata_to_result"]:
                for k,v in meta_info.items():
                    cfg["cnf_add_to_result"]["info_meta_modem_" + k] = v

            towrite_data = cfg["cnf_add_to_result"]

        except Exception as e:
            if cfg["cnf_verbosity"] > 0:
                print (TAG + "[Exception #2] Execution or parsing failed for error: {}").format(e)

        if not DEBUG:
            if cfg["cnf_verbosity"] > 1:
                print("\n" + TAG + "Saving results")

            # Saving output file(s)
            save_output(expconfig=cfg, msg=json.dumps(towrite_data), postfix=("SESSION." + cfg["cnf_sessionid"] + "_SUMMARY"), tstamp=timestamp_run, outdir=cfg["cnf_resultdir"], interface=ifname)

            save_output(expconfig=cfg, msg=json.dumps(towrite_consoleoutput), postfix=("SESSION." + cfg["cnf_sessionid"] + "_CONSOLEOUTPUT"), tstamp=timestamp_run, outdir=cfg["cnf_resultdir"], interface=ifname)

            if not cfg["cnf_ping_skip"]:
                save_output(expconfig=cfg, msg=json.dumps(towrite_ping), postfix=("SESSION." + cfg["cnf_sessionid"] + "_PING"), tstamp=timestamp_run, outdir=cfg["cnf_resultdir"], interface=ifname)

            if not cfg["cnf_traceroute_skip"]:
                save_output(expconfig=cfg, msg=json.dumps(towrite_traceroute), postfix=("SESSION." + cfg["cnf_sessionid"] + "_TRACEROUTE"), tstamp=timestamp_run, outdir=cfg["cnf_resultdir"], interface=ifname)

            if not os.path.exists(cfg["cnf_save_metadata_resultdir"]) or not os.listdir(cfg["cnf_save_metadata_resultdir"]):
                print(TAG + "No metadata, skipping folder compression")
            else:
                shutil.make_archive(base_name=os.path.join(cfg["cnf_resultdir"], get_filename(expconfig=cfg, postfix=("SESSION." + cfg["cnf_sessionid"]), ending="METADATA", tstamp=timestamp_run, interface=ifname)), format="gztar", root_dir=cfg["cnf_save_metadata_resultdir"],base_dir="./")

                if cfg["cnf_verbosity"] > 2:
                    print("\n" + TAG + "Contents of " + cfg["cnf_save_metadata_resultdir"] + " to be removed:")
                    for tmpfile in os.listdir(cfg["cnf_save_metadata_resultdir"]):
                        print(tmpfile)
                        os.remove(os.path.join(cfg["cnf_save_metadata_resultdir"],tmpfile))

                shutil.rmtree(cfg["cnf_save_metadata_resultdir"])

        print("")

    except Exception as e:
        if cfg["cnf_verbosity"] > 0:
            print (TAG + "[Exception #1] Execution or parsing failed for error: {}").format(e)

if __name__ == '__main__':
    """The main thread control the processes (experiment/metadata))."""
    # Try to get the experiment config as provided by the scheduler
    try:
        with open(CONFIGFILE) as configfd:
            EXPCONFIG.update(json.load(configfd))
    except Exception as e:
        print(TAG + "Cannot retrive expconfig {}".format(e))
        # raise e
        print(TAG + "Continuing with default configuration parameters")

    if DEBUG:
        # We are in debug state always put out all information
        EXPCONFIG["cnf_verbosity"] = 3
        try:
            EXPCONFIG["cnf_disabled_interfaces"].remove("eth0")
        except Exception as e:
            pass

    # Short hand variables and check so we have all variables we need
    try:
        disabled_interfaces = EXPCONFIG["cnf_disabled_interfaces"]
        if_without_metadata = EXPCONFIG["interfaces_without_metadata"]
        meta_grace = EXPCONFIG["cnf_meta_grace"]
        exp_grace = EXPCONFIG["cnf_exp_grace"]
        ifup_interval_check = EXPCONFIG["ifup_interval_check"]
        time_between_runs = EXPCONFIG["cnf_time_between_runs"]
        EXPCONFIG["cnf_resultdir"]
        EXPCONFIG["cnf_verbosity"]
        EXPCONFIG["guid"]
        EXPCONFIG["modeminterfacename"]
        EXPCONFIG["modem_metadata_topic"]
        EXPCONFIG["zmqport"]

    except Exception as e:
        print("ERR: Missing expconfig variable {}".format(e))
        raise e

    sequence_number = 0
    tot_start_time = time.time()
    for ifname in netifaces.interfaces():
        # Skip disbaled interfaces
        if ifname in disabled_interfaces:
            if EXPCONFIG["cnf_verbosity"] > 1:
                print(TAG + "Interface is disabled, skipping {}".format(ifname))
            continue

        if "cnf_enabled_interfaces" in EXPCONFIG and not ifname in EXPCONFIG["cnf_enabled_interfaces"]:
            if EXPCONFIG["cnf_verbosity"] > 1:
                print(TAG + "Interface is not enabled, skipping {}".format(ifname))
            continue

        # Interface is not up we just skip that one
        if not check_if(ifname):
            if EXPCONFIG["cnf_verbosity"] > 1:
                print(TAG + "Interface is not up {}".format(ifname))
            continue

        EXPCONFIG["cnf_bind_ip"] = get_ip(ifname)

        # Create a process for getting the metadata
        # (could have used a thread as well but this is true multiprocessing)
        meta_info, meta_process = create_meta_process(ifname, EXPCONFIG)
        meta_process.start()

        if EXPCONFIG["cnf_verbosity"] > 1:
            print(TAG + "Running on interface : {}".format(ifname))

        # On these Interfaces we do net get modem information so we hack
        # in the required values by hand whcih will immeditaly terminate
        # metadata loop below
        if (check_if(ifname) and ifname in if_without_metadata):
            add_manual_metadata_information(meta_info, ifname, EXPCONFIG)

        # Try to get metadata
        # if the metadata process dies we retry until the IF_META_GRACE is up
        start_time = time.time()
        while (time.time() - start_time < meta_grace and
               not check_meta(meta_info, meta_grace, EXPCONFIG)):
            if not meta_process.is_alive():
                # This is serious as we will not receive updates
                # The meta_info dict may have been corrupt so recreate that one
                meta_info, meta_process = create_meta_process(ifname,
                                                              EXPCONFIG)
                meta_process.start()
            if EXPCONFIG["cnf_verbosity"] > 1:
                print(TAG + "Trying to get metadata")
            time.sleep(ifup_interval_check)

        # Ok we did not get any information within the grace period
        # we give up on that interface
        if not check_meta(meta_info, meta_grace, EXPCONFIG):
            if EXPCONFIG["cnf_verbosity"] > 1:
                print(TAG + "No metadata continuing")
            continue

        # cmd1=["route","del","default"]
        # #os.system(bashcommand)
        # try:
        #         check_output(cmd1)
        # except CalledProcessError as e:
        #         if e.returncode == 28:
        #                  print("Time limit exceeded for command1")
        # #gw_ip="192.168."+str(meta_info["IPAddress"].split(".")[2])+".1"
        # gw_ip="undefined"
        # print(netifaces.gateways()[netifaces.AF_INET])
        # print(netifaces.gateways())
        # for g in netifaces.gateways()[netifaces.AF_INET]:
        #     if g[1] == ifname:
        #         gw_ip = g[0]
        #         break
        #
        # cmd2=["route", "add", "default", "gw", gw_ip,str(ifname)]
        # try:
        #         check_output(cmd2)
        # except CalledProcessError as e:
        #          if e.returncode == 28:
        #                 print("Time limit exceeded for command2")
        #
        # cmd3=["ip", "route", "get", "8.8.8.8"]
        # try:
        #         output=check_output(cmd3)
        # except CalledProcessError as e:
        #          if e.returncode == 28:
        #                 print("Time limit exceeded for command3")
        # output = output.strip(" \t\r\n\0")
        # output_interface=output.split(" ")[4]
        # if output_interface==str(ifname):
        #         print("Source interface is set to " + str(ifname))

        cfg_counter = 1

        for cfg in get_config_combinations(EXPCONFIG):

            print("\n----------------------------------------------------------")
            print(TAG + "Running configuration " + str(cfg_counter) + " of " + str(EXPCONFIG["summary_number_of_configurations"]) + "...")
            print("----------------------------------------------------------")

            cfg_counter = cfg_counter + 1

            if EXPCONFIG["cnf_verbosity"] > 1:
                print(TAG + "Starting run")

            # Create an experiment process and start it
            start_time_exp=time.time()
            exp_process = create_exp_process(meta_info, cfg, ifname)
            exp_process.start()

            while (time.time() - start_time_exp < exp_grace and
                   exp_process.is_alive()):
                # Here we could add code to handle interfaces going up or down
                # Similar to what exist in the ping experiment
                # However, for now we just abort if we loose the interface

                if not check_if(ifname):
                    if cfg["cnf_verbosity"] > 0:
                        print(TAG + "ERR: Interface went down during run")
                    break
                elapsed_exp = time.time() - start_time_exp
                if cfg["cnf_verbosity"] > 1:
                    print(TAG + "Running Experiment for {} s".format(elapsed_exp))
                time.sleep(ifup_interval_check)

            if exp_process.is_alive():
                exp_process.terminate()
            if meta_process.is_alive():
                meta_process.terminate()

        elapsed = time.time() - start_time
        if EXPCONFIG["cnf_verbosity"] > 1:
            print("\n----------------------------------------------------------")
            print(TAG + "Finished {} after {}".format(ifname, elapsed))
            print("----------------------------------------------------------")
        time.sleep(time_between_runs)

    if EXPCONFIG["cnf_verbosity"] > 1:
        print("\n----------------------------------------------------------")
        print(TAG + "Batch took {}, now exiting".format(time.time() - tot_start_time))
        print("----------------------------------------------------------")
