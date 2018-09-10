# chromexup

External extension updater for Chromium based browsers.

## Description

This tool was created due to missing update mechanisms for extensions in privacy-focused variants of Chromium.

Chromium extensions can be installed inline via the Chrome Web Store or deployed automatically from an [external](https://developer.chrome.com/apps/external_extensions) location. An external extension is set up by referencing its local path and version in a location hard-coded in the browser.

Linux and macOS versions of Chromium both support loading extensions from the *External Extensions* directory in the Chromium user data folder. The windows version on the other hand supports loading extensions referenced by a static registry key. While the first case supports different sets of extensions for each Chromium user data folder, the second does not and only allows a single set for an OS user.

chromexup uses configuration files to keep different sets of extensions updated and remove orphaned ones, if necessary.

Extensions can be updated automatically by using the various automation scripts.

To avoid different kinds of issues, extensions should be installed and removed by using this tool only.

## F.A.Q.

#### An extension was removed manually via chrome://extensions and does not reappear after trying to install it again with chromexup.
The extension was blacklisted by the browser. To remove it from the blacklist, it needs to be installed by dropping the .crx file in the `chrome://extensions` page (make sure that Developer Mode is enabled) and uninstalled again.

## Installation Instructions

1. Install python3 using a package manager of your choice and add the install directory to `PATH`.
2. Install chromexup with `python3 setup.py install --optimize=1`.
3. Create the configuration file `<APP_DATA>/chromexup/config.ini` using the [template](config.ini.example) and edit it to your liking. Depending on the OS, the path for `<APP_DATA>` is as follows:
    - Linux: `~/.config`
    - macOS: `~/Library/Application\ Support`
    - Windows: `%AppData%`
4. Repeat step 3. with a differently named configuration file for another browser variant if needed.
5. Run `chromexup` to verify the tool is working as intended.
6. Set up automatic updates if necessary (see next section).

### Automatic Updates

Automation scripts for different operating systems are located in the [scripts](scripts) directory.

#### Linux (systemd)
- Copy the service `chromexup.service` and one of the timers `chromexup-{daily,weekly}.timer` to `~/.config/systemd/user`.
- Enable the timer with `systemctl --user enable <TIMER>`.

#### macOS (launchd)
- Copy one of the launchd user agents `local.chromexup.{daily,weekly}.plist` to `~/Library/LaunchAgents`.
- Load the user agent or re-login.

#### Windows (taskschd)
- Run one of the batch files `chromexup-{daily,weekly}.bat` to create a new update task.
