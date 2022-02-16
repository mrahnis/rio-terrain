<#
    Generate CLI help files from Click online help.
    These will get picked up by Sphinx.
 #>
# can i get the command list elsewhere?
$commands = @(
    "aspect",
    "curvature",
    "difference",
    "extract",
    "label",
    "mad",
    "quantiles",
    "slice",
    "slope",
    "std",
    "threshold",
    "uncertainty"
)

$dst = "$($PSScriptRoot)\..\docs\source\cli"
ForEach ($command in $commands)
{
    Write-Host "Writing help for $command"
    $path = Join-Path $dst cli.${command}.txt
    & "rio" ${command} --help | Out-File $path
}
