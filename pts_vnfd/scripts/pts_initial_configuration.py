#!/usr/bin/env python

import argparse
import logging
import os
import subprocess
import sys
import time
from svapiclient  import client 
from svapisession import session 
import yaml
import re

def get_vnfr(yaml_cfg,name):
    for index, vnfr in yaml_cfg['vnfr'].items():
        if name in vnfr['name']:
            return vnfr
    return None

def configure(yaml_cfg,logger):
    pts_name = yaml_cfg['vnfr_name']
    pts_vnfr = get_vnfr(yaml_cfg,pts_name)
    tse_vnfr = get_vnfr(yaml_cfg,'Traffic Steering')

    if pts_vnfr is None:
        logger.info("NO vnfr record found")
        sys.exit(1)

    logger.debug("PTS YAML: {}".format(pts_vnfr))

    pts_sess=session.Session(pts_vnfr['mgmt_ip_address'])
    tse_sess=session.Session(tse_vnfr['mgmt_ip_address'])

    if not pts_sess.wait_for_api_ready():
        logger.info("PTS API did not become ready")
        sys.exit(1)

    if not tse_sess.wait_for_api_ready():
        logger.info("TSE API did not become ready")
        sys.exit(1)

    pts_cli = client.Client(pts_sess)
    tse_cli = client.Client(tse_sess)
    
    # get the pts mac address
    mac=pts_cli.get_interface_mac('1-3')

    #need a name without spaces
    cli_pts_name = '_'.join(pts_name.split())

    tse_sess.add_cmd('add config traffic-steering service-locator mac-nsh-locator ' +  cli_pts_name + ' mac ' + mac )
    tse_sess.add_cmd('add config traffic-steering service-function ' + cli_pts_name + ' transport mac-nsh locator ' + cli_pts_name )
    tse_sess.add_cmd('add config traffic-steering service-group-member ' + cli_pts_name + ' service-group pts-group' )
    tse_sess.commit()

def main(argv=sys.argv[1:]):
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("yaml_cfg_file", type=argparse.FileType('r'))
        parser.add_argument("-q", "--quiet", dest="verbose", action="store_false")
        parser.add_argument("-r", "--rundir", dest='run_dir', action='store')
        args = parser.parse_args()

        yaml_str = args.yaml_cfg_file.read()
        yaml_cfg = yaml.load(yaml_str)

        run_dir = args.run_dir
        if not run_dir:
            run_dir = os.path.join(os.environ['RIFT_INSTALL'], "var/run/rift")
            if not os.path.exists(run_dir):
                os.makedirs(run_dir)
        log_file = "{}/initial-configuration-{}-{}.log".format(run_dir, yaml_cfg['vnfr_name'], time.strftime("%Y%m%d%H%M%S"))
        logging.basicConfig(filename=log_file, level=logging.DEBUG)
        logger = logging.getLogger()

    except Exception as e:
        print("Exception in {}: {}".format(__file__, e))
        sys.exit(1)

    try:
        ch = logging.StreamHandler()
        if args.verbose:
            ch.setLevel(logging.DEBUG)
        else:
            ch.setLevel(logging.INFO)

        # create formatter and add it to the handlers
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    except Exception as e:
        logger.exception(e)
        raise e

    try:
        logger.debug("Input YAML: {}".format(yaml_cfg))
        configure(yaml_cfg,logger)

    except Exception as e:
        logger.exception(e)
        raise e

if __name__ == "__main__":
    main()
