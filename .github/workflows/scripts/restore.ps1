Set-StrictMode -Version latest
$ErrorActionPreference = "Stop"
Import-Module "$PSScriptRoot/common.psm1" -Force
$root = Get-Root

foreach($solution in $(Get-Solutions)) {
    Write-Output "Restoring '$solution' using dotnet command line." 

    push-location $(Split-Path $solution -Parent)
        Show-SDKs

        dotnet restore $solution /bl:"$solution.restore.binlog" "/flp1:errorsOnly;logfile=$solution.Errors.log"

        if (! $?) {
            $rawError = $(Get-Content -Raw "$solution.Errors.log")
            Write-Error "Failed to restore NuGet packages for $solution. Error: $rawError"
            pop-location
            throw
        }
    pop-location
}

# Write-Output "Restored Packages: "
# $(get-childitem -Path $root/Ontology.Mappings/packages/ -Directory).FullName
