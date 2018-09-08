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
from typing import Any, Dict, List, Tuple

import requests
from requests.exceptions import RequestException

import chromexup

if sys.platform.startswith('win32'):
    import winreg

logger = logging.getLogger(__name__)

# Main settings
WEBSTORE_URL_TPL = 'https://clients2.google.com/service/update2/crx?response=redirect&prodversion=65.0&x=id%3D{}%26installsource%3Dondemand%26uc'
USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36'

# Logging settings
LOGGING_FORMAT = '[%(levelname)s] %(message)s'

if sys.platform.startswith('win32'):
    HKEY_ROOT = winreg.HKEY_CURRENT_USER
    EXT_KEY = 'Software\\Google\\Chrome\\Extensions'

cfg: Dict[str, Any] = None


def process(id: str) -> None:
    """
    Checks if an extension is outdated and updates it if necessary.
    :param id: Extension ID
    :return:
    """
    installed_ver = _get_installed_version(id)
    try:
        (latest_ver, url) = _get_latest_version(id)
    except FileNotFoundError:
        return

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
    if sys.platform.startswith('linux') or sys.platform.startswith('darwin'):
        try:
            # Get version from preferences file
            with open(os.path.join(cfg['extdir'], '%s.json' % id), 'r') as f:
                pref_data = json.load(f)
                if 'external_version' not in pref_data:
                    raise KeyError
                return pref_data['external_version']
        except FileNotFoundError:
            return '0'
    elif sys.platform.startswith('win32'):
        try:
            # Get version from registry value
            with winreg.OpenKey(HKEY_ROOT, EXT_KEY + '\\' + id) as key:
                version = winreg.QueryValueEx(key, 'version')[0]
                return version
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

    if r.status_code == 204:
        # Extension was probably removed from the Chrome Web Store
        logger.warning('extension is not downloadable %s', id)
        raise FileNotFoundError

    # Extract the version from the download URL
    url = r.next.url
    m = re.search(r'extension_([\d_]+).crx', url)
    if not m:
        logger.error('extension version not found')
        logger.debug(url)
        raise RuntimeError
    version = m.group(1).replace('_', '.')

    return version, url


def _download(url: str) -> bytearray:
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

    if sys.platform.startswith('linux') or sys.platform.startswith('darwin'):
        # Create preferences file
        pref_name = '%s.json' % id
        pref_data = {'external_crx': ext_name, 'external_version': version}
        with open(os.path.join(cfg['extdir'], pref_name), 'w') as f:
            json.dump(pref_data, f)
    elif sys.platform.startswith('win32'):
        # Create registry key
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, EXT_KEY + '\\' + id) as key:
            winreg.SetValueEx(key, 'path', 0, winreg.REG_SZ, os.path.join(cfg['extdir'], ext_name))
            winreg.SetValueEx(key, 'version', 0, winreg.REG_SZ, version)


def _config_dir() -> str:
    """
    Constructs the path of the configuration directory, depending on the operating system.
    :return: Path of the configuration directory
    """
    if sys.platform.startswith('linux'):
        result = os.path.join(os.environ['HOME'], '.config')
    elif sys.platform.startswith('darwin'):
        result = os.path.join(os.environ['HOME'], 'Library/Application Support')
    elif sys.platform.startswith('win32'):
        result = os.path.join(os.environ['AppData'])
    else:
        logger.error('unsupported platform %s', sys.platform)
        raise RuntimeError
    return os.path.join(result, chromexup.__name__)


def _extensions_dir(branding: str) -> str:
    """
    Constructs the path of the extension directory, depending on the operating system.
    :return: Path of the extension directory
    """
    if sys.platform.startswith('linux'):
        result = os.path.join(os.environ['HOME'], '.config', branding)
    elif sys.platform.startswith('darwin'):
        branding = branding.title()
        result = os.path.join(os.environ['HOME'], 'Library/Application Support', branding)
    elif sys.platform.startswith('win32'):
        # Windows does not load extensions from the 'External Extensions' directory,
        # store them in %AppData% instead
        result = os.path.join(os.environ['AppData'], chromexup.__name__)
    else:
        logger.error('unsupported platform %s', sys.platform)
        raise RuntimeError
    return os.path.join(result, 'External Extensions')


def check(cfgfile: str, ext_dir: str) -> None:
    """
    Performs basic checks before updating extensions.
    :param cfgfile: Configuration file path
    :param ext_dir: Extension directory
    :return:
    """
    # Check configuration file
    if not os.path.exists(cfgfile):
        logger.error('missing configuration file %s', cfgfile)
        exit(1)

    # Check browser user data directory
    user_data_dir = os.path.dirname(ext_dir)
    if not os.path.exists(user_data_dir):
        logger.error('missing browser user data directory %s', user_data_dir)
        exit(1)
    # Create 'External Extensions' directory if necessary
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

    logger.info('removing orphans: %s', orphans)

    if sys.platform.startswith('linux') or sys.platform.startswith('darwin'):
        for id in orphans:
            try:
                # Remove orphaned extension and preferences file
                os.remove(os.path.join(cfg['extdir'], '%s.crx' % id))
                os.remove(os.path.join(cfg['extdir'], '%s.json' % id))
            except FileNotFoundError as e:
                logger.error('file not found while removing extension %s', id)
                logger.debug(e)
    elif sys.platform.startswith('win32'):
        for id in orphans:
            try:
                # Remove orphaned extension and registry keys
                os.remove(os.path.join(cfg['extdir'], '%s.crx' % id))
                winreg.DeleteKey(HKEY_ROOT, EXT_KEY + '\\' + id)
            except FileNotFoundError as e:
                logger.error('file not found while removing extension %s', id)
                logger.debug(e)


def parse_config(cfgfile: str) -> Dict[str, Any]:
    """
    Performs basic checks and parses the configuration file.
    :param cfgfile: Configuration file path
    :return Dictionary containing the configuration options
    """

    sections = ['main', 'extensions']
    parser = configparser.ConfigParser()
    parser.read(cfgfile)

    # Quick section check
    for s in sections:
        if s not in parser:
            logger.error('missing section in configuration file: [%s]', s)
            exit(1)

    cfg = {
        # Main section
        'branding': parser['main'].get('branding', 'chromium'),
        'threads': parser['main'].getint('threads', 4),
        'remove_orphans': parser['main'].getboolean('remove_orphans', False),
        # Extensions section
        'extensions': [e for e in parser['extensions'].values()]
    }
    # Set extension directory
    cfg['extdir'] = _extensions_dir(cfg['branding'])

    return cfg


def parse_args() -> argparse.Namespace:
    """
    Parses command line arguments.
    :return: Namespace of the argument parser
    """
    global cfg

    parser = argparse.ArgumentParser(description=chromexup.__description__)
    parser.add_argument('-v', '--verbose',
                        help='increase output verbosity',
                        action='store_const', dest='loglevel', const=logging.DEBUG,
                        default=logging.INFO)
    parser.add_argument('--version', action='version',
                        version='%s %s' % (chromexup.__name__, chromexup.__version__))
    args = parser.parse_args()

    return args


def get_cfgfiles() -> List[str]:
    result = glob.glob(os.path.join(_config_dir(), '*.ini'))
    logger.debug('found %d configuration file(s): %s', len(result), result)
    return result


def main() -> None:
    """
    Main method.
    :return:
    """
    global cfg

    # Parse command line arguments
    args = parse_args()

    # Initialize logging
    logging.basicConfig(format=LOGGING_FORMAT, level=args.loglevel)

    # Parse all configuration files
    cfgfiles = get_cfgfiles()
    for cfgfile in cfgfiles:
        cfg = parse_config(cfgfile)

        # Check configuration
        check(cfgfile, cfg['extdir'])

        # Process extensions
        extensions = cfg['extensions']
        logger.info('%s, processing %d extension(s)', os.path.basename(cfgfile), len(extensions))
        pool = ThreadPool(cfg['threads'])
        pool.map(process, extensions)
        pool.close()
        pool.join()

        # Remove orphans
        remove_orphans()


if __name__ == '__main__':
    main()
