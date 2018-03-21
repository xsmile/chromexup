#!/usr/bin/env python

"""
External extension updater for Chromium based browsers.
"""

import argparse
import configparser
import glob
import json
import logging
import os
import re
import sys
from multiprocessing.dummy import Pool as ThreadPool
from typing import Any, Dict, Tuple

import requests
from requests.exceptions import RequestException

import chromexup

logger = logging.getLogger(__name__)

# Main settings
WEBSTORE_URL_TPL = 'https://clients2.google.com/service/update2/crx?response=redirect&prodversion=65.0&x=id%3D{}%26installsource%3Dondemand%26uc'
USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.162 Safari/537.36'

# Logging settings
LOGGING_FORMAT = '[%(levelname)s] %(message)s'

cfg: Dict[str, Any] = {}


def process(id: str) -> None:
    """
    Checks if an extension is outdated and updates it if necessary.
    :param id: Extension ID
    :return:
    """
    installed_ver = _get_installed_version(id)
    (latest_ver, url) = _get_latest_version(id)
    is_outdated = installed_ver != latest_ver
    logger.debug('id: %s, installed_ver: %s, latest_ver: %s, is_outdated: %s', id,
                 installed_ver, latest_ver, is_outdated)
    if is_outdated:
        logger.info('updating %s', id)
        ext_data = _download(url)
        _create(id, latest_ver, ext_data)


def _get_installed_version(id: str) -> str:
    """
    Gets the version of the currently installed extension.
    :param id: Extension ID
    :return: Extension version
    """
    try:
        with open(os.path.join(cfg['extdir'], '%s.json' % id), 'r') as f:
            pref_data = json.load(f)
            if 'external_version' not in pref_data:
                raise KeyError
            return pref_data['external_version']
    except FileNotFoundError:
        return '0'


def _get_latest_version(id: str) -> Tuple[str, str]:
    """
    Gets the latest version of the extension from Google.
    :param id: Extension ID
    :return: Tuple of the extension version and the download URL
    """
    # Request URL but do not follow the redirection and do not download the extension
    try:
        r = requests.get(url=WEBSTORE_URL_TPL.format(id), headers={'User-Agent': USER_AGENT},
                         allow_redirects=False)
    except RequestException as e:
        logger.error('failed URL request for extension %s', id)
        logger.debug(e)
        os._exit(1)

    # Extract the version from the download URL
    url = r.next.url
    m = re.search(r'extension_([\d_]+).crx', url)
    if not m:
        logger.error('extension version not found')
        logger.debug(url)
        raise RuntimeError
    version = m.group(1).replace('_', '.')

    return version, url


def _download(url) -> bytearray:
    """
    Downloads an extension and returns its contents.
    :param url: Download URL
    :return: Extension contents
    """
    try:
        r = requests.get(url=url, headers={'User-Agent': USER_AGENT})
    except RequestException as e:
        logger.error('download failed')
        logger.debug(e)
        os._exit(1)

    return r.content


def _create(id: str, version: str, data: bytearray) -> None:
    """
    Creates an extension and the accompanying preferences file in the same directory.
    The preferences file contains a path to the .crx file and a version string.
    :param id: Extension ID
    :param version: Extension version
    :param data: Extension byte array
    :return:
    """
    # Create extension
    ext_name = '%s.crx' % id
    with open(os.path.join(cfg['extdir'], ext_name), 'wb') as f:
        f.write(data)

    # Create preferences file
    pref_name = '%s.json' % id
    pref_data = {'external_crx': ext_name, 'external_version': version}
    with open(os.path.join(cfg['extdir'], pref_name), 'w') as f:
        json.dump(pref_data, f)


def check(cfgfile: str, ext_dir: str) -> None:
    """
    Performs basic checks before updating extensions.
    :return: Success status
    """
    if not os.path.exists(cfgfile):
        logger.error('missing configuration file %s', cfgfile)
        exit(1)
    if not os.path.exists(ext_dir):
        logger.info('creating directory %s', ext_dir)
        os.mkdir(ext_dir, 0o755)


def remove_orphans() -> None:
    """
    Removes extensions and their accompanying preference files not defined in the configuration
    file.
    :return:
    """
    if not cfg['remove_orphans']:
        logger.info('skipping orphan removal')
        return

    # Get IDs of orphaned extensions
    ext_files = glob.glob(os.path.join(cfg['extdir'], '*.crx'))
    ext_files = [os.path.splitext(os.path.basename(e))[0] for e in ext_files]
    orphans = list(set(ext_files) - set(cfg['extensions']))
    if not orphans:
        return

    # Remove orphaned extension and preferences files
    logger.info('removing orphaned extensions: %s', orphans)
    for id in orphans:
        try:
            os.remove(os.path.join(cfg['extdir'], '%s.crx' % id))
            os.remove(os.path.join(cfg['extdir'], '%s.json' % id))
        except FileNotFoundError as e:
            logger.error('file not found while removing extension: %s', id)
            logger.debug(e)


def parse_config(cfgfile: str) -> None:
    """
    Parses the configuration file and performs basic checks.
    :param cfgfile: Configuration file path
    :return: Success status
    """
    global cfg

    sections = ['main', 'extensions']
    parser = configparser.ConfigParser()
    parser.read(cfgfile)

    # Quick section check
    for s in sections:
        if s not in parser:
            logger.error('missing section in configuration file: [%s]', s)
            exit(1)

    # Main section
    cfg['threads'] = parser['main'].getint('threads', 4)
    cfg['remove_orphans'] = parser['main'].getboolean('remove_orphans', False)
    # Extensions section
    cfg['extensions'] = [e for e in parser['extensions'].values()]


def default_config_file() -> str:
    """
    Construct the default path of the configuration file, depending on the operating system.
    :return: Path of the configuration file
    """
    if sys.platform.startswith('linux'):
        result = os.path.join(os.environ['HOME'], '.config')
    elif sys.platform.startswith('darwin'):
        result = os.path.join(os.environ['HOME'], 'Library/Application Support')
    else:
        logger.error('unsupported platform %s', sys.platform)
        raise RuntimeError
    return os.path.join(result, chromexup.__name__, 'config.ini')


def default_extensions_dir() -> str:
    """
    Construct the default path of the extension directory, depending on the operating system.
    :return: Path of the extension directory
    """
    if sys.platform.startswith('linux'):
        result = os.path.join(os.environ['HOME'], '.config/chromium')
    elif sys.platform.startswith('darwin'):
        result = os.path.join(os.environ['HOME'], 'Library/Application Support/Chromium')
    else:
        logger.error('unsupported platform %s', sys.platform)
        raise RuntimeError
    return os.path.join(result, 'External Extensions')


def parse_args() -> argparse.Namespace:
    """
    Parses command line arguments.
    :return: Namespace of the argument parser
    """
    global cfg

    parser = argparse.ArgumentParser(description=chromexup.__description__)
    parser.add_argument('-c', '--cfgfile',
                        help='path of the configuration file',
                        dest='cfgfile', default=default_config_file())
    parser.add_argument('-e', '--extdir',
                        help='directory for external extensions and preferences files',
                        dest='extdir', default=default_extensions_dir())
    parser.add_argument('-v', '--verbose',
                        help='increase output verbosity',
                        action='store_const', dest='loglevel', const=logging.DEBUG,
                        default=logging.INFO)
    parser.add_argument('--version', action='version',
                        version='%s %s' % (chromexup.__name__, chromexup.__version__))
    args = parser.parse_args()

    args.cfgfile = os.path.expandvars(os.path.expanduser(args.cfgfile))
    args.extdir = os.path.expandvars(os.path.expanduser(args.extdir))

    cfg['cfgfile'] = args.cfgfile
    cfg['extdir'] = args.extdir

    return args


def main() -> None:
    """
    Main method.
    :return:
    """
    # Parse command line arguments
    args = parse_args()

    # Initialize logging
    logging.basicConfig(format=LOGGING_FORMAT, level=args.loglevel)

    check(args.cfgfile, args.extdir)

    # Parse configuration file and get extension IDs
    parse_config(args.cfgfile)
    extensions = cfg['extensions']

    # Process extensions
    logger.info('processing %d extensions', len(extensions))
    pool = ThreadPool(cfg['threads'])
    pool.map(process, extensions)
    pool.close()
    pool.join()

    # Remove orphans
    remove_orphans()


if __name__ == '__main__':
    main()
