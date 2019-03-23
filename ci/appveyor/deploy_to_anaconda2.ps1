if (($Env:APPVEYOR_REPO_TAG -eq "true") -and
    ($Env:APPVEYOR_REPO_NAME -eq ${Env:GITHUB_REPO_NAME})) {
  $tar_glob = ".\conda-bld\noarch\${Env:PYPKG}-${Env:APPVEYOR_REPO_TAG_NAME}-*.tar.bz2";
  Write-Host "tar_glob $tar_glob";
  if ($env:APPVEYOR_REPO_TAG_NAME.StartsWith("v")) {
    $anaconda_label = "main"
  } elseif ($Env:APPVEYOR_REPO_TAG_NAME -like "*b*") {
    $anaconda_label = "beta"
  } else {
    $anaconda_label = "dev"
  };
  Write-Host "anaconda_label $anaconda_label";
  Invoke-Expression "anaconda upload $file_to_upload -t $env:ANACONDA_TOKEN --label $anaconda_label --force"
}
