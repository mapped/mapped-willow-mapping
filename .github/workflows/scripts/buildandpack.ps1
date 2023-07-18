param (
    [Parameter(Mandatory)]
    [string]$nugetSecret,

    [Parameter(Mandatory)]
    [string]$VERTUPLE,

    [Parameter(Mandatory)]
    [string]$githubRepo,

    [Parameter(Mandatory)]
    [string]$githubBranch,

    [Parameter(Mandatory)]
    [string]$githubCommit,

    [Parameter(Mandatory)]
    [string]$buildNumber
    )

Set-StrictMode -Version latest
$ErrorActionPreference = "Stop"
Import-Module "$PSScriptRoot/common.psm1" -Force

foreach($solution in $(Get-Solutions)) {
    Write-Output "Building '$solution' using dotnet command line." 

    $rootPath =  $(Split-Path $solution -Parent)

    push-location $rootPath
        Show-SDKs


        dotnet pack $solution --include-source --include-symbols --version-suffix $buildNumber --no-restore -c Release /bl:"$solution.build.binlog" "/flp1:errorsOnly;logfile=$solution.Errors.log" -p:Version=$VERTUPLE -p:AssemblyVersion=$VERTUPLE -p:FileVersion=$VERTUPLE -p:RepositoryUrl=https://github.com/$githubRepo -p:RepositoryType=git -p:RepositoryBranch=$githubBranch -p:RepositoryCommit=$githubCommit
        if (! $?) {
            $rawError = $(Get-Content -Raw "$solution.Errors.log")
            Write-Error "Failed to build $solution. Error: $rawError"
            pop-location
            throw
        }

        dotnet nuget push **/*.nupkg --skip-duplicate 
        dotnet nuget push **/*.nupkg --skip-duplicate --source https://api.nuget.org/v3/index.json --api-key $nugetSecret

        pop-location
}
