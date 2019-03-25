If (($Env:APPVEYOR_REPO_TAG -eq "true") -and
    ($Env:APPVEYOR_REPO_NAME -eq ${Env:GITHUB_REPO_NAME})) {

  $file_to_upload = (conda build --output .) | Out-String

  #$tar_glob = ".\conda-bld\noarch\${Env:PYPKG}-${Env:APPVEYOR_REPO_TAG_NAME}-*.tar.bz2"
  #Write-Host "distribution file: $tar_glob"

  If ($Env:APPVEYOR_REPO_TAG_NAME.StartsWith("v")) {
    $anaconda_label = "main"

    If ($Env:APPVEYOR_REPO_TAG_NAME.EndsWith("-beta")) {
      $anaconda_label = "main beta"
    } ElseIf ($Env:APPVEYOR_REPO_TAG_NAME.EndsWith("-dev")) {
      $anaconda_label = "dev"
    }
  } Else {
    Write-Host "Tag not for deployment, skipping conda package deployment."
    Return
  }

  Write-Host "Uploading $file_to_upload with label $anaconda_label"
  # if the token or filename has certain special characters in it powershell sees subsequent -- as unary minus
  Invoke-Expression "anaconda -t $Env:ANACONDA_TOKEN upload --label $anaconda_label --force --no-progress $file_to_upload"
  # Invoke-Expression "anaconda -t $env:ANACONDA_TOKEN upload $tar_glob --label $anaconda_label --force"
} Else {
  Write-Host "Not tagged, skipping conda package deployment."
}
