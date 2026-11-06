# Heating - boiler control by room weights

One **automation blueprint** (`heating_control.yaml`), configured entirely in the GUI. A boiler (for example a Viessmann) is switched by a single on/off relay. The decision is based on a **weighted demand**: every room contributes `weight × deficit`, where `deficit = max(0, target − current temperature)` in K.

Target version: Home Assistant 2026.10. The blueprint needs no YAML packages and no generated files.

## Installation

1. Copy `blueprints/automation/petr1h/heating_control.yaml` to `config/blueprints/automation/petr1h/` (or use Settings → Automations & scenes → Blueprints → Import if you publish it).
2. Optional helper entities (mode, heating season, status text, demand for a graph, temporary override): `helpers/heating_helpers.yaml` into `config/packages/` (or create the same helpers in the GUI). Restart HA after adding them.
3. **Settings → Automations & scenes → Blueprints → "Heating - boiler control by room weights" → Create automation.**
4. Fill in the **Boiler relay** (the only required value) and, in the **Rooms** section, the **TRVs** of every room. Add rooms with the add button below the list and remove them in the item menu (see below). A room without a TRV is ignored. Everything else is optional and can be added later by editing the automation.
5. Turn on `input_boolean.heating_season` (if you use it, it is off after creation, so the boiler stays off).

### Sections of the blueprint (collapsed)

| Section | Contents |
|---|---|
| Boiler | relay, heating season, mode / preset (none, away, comfort, eco, home, sleep, work from home, vacation), schedule |
| Thresholds, timing and protections | on / off threshold, minimum on / off time, minimum number of open valves, frost-protection start, failure behavior |
| Target temperatures per preset | comfort, eco, home, sleep, away, work from home, frost (defaults for all rooms) |
| Demand and sensors | deadband, deficit cap, stale data timeout |
| TRV control | setpoint tolerance, forcing `heat` mode, sending the external temperature to Z2M |
| Temporary manual override | state helper, watched TRVs, duration (default 60 min) |
| ViCare feedback and alerts | burner entity (read-only), delay, custom alert action (e.g. `notify`) |
| Outputs and debugging | status text and demand number helpers, logbook, detailed log |
| Rooms | any number of rooms (add / remove): name, TRVs (several allowed), external sensor, temperature source, **weight**, target shift, sensor correction, window contact, "always heat", **own temperature for every preset** |

### Adding and removing rooms

A blueprint cannot have its own "Add room" button or create inputs dynamically. The rooms are therefore one input of type `object` (a list of items); its GUI editor has a button to add an item and a menu to remove one. The number of rooms is not limited. Save the automation to apply the change. The list is empty after you create the automation.

- Optional fields you leave empty use defaults: source = TRV, weight = 5, shift = 0, correction = 0, always heat = off.
- If you do not use the item editor, the list can be edited in the automation YAML (`use_blueprint → input → rooms`): `- {name: Living room, trvs: [climate.living_room], weight: 8}`.

## Presets and temperatures per room

The preset is selected in an `input_select` (the **Mode / preset** field, helper `heating_mode`). Recognised options (case-insensitive, `_` and `-` count as a space): `none`, `away`, `comfort`, `eco`, `home`, `sleep` (also `night`), `work from home` (also `work_from_home`, `wfh`) and `vacation`. Any other value counts as `none`.

| Preset | Room target |
|---|---|
| none | schedule: on = comfort, off = eco (no schedule = comfort) |
| comfort / eco / home / work from home | the respective temperature |
| sleep | sleep temperature (comfort for a room with "always heat") |
| away | away temperature |
| vacation | frost |

Every preset has a **global temperature** (section Target temperatures per preset), and every room can have its **own temperature** (`t_away`, `t_comfort`, `t_eco`, `t_home`, `t_sleep`, `t_work`). A room temperature is used exactly as entered (the target shift is not added). If it is empty, the global temperature plus the target shift applies. An open window and vacation always give the frost temperature.

Example: `work from home` with `t_work: 21` for the office and `t_work: 20` for the living room sets the office to 21 and the living room to 20; the other rooms get the global work from home temperature.

The preset `home` has a fixed temperature and is not driven by the schedule (the schedule applies only to `none`).

## Temporary manual override (knob turn)

When you turn the knob on a TRV, the new temperature is kept for **60 minutes** (configurable, 15 to 240 min) and neither the schedule nor the preset overwrites it. It is implemented entirely in Home Assistant; the TRV's built-in temporary mode is not used. If the field **Override state helper** is empty, the feature is off and a manual change is overwritten as before.

### Setup

1. Create the helpers from `helpers/heating_helpers.yaml`: `input_text.heating_override_store` (max 255) and optionally `input_number.heating_override_duration`.
2. In the section **Temporary manual override** select the state helper, **all TRVs** whose changes should be detected (the list has to be entered again, because automation triggers cannot take their entities from the room list) and optionally the duration helper.

### Behavior

| Situation | Result |
|---|---|
| Knob turned to a temperature other than the target | Temporary override of this TRV with the new temperature, valid for the full duration from the turn |
| Another knob turn during an override | New temperature and the **full duration restarts** |
| Schedule, preset or shift changes during an override | The TRV keeps the manual temperature |
| Duration expires | The override ends, the **current normal target is evaluated** and written to the TRV (the old target is not restored). Happens at the next run, i.e. within 1 min |
| Knob turned back to the normal target during an override | The override is cancelled |
| Open window or vacation preset | Takes precedence: target is frost, the override is ignored (its time keeps running and it continues after the window closes) |
| HA restart | The expiry is stored as an absolute time, the override continues and the timer is not started again. An override that has already expired returns to normal control immediately |
| Several TRVs | Every TRV has its own override. The room demand uses the average of the targets of its TRVs |

The tolerance for "same as the normal target" is the **Setpoint tolerance** (default 0.4 °C). Keep it below the TRV step (0.5 °C), otherwise a 0.5 °C change is not detected.

### How a knob turn is told apart from a write by HA

After every target change (also one written by HA) the TRV reports the new target and the automation runs. Two cases are distinguished:

1. **Before every write** the automation notes in the state helper "I wrote temperature T to TRV X". When the TRV then reports T, it is the confirmation of our own write: the note is consumed and nothing happens. A TRV can have several notes (write 21, shortly after write 20, the TRV wakes up and reports 21 and then 20), so a late report does no harm. A note is valid for 10 min and is then forgotten (TRV out of reach).
2. **A temperature that HA did not write** and that differs from the normal target (by more than the tolerance) is a knob turn. Comparing with the schedule alone would not be enough, which is why the writes are recorded.

The state helper has the form `number_of_TRVs|overrides|writes`, where an override is `index,temperature×10,expiry in epoch minutes` and the index is the position of the TRV in the watched list. If the **number** of watched TRVs changes, the stored state is discarded. If TRVs are reordered while an override is active, the override may be assigned to another TRV until it expires, so only append to the list during operation.

### Adding another TRV

1. Add the TRV to its room in the **Rooms** section.
2. Add it to the list **TRVs watched for manual changes** as well (preferably at the end).
3. Save the automation. Because the number of watched TRVs changed, the stored state is discarded once and any running override ends.

### Test scenarios (in HA, automation trace)

1. Normal schedule change: the target is written, the TRV confirms it, no "manual change" in the logbook.
2. Turn the knob: the logbook shows "Manual change on climate.x" and the `input_text` contains an entry.
3. Turn it again 30 min later: the expiry moves by the full duration.
4. Change the schedule during an override: the TRV keeps the manual temperature.
5. After expiry: the current normal target is written to the TRV.
6. Restart HA during an override: the override continues until its original end.
7. A write from HA followed by a late TRV report: nothing is created.

## How it decides

| Topic | Decision |
|---|---|
| Formula | `demand = Σ weight × min(deficit, cap)` over rooms with a deficit ≥ deadband. One unimportant room alone does not start the boiler. |
| Threshold | A room with weight `w` alone starts the boiler at a deficit of `threshold / w` (threshold 6: weight 8 → 0.75 K, weight 2 → 3 K). Weight 0 = the room never starts the boiler. |
| Hysteresis | Switch on at demand ≥ 6, off at ≤ 2 (defaults). |
| Relay protection | Minimum on and off time 10 min and at least 1 open valve (`hvac_action = heating`). |
| Frost | A room below the frost temperature forces a start (with the minimum times and open valves). |
| Failure | Unavailable relay or no room → relay "off" (or "keep") + alert. |
| Temperature source | The selected source (TRV / external); if it is unavailable or stale, automatically the other one. A room without a valid temperature is not counted in the demand and is reported. |
| Target | By preset (see above). Vacation and an open window: frost. The target never drops below frost. |

The automation runs every minute, on relay changes and (with the temporary override enabled) on every target report from a TRV; runs are queued (`mode: queued`). Commands are sent to the TRVs only when the target differs, not periodically.

## Temperature source and TRV-ZBT (verified in the Z2M documentation)

- Z2M exposes `external_temperature_input` (0–99.9 °C) and `temperature_sensor_select` (`local_temperature` / `remote_temperature` / `remote_source_offline`). The external value must be synchronised by HA. The blueprint sends it through `mqtt.publish` (option "Send external temperature to the TRVs", off by default, interval 5 min, only for rooms with an external sensor).
- The Z2M device name (friendly name) is taken from the device name of the climate entity. If it is renamed in HA, the MQTT commands will not work.
- The TRV-ZBT has no `preset`. The `auto` mode would start its own weekly program, so the blueprint forces `heat` by default.
- A manual temperature change on a TRV is kept for the configured duration when the temporary override is enabled; otherwise it is overwritten at the next difference from the target.
- The TRV behavior when HA/MQTT is down (`remote_source_offline`) is not described in the documentation; verify it on one unit.

## Dashboard

`helpers/heating_dashboard.yaml` is a simple dashboard (mode, season, relay, status and reason, demand). The blueprint does not expose individual rooms as entities (a blueprint cannot create sensors). Per-room details are in the automation trace (Settings → Automations → Traces) and, with "Detailed log every minute" on, in the HA log.

## Test plan

1. Create an automation with only the relay and one room. Run it manually and open **Traces**: `room_data` shows the temperature, target, deficit and demand.
2. Lower the room target (target shift) or cool the room in a test. A low-weight room alone: `decision: off`, reason "below the on threshold". High weight: the boiler turns on and the logbook has an entry with the reason.
3. Right after switching on, lower the demand: the relay stays on until the minimum on time passes.
4. Disconnect the relay: the alert "Boiler relay unavailable" after the delay.
5. Fill in the ViCare burner entity: with the relay on and the burner not running for longer than the delay, an alert is sent.

## Not verified and open points

- **The blueprint has not been loaded in a real HA.** This also applies to the room list editor (`object` selector with `fields`, `multiple`, `label_field`): verify the GUI behavior when you first open it. The template logic was verified offline, the blueprint schema against HA's only by hand (header, sections, input names). When you first create the automation, watch `Settings → System → Logs`.
- **Relay fail-safe when HA is down**: undecided, depends on the relay settings (default state after losing connection / power, NO/NC).
- Temporary manual override: a `state` trigger with an empty TRV list (the default, feature off) and with `attribute: temperature` was not verified in HA. If HA rejects the empty list, select at least one TRV. The wake-up delay of battery TRV-ZBT reports is handled by the 10-minute record of writes; verify the real delay in operation.
- Unknown: ViCare entities (burner), the boiler's own program, which rooms should "always heat", window contacts, external sensors.
- Weights are changed by editing the automation (not at runtime from a dashboard). A manual temperature override with a timer is implemented only for TRV knob turns; window detection from a temperature drop is not implemented. A window contact is supported.
