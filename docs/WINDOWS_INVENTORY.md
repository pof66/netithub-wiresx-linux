# HRI-200 read-only device survey on Windows

## Purpose

Compare the already working Windows hardware configuration with future Linux
USB discovery. This is **not** an attempt to clone USB traffic or log into
WIRES-X services.

The script [tools/windows/hri200_inventory.ps1](../tools/windows/hri200_inventory.ps1)
uses Windows Plug and Play enumeration only. It does not open the COM port,
change DTR/RTS, sample audio, initialize HID devices, alter drivers, restart
WIRES-X, update firmware, or transmit RF.

## One command (after obtaining this repository)

Open Windows PowerShell **without Administrator rights** in the local
repository directory, then run:

```powershell
.\tools\windows\hri200_inventory.ps1
```

The report appears as JSON in the terminal. No output file is created.

If Windows execution policy blocks local scripts, do not change the
machine's policy as part of this diagnostic. The equivalent initial
read-only inventory may be run directly as a one-liner:

```powershell
Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -match 'VID_26AA' } | Select-Object Status,Class,FriendlyName
```

## Output fields

- USB **vendor/product** and **MI interface** IDs, when present.
- PnP name, class, status.
- Installed driver service and version, when exposed.
- Driver INF name and USB-compatible class identifiers.
- A timestamp and Windows OS version.

For privacy, the report intentionally **excludes full PnP instance IDs,
device serial numbers, IPs, station IDs, passwords and traffic data**.

Before sharing any diagnostic reports publicly, check them for sensitive
user-supplied labels.

## Observations already confirmed on one Windows PC

| Field | Value |
| --- | --- |
| Communication device A | PID 0002, Windows COM21 |
| Driver service | usbser |
| Driver description | HRI-200 Communication device A |
| Driver provider | YAESU MUSEN CO., LTD. |
| USB-compatible class | 02 / 02 / 01 (CDC ACM style) |
| USB Audio A (CH1) | PID 0003 / MI 00; Windows service `usbaudio`; PnP status OK |
| USB composite parent | PID 0003; Windows service `usbccgp`; PnP status OK |
| USB input HID | PID 0003 / MI 03; Windows service `HidUsb`; PnP status OK |
| HID-compatible consumer control | PID 0003 / MI 03; PnP status OK; Windows service not returned by this command |

The COM number is host-specific and **must never be hardcoded** in the Linux
program. The full serial command framing and HID semantics are still unknown.


### Additional Windows verification (same date)

Read-only PowerShell queried present devices whose PnP instance identifier contains `VID_26AA&PID_0003`. All four rows reported status `OK`, with service names `usbaudio`, `usbccgp`, `HidUsb`, and an empty service entry for the additional consumer-control HID collection. **An empty service field does not indicate failure**; it may be a logical HID child device rather than a separately serviced USB interface. The command returned no audio streaming data, HID reports, endpoint descriptors, or control framing.

For initial Linux comparison, likely kernel components are `snd-usb-audio`, `usbhid`, and `cdc_acm`. Actual Raspberry Pi binding and end-to-end functionality remain unverified.

## Next verification gate

Once Linux testing hardware is explicitly available, perform sysfs
enumeration with `tools/usb_probe.py` and compare descriptors and
kernel driver bindings. Opening USB/serial endpoints for bidirectional
experiments is a *separate permission gate*, not part of this survey.
