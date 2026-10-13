# Copyright 2026 IU0NDT
# SPDX-License-Identifier: Apache-2.0
# Source: https://github.com/pof66/netithub-wiresx-linux

# HRI-200 USB inventory for Windows PowerShell 5.1 or later.
# Read-only: queries Plug and Play device properties. Never opens serial,
# audio or HID endpoints and never changes any system configuration.
# Output intentionally excludes full PnP instance IDs and device serial numbers.

[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-SafePnpProperty {
    param(
        [Parameter(Mandatory = $true)][string]$InstanceId,
        [Parameter(Mandatory = $true)][string]$Key
    )

    try {
        $property = Get-PnpDeviceProperty -InstanceId $InstanceId -KeyName $Key -ErrorAction Stop
        if ($null -eq $property -or $null -eq $property.Data) {
            return $null
        }
        return [string]($property.Data -join '; ')
    }
    catch {
        # Some property keys are absent on older Windows versions.
        return $null
    }
}

$devices = @(Get-PnpDevice -PresentOnly -ErrorAction Stop |
    Where-Object { $_.InstanceId -match '(?i)VID_26AA' } |
    Sort-Object Class, FriendlyName)

$reportDevices = @(
    foreach ($device in $devices) {
        $id = [string]$device.InstanceId
        $vid = $null
        $pid = $null
        $mi = $null
        if ($id -match '(?i)VID_([0-9a-f]{4})') { $vid = $Matches[1].ToUpperInvariant() }
        if ($id -match '(?i)PID_([0-9a-f]{4})') { $pid = $Matches[1].ToUpperInvariant() }
        if ($id -match '(?i)MI_([0-9a-f]{2})') { $mi = $Matches[1].ToUpperInvariant() }

        [pscustomobject]@{
            Name           = [string]$device.FriendlyName
            Class          = [string]$device.Class
            Status         = [string]$device.Status
            VendorId       = $vid
            ProductId      = $pid
            Interface      = $mi
            Service        = Get-SafePnpProperty $id 'DEVPKEY_Device_Service'
            DriverName     = Get-SafePnpProperty $id 'DEVPKEY_Device_DriverDesc'
            DriverProvider = Get-SafePnpProperty $id 'DEVPKEY_Device_DriverProvider'
            DriverVersion  = Get-SafePnpProperty $id 'DEVPKEY_Device_DriverVersion'
            DriverInf      = Get-SafePnpProperty $id 'DEVPKEY_Device_DriverInfPath'
            CompatibleIds  = Get-SafePnpProperty $id 'DEVPKEY_Device_CompatibleIds'
        }
    }
)

$report = [pscustomobject]@{
    SchemaVersion = 'hri200-windows-pnp-v1'
    TimestampUtc  = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    Platform      = [Environment]::OSVersion.VersionString
    Count         = $reportDevices.Count
    Devices       = $reportDevices
    Notice        = 'Read-only PnP snapshot. USB session/control protocol not yet verified. Full instance IDs and serial numbers are excluded.'
}

$report | ConvertTo-Json -Depth 5
