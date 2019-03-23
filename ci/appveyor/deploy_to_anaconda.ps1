if (($Env:APPVEYOR_REPO_TAG -eq "true") -and
    ($Env:APPVEYOR_REPO_NAME -eq ${Env:GITHUB_REPO_NAME})) {
  $tar_glob = ".\conda-bld\noarch\${Env:PYPKG}-${Env:APPVEYOR_REPO_TAG_NAME}-*.tar.bz2";
  Write-Host "distribution file: $tar_glob";
  if ($env:APPVEYOR_REPO_TAG_NAME.StartsWith("v")) {
    $anaconda_label = "main"
  } elseif ($Env:APPVEYOR_REPO_TAG_NAME.EndsWith("-beta")) {
    $anaconda_label = "beta"
  } elseif ($Env:APPVEYOR_REPO_TAG_NAME.EndsWith("-dev")) {
    $anaconda_label = "dev"
  } else {
    Write-Host "Tag not for deployment, skipping conda package deployment."
    Return
  };
  Write-Host "anaconda_label $anaconda_label";
  Invoke-Expression "anaconda upload $file_to_upload -t $env:ANACONDA_TOKEN --label $anaconda_label --force"
} else {
  Write-Host "Not tagged, skipping conda package deployment."
}
