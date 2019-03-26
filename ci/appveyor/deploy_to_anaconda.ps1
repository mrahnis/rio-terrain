If (($Env:APPVEYOR_REPO_TAG -eq "true") -and
    ($Env:APPVEYOR_REPO_NAME -eq ${Env:GITHUB_REPO_NAME})) {

  $file_to_upload = (conda build --output .) | Out-String

  If ($Env:APPVEYOR_REPO_TAG_NAME.StartsWith("v")) {
    If ($Env:APPVEYOR_REPO_TAG_NAME.EndsWith("-dev")) {
      $labels = "dev"
    } ElseIf ($Env:APPVEYOR_REPO_TAG_NAME.EndsWith("-beta")) {
      $labels = "beta"
    } else {
      $labels = "main"
    }
  } Else {
    Write-Host "Tag not for deployment, skipping conda package deployment."
    Return
  }
  Write-Host "Deploying package $file_to_upload with label $labels"
  Invoke-Expression "anaconda -t $Env:ANACONDA_TOKEN upload --label $labels --force --no-progress $file_to_upload"
} Else {
  Write-Host "Not tagged, skipping conda package deployment."
}
