# OctoPrint-LiveGCodeControl

**Author:** GlitchLab.xyz
**License:** MIT

## Objective
OctoPrint-LiveGCodeControl is an OctoPrint plugin that provides users with powerful real-time G-code stream manipulation capabilities. It allows you to define rules that monitor outgoing G-code commands and automatically intervene by modifying, skipping, or injecting new G-code commands just before they are sent to the printer.

## Core Functional Requirements

### 1. G-code Stream Interception
The plugin intercepts every G-code command line *before* it is sent to the printer. This is achieved by utilizing OctoPrint's `octoprint.comm.protocol.gcode.queuing` hook, which allows for robust modification, suppression, and injection of commands into the G-code queue.

### 2. User-Defined Rules
Users can create and manage a list of rules. Each rule consists of:
*   **Pattern:** A user-defined **regular expression (regex)** to match against the content of outgoing G-code lines. The matching is performed on the full G-code line, including any comments (e.g., `;TYPE:Bridge`, `;LAYER_CHANGE`), as these often contain valuable metadata from slicers.
*   **Action Type:** A selection of what to do if the pattern matches.
*   **Action G-code(s):** User-defined G-code command(s) to be used for certain actions (like inject/replace/modify).

### 3. Supported Action Types
Upon a pattern match, the following actions can be performed:
*   **Modify:** Alters the current G-code command. The user provides the new, complete G-code line.
*   **Skip/Suppress:** Prevents the current G-code command from being sent to the printer.
*   **Inject Before:** Inserts one or more user-defined G-code commands immediately *before* the matched command.
*   **Inject After:** Inserts one or more user-defined G-code commands immediately *after* the matched command.
*   **Replace:** Substitutes the current G-code command with one or more user-defined G-code commands.

## User Interface (Plugin Settings Page)
The plugin provides an interface within OctoPrint's settings for users to:
*   Add new rules.
*   Edit existing rules (pattern, action type, associated G-code).
*   Delete rules.
*   Enable/disable individual rules.
The interface includes input fields for the regex pattern and any G-code commands related to the actions.

## Example Use Case
**Scenario:** You want to change all commands that set the fan to full speed (`M106 S255`) to instead set the fan to half speed (`M106 S128`).
*   **Rule:**
    *   **Pattern:** `M106 S255`
    *   **Action Type:** `Modify`
    *   **Action G-code:** `M106 S128`

This rule will find any G-code line that is exactly `M106 S255` and change it to `M106 S128`. More complex patterns can be used for more flexible matching.

## Installation
1.  Open OctoPrint's settings.
2.  Go to the **Plugin Manager**.
3.  Click on **Get More...**.
4.  Search for "**LiveGCodeControl**" and click **Install**.
Alternatively, you can manually install by pasting the URL of the  [repository archive](https://github.com/VisualBoy/OctoPrint-LiveGCodeControl/archive/master.zip):
```
https://github.com/VisualBoy/OctoPrint-LiveGCodeControl/archive/master.zip
```
into the `...from URL` field in the **Plugin Manager**.

