# chromexup

External extension updater for Chromium based browsers.

## Description

This tool was created due to missing update mechanisms for extensions in privacy-focused variants of Chromium.

A Chromium extension can be installed inline via the Chrome Web Store or distributed [externally](https://developer.chrome.com/apps/external_extensions). An external extension can be set up by providing a preferences file in a pre-defined location, which in turn can contain the local path of the extension and its version.

Linux and macOS versions of Chromium both support loading extensions from *External Extensions* in the Chromium user data directory. The windows version on the other hand does not allow installations of local extensions at all.   

chromexup can manage a set of external extensions per OS user and remove orphaned ones if necessary.


## Installation methods

A list of supported installation methods.

### Arch Linux

1. Use the AUR to install the package [chromexup](https://aur.archlinux.org/packages/chromexup/).
2. Follow the post-installation instructions.

### macOS

1. Install python3 with homebrew.
2. Install chromexup with `python3 setup.py install --optimize=1`.
3. Create the configuration file `~/Library/Application\ Support/chromexup/config.ini` using the template `config.ini.example` and edit it to your liking.
4. For automatic updates enable one of the launchd user agents `scripts/launchd/local.chromexup.{daily,weekly}.plist` by placing it in `~/Library/LaunchAgents` and load it or re-login.
5. Run `chromexup` to verify it is working as intended.
