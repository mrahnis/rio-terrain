# if (($env:APPVEYOR_REPO_TAG -eq "true") -and ($env:APPVEYOR_REPO_TAG_NAME.StartsWith("v"))) {
if (($env:APPVEYOR_REPO_TAG -eq "true") -and ($env:GIT_DESCRIBE_TAG.StartsWith("v"))) {
    write-output "Deploying to anaconda main channel..."
    $channel = "main"
} else {
    write-output "Deploying to anaconda dev channel..."
    $channel = "dev"
    $env:BUILD_STR = "dev"
}

Invoke-Expression "conda config --set anaconda_upload no"

$file_to_upload = (conda build --output .) | Out-String

write-output "Uploading $file_to_upload..."
Invoke-Expression "anaconda -t $env:ANACONDA_TOKEN upload --force --user mrahnis --channel $channel $file_to_upload"

write-output "Upload sucess"