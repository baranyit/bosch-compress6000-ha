# Open decisions and questions

1. **Standard catalog points** (graded 2026-11-09, only `system_pressure` and `heating_manual_setpoint` are absent here) (starts, pressure, power setpoint, DHW mode/levels, manual setpoint,
   outputProduced): confirm paths, units and `writeable` on the first read-only run.
2. **Extra hot water semantics**: does `charge = start` run one charge to the target and stop by
   itself? Does `stop` while idle do anything? The write format is hardware-checked; the physical effect and run time are still open.
3. **Operation mode values** (`allowedValues`) differ by installation; the select uses what the
   gateway reports.
4. **Recording unit**: kWh is plausible (heat output about 4.5 × compressor on 2026-11-09), still not documented by the vendor. If it is Wh, change the sensor unit/scale *and* migrate the
   statistics together; do not change it silently.
5. **Back-fill** of hours missed during the cut-over: out of scope until requested.
6. **Dynamic entities**: entities for points that appear later need an integration reload.
7. **Second heating circuit / multiple DHW circuits**: only `hc1` and `dhw1` are in the catalog.
8. **HACS repository name** and public/private status (the HACS action runs only on public repos).
