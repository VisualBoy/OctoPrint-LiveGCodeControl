# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin
import logging # Import the logging module
import re # Import the regular expression module
import threading
import time
import math

class LedWorker(threading.Thread):
    def __init__(self, printer, logger):
        super(LedWorker, self).__init__()
        self._printer = printer
        self._logger = logger
        self.daemon = True
        self.running = True
        self.paused = False

        # Configuration
        self.colors = ["#FF0000", "#0000FF"]
        self.mode = "spatial_wave"
        self.speed = 150

        # Internal State
        self.led_count = 30

    def update_config(self, payload):
        if "colors" in payload:
            self.colors = payload["colors"]
        if "mode" in payload:
            self.mode = payload["mode"]
        if "speed" in payload:
            self.speed = payload["speed"]
        self._logger.info(f"LedWorker config updated: {payload}")

    def run(self):
        self._logger.info("LedWorker started")
        while self.running:
            if self.paused:
                time.sleep(1)
                continue

            try:
                is_printing = self._printer.is_printing()

                # Adaptive Frequency
                if is_printing:
                    delay = 0.6 # 600ms Safe Mode
                else:
                    delay = 0.05 # 50ms Idle Mode

                self.process_frame(is_printing)
                time.sleep(delay)

            except Exception as e:
                self._logger.error(f"LedWorker error: {e}")
                time.sleep(1)

    def process_frame(self, is_printing):
        # Bandwidth Safety / Fallback logic
        current_mode = self.mode
        if is_printing and self.mode in ["spatial_wave"]: # Add other spatial modes here
            current_mode = "solid" # Downgrade to global fade/solid

        commands = []

        if current_mode == "solid":
            # Global Fade (Single M150)
            # Assuming first color is primary
            color = self.colors[0] if self.colors else "#FFFFFF"
            r, g, b = self.hex_to_rgb(color)
            commands.append(f"M150 R{r} U{g} B{b}")

        elif current_mode == "spatial_wave":
            # Multiple M150 commands
            # Example wave effect
            t = time.time()
            for i in range(self.led_count):
                phase = (t / (20000.0 / (self.speed or 1))) + (i / 5.0)
                r = int(math.sin(phase) * 127 + 128)
                b = int(math.cos(phase) * 127 + 128)
                commands.append(f"M150 I{i} R{r} U0 B{b}")

        # Inject G-code
        if commands:
             # In a real scenario, you might batch these or send individually
             # OctoPrint's send_cmd doesn't support lists for single command, but self._printer.commands does
             self._printer.commands(commands, tags=set(["suppress_log"]))

    def hex_to_rgb(self, hex_val):
        hex_val = hex_val.lstrip('#')
        lv = len(hex_val)
        return tuple(int(hex_val[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))

    def stop(self):
        self.running = False


class LiveGCodeControlPlugin(octoprint.plugin.SettingsPlugin,
                             octoprint.plugin.AssetPlugin,
                             octoprint.plugin.TemplatePlugin,
                             octoprint.plugin.SimpleApiPlugin):

    def __init__(self):
        # Initialize the logger
        self._logger = logging.getLogger("octoprint.plugins.livegcodecontrol")
        self._logger.info("LiveGCodeControlPlugin: Initializing...")
        self.active_rules = [] # Initialize active_rules
        self.last_matched_rule_pattern = None # Initialize last matched rule pattern
        self.led_worker = None

    def on_after_startup(self):
        self._logger.info("LiveGCodeControlPlugin: Starting LedWorker...")
        self.led_worker = LedWorker(self._printer, self._logger)
        self.led_worker.start()

    ##~~ SimpleApiPlugin mixin

    def on_api_command(self, command, data):
        if command == "update_led_config":
            if self.led_worker:
                 self.led_worker.update_config(data.get('payload', {}))

    def get_api_commands(self):
        return dict(
            update_led_config=["payload"]
        )

    ##~~ SettingsPlugin mixin

    def get_settings_defaults(self):
        return dict(
            rules=[]  # Default empty list for rules
        )

    def on_settings_initialized(self):
        self._logger.info("LiveGCodeControlPlugin: Settings initialized.")
        self.active_rules = self._settings.get(["rules"])
        if self.active_rules is None:
            self.active_rules = []
        self._logger.info(f"LiveGCodeControlPlugin: Loaded {len(self.active_rules)} rules.")

    def on_settings_save(self, data):
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
        self.active_rules = self._settings.get(["rules"])
        if self.active_rules is None:
            self.active_rules = []
        self._logger.info(f"LiveGCodeControlPlugin: Settings saved, {len(self.active_rules)} rules reloaded.")


    ##~~ AssetPlugin mixin

    def get_assets(self):
        # Define your plugin's asset files to automatically include in the
        # core UI here.
        return dict(
            js=["js/livegcodecontrol.js", "js/neoflux_ui.js"],
            css=["css/livegcodecontrol.css", "css/neoflux.css"],
            less=["less/livegcodecontrol.less"]
        )

    ##~~ G-code queuing hook
    def hook_gcode_queuing(self, comm_instance, phase, cmd, cmd_type, gcode, *args, **kwargs):
        if not gcode:  # Check if gcode is None or empty
            return cmd

        # self._logger.info(f"LiveGCodeControlPlugin: Processing G-code: {cmd}") # DEBUG

        for rule in self.active_rules:
            if not rule.get("enabled"):
                continue

            pattern_str = rule.get("pattern")
            if not pattern_str:
                continue

            try:
                regex = re.compile(pattern_str)
                match = regex.search(gcode)

                if match:
                    self._logger.info(f"LiveGCodeControlPlugin: Rule '{pattern_str}' matched G-code: {gcode}")
                    action_type = rule.get("actionType", "").lower()
                    action_gcode_str = rule.get("actionGcode", "")

                    # Split action_gcode_str into individual commands, filtering out empty lines
                    action_gcode_lines = [line for line in action_gcode_str.splitlines() if line.strip()]

                    self._logger.info(f"LiveGCodeControlPlugin: Action '{action_type}' with G-code(s): {action_gcode_lines}")

                    # Store the pattern of the matched rule
                    self.last_matched_rule_pattern = pattern_str

                    if action_type == "skip" or action_type == "skip/suppress":
                        self._logger.info(f"LiveGCodeControlPlugin: Suppressing G-code: {gcode}")
                        return None  # Suppress the command

                    elif action_type == "inject_before":
                        commands_to_send = action_gcode_lines + [cmd]
                        self._logger.info(f"LiveGCodeControlPlugin: Injecting before, sending: {commands_to_send}")
                        return commands_to_send

                    elif action_type == "inject_after":
                        commands_to_send = [cmd] + action_gcode_lines
                        self._logger.info(f"LiveGCodeControlPlugin: Injecting after, sending: {commands_to_send}")
                        return commands_to_send

                    elif action_type == "replace" or action_type == "modify": # Modify treated as Replace for now
                        if not action_gcode_lines: # If action G-code is empty, effectively skip
                            self._logger.info(f"LiveGCodeControlPlugin: Replacing with empty, effectively suppressing G-code: {gcode}")
                            return None
                        self._logger.info(f"LiveGCodeControlPlugin: Replacing G-code '{gcode}' with: {action_gcode_lines}")
                        return action_gcode_lines

                    else:
                        self._logger.warning(f"LiveGCodeControlPlugin: Unknown action type '{action_type}' for rule '{pattern_str}'. Passing original command.")
                        # Even if action is unknown, a rule matched. Storing its pattern.
                        # self.last_matched_rule_pattern is already set above.
                        return cmd

                    # If a rule matched and an action was taken (or attempted), stop processing further rules for this G-code line.
                    # The return statements above handle this for specific actions.
                    # If an unknown action type occurs, we fall through and return original cmd, but ideally, we should break here too.
                    # However, since all known actions return, this break is implicitly handled for them.
                    # break # This break is now effectively handled by returns in each action block

            except re.error as e:
                self._logger.error(f"LiveGCodeControlPlugin: Invalid regex pattern '{pattern_str}': {e}")
            except Exception as e_gen:
                self._logger.error(f"LiveGCodeControlPlugin: Error processing rule '{pattern_str}' for G-code '{gcode}': {e_gen}")

        return cmd # Return the original command if no rules matched or no action taken


    ##~~ Softwareupdate hook

    def get_update_information(self):
        # Define the configuration for your plugin to use with the Software Update
        # Plugin here. See https://docs.octoprint.org/en/master/bundledplugins/softwareupdate.html
        # for details.
        return dict(
            livegcodecontrol=dict(
                displayName="OctoPrint-LiveGCodeControl", # Updated display name
                displayVersion=self._plugin_version,

                # version check: github repository
                type="github_release",
                user="VisualBoy", # Update with your GitHub username
                repo="OctoPrint-LiveGCodeControl",
                current=self._plugin_version,

                # update method: pip
                pip="https://github.com/VisualBoy/OctoPrint-LiveGCodeControl/archive/{target_version}.zip"
            )
        )

# Plugin registration
__plugin_name__ = "OctoPrint-LiveGCodeControl"
__plugin_version__ = "0.1.0"
__plugin_description__ = "A plugin for real-time G-code stream manipulation based on user-defined rules."
__plugin_pythoncompat__ = ">=3,<4" # Python 3 compatibility


def __plugin_load__():
    global __plugin_implementation__
    plugin = LiveGCodeControlPlugin()
    __plugin_implementation__ = plugin

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.comm.protocol.gcode.queuing": __plugin_implementation__.hook_gcode_queuing,
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
        "octoprint.plugin.settings.initialized": __plugin_implementation__.on_settings_initialized # Add this hook
    }
