Set-StrictMode -Version latest
$ErrorActionPreference = "Stop"
$root = Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent

function Get-Root {
    return $root
}

function Get-Solutions {
    $list = @(Get-ChildItem $root -File -Recurse -Include *.sln | Foreach-Object { $_.FullName } )
    return $list
}

function Show-SDKs {
    Write-Output "-------------- +SDK INFO ---------------"

    Write-Output "Global.json contents:"
    Get-Content $root/Ontologies.Mappings/global.json
    Write-Output "Installed SDK versions:"
    dotnet --list-sdks
    Write-Output "Active SDK Version:"
    dotnet --version
    Write-Output "Active MSBuild Version:"
    dotnet msbuild -version
    Write-Output "Active Powershell Version:"
    Write-Output $PSVersionTable

    Write-Output "-------------- -SDK INFO ---------------"
}
