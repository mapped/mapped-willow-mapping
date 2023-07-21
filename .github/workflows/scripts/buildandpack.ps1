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
    [string]$buildNumber,

    [Parameter(Mandatory)]
    [string]$publishPackage
    )

Set-StrictMode -Version latest
$ErrorActionPreference = "Stop"
Import-Module "$PSScriptRoot/common.psm1" -Force

foreach($solution in $(Get-Solutions)) {
    Write-Output "Building '$solution' using dotnet command line." 

    $rootPath =  $(Split-Path $solution -Parent)

    push-location $rootPath
        Show-SDKs


        dotnet pack $solution --include-source --include-symbols --version-suffix $buildNumber --no-restore -p:Version=$VERTUPLE -p:AssemblyVersion=$VERTUPLE -p:FileVersion=$VERTUPLE -p:RepositoryUrl=https://github.com/$githubRepo -p:RepositoryType=git -p:RepositoryBranch=$githubBranch -p:RepositoryCommit=$githubCommit -c Release
        if (! $?) {
            $rawError = $(Get-Content -Raw "$solution.Errors.log")
            Write-Error "Failed to build $solution. Error: $rawError"
            pop-location
            throw
        }

        if ($publishPackage -eq 'True') {
            # Write-Output "Pushing Package to GitHub Package Repository using dotnet command line." 
            # dotnet nuget push **/*.nupkg --skip-duplicate 
            
            Write-Output $nugetSecret | sed 's/./& /g'
            
            Write-Output "Pushing Package to Nuget Package Repository using dotnet command line." 
            dotnet nuget push **/*.nupkg --skip-duplicate --source https://api.nuget.org/v3/index.json --api-key "$nugetSecret"
        }

        pop-location
}
