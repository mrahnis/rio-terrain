If (($Env:APPVEYOR_REPO_TAG -eq "true") -and
    ($Env:APPVEYOR_REPO_NAME -eq ${Env:GITHUB_REPO_NAME})) {

  $file_to_upload = (conda build --output .) | Out-String

  #$tar_glob = ".\conda-bld\noarch\${Env:PYPKG}-${Env:APPVEYOR_REPO_TAG_NAME}-*.tar.bz2";
  #Write-Host "distribution file: $tar_glob";

  #If (Test-Path $file_to_upload -PathType Leaf) {
  #    Write-Host "Uploading $file_to_upload"
  #} Else {
  #    Write-Host "Unable to find file to upload: $file_to_upload" -ForegroundColor Red
  #    Return
  #}

  If ($env:APPVEYOR_REPO_TAG_NAME.StartsWith("v")) {
    $anaconda_label = "main"
  } ElseIf ($Env:APPVEYOR_REPO_TAG_NAME.EndsWith("-beta")) {
    $anaconda_label = "beta"
  } ElseIf ($Env:APPVEYOR_REPO_TAG_NAME.EndsWith("-dev")) {
    $anaconda_label = "dev"
  } Else {
    Write-Host "Tag not for deployment, skipping conda package deployment."
    Return
  };

  Write-Host "anaconda_label $anaconda_label";
  Invoke-Expression "anaconda upload $file_to_upload -t $env:ANACONDA_TOKEN -u mrahnis --label $anaconda_label --force"
  # Invoke-Expression "anaconda upload $tar_glob -t $env:ANACONDA_TOKEN -u mrahnis --label $anaconda_label --force"
} Else {
  Write-Host "Not tagged, skipping conda package deployment."
}
