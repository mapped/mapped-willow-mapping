param (
    [Parameter(Mandatory)]
    [string]$nugetSecret,

    [Parameter(Mandatory)]
    [string]$config,

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

Show-SDKs

foreach($solution in $(Get-Solutions)) {
    $rootPath =  $(Split-Path $solution -Parent)

    Write-Output "-------------- $solution ---------------"

    push-location $rootPath

    # dotnet pack ignores version details, so we have to build first, then pack with 'no-build'
    Write-Output "Building '$config' config of '$solution' using dotnet command line with version='$VERTUPLE'." 
    dotnet build $solution -c $config -p:AssemblyVersion=$VERTUPLE -p:FileVersion=$VERTUPLE -p:RepositoryUrl=https://github.com/$githubRepo -p:RepositoryType=git -p:RepositoryBranch=$githubBranch -p:RepositoryCommit=$githubCommit
    if (! $?) {
        $rawError = $(Get-Content -Raw "$solution.Errors.log")
        Write-Error "Failed to build $solution. Error: $rawError"
        pop-location
        throw
    }

    Write-Output "Packing '$config' config of '$solution' using dotnet command line." 
    dotnet pack $solution -c $config --no-build --include-source --include-symbols --version-suffix $buildNumber --no-restore -p:Version=$VERTUPLE -p:AssemblyVersion=$VERTUPLE -p:FileVersion=$VERTUPLE -p:RepositoryUrl=https://github.com/$githubRepo -p:RepositoryType=git -p:RepositoryBranch=$githubBranch -p:RepositoryCommit=$githubCommit
    if (! $?) {
        $rawError = $(Get-Content -Raw "$solution.Errors.log")
        Write-Error "Failed to pack $solution. Error: $rawError"
        pop-location
        throw
    }

    if ($publishPackage -eq 'True') {
        # Write-Output "Pushing Package to GitHub Package Repository using dotnet command line." 
        # dotnet nuget push **/*.nupkg --skip-duplicate 
        
        Write-Output "Pushing Package to Nuget Package Repository using dotnet command line." 
        dotnet nuget push **/*.nupkg --skip-duplicate --source https://api.nuget.org/v3/index.json --api-key $nugetSecret
    }

    pop-location
}
