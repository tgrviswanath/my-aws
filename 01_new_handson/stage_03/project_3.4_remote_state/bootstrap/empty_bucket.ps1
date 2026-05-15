# empty_bucket.ps1 — Delete all versions and delete markers from the state bucket

$bucket = "handson-terraform-state-495331821583"

Write-Host "Fetching all object versions..." -ForegroundColor Cyan

# Get raw JSON from AWS
$rawVersions = aws s3api list-object-versions --bucket $bucket --output json | ConvertFrom-Json

# Build the objects array manually
$objects = @()

if ($rawVersions.Versions) {
    foreach ($v in $rawVersions.Versions) {
        $objects += @{ Key = $v.Key; VersionId = $v.VersionId }
    }
    Write-Host "Found $($rawVersions.Versions.Count) versions." -ForegroundColor Yellow
}

if ($rawVersions.DeleteMarkers) {
    foreach ($m in $rawVersions.DeleteMarkers) {
        $objects += @{ Key = $m.Key; VersionId = $m.VersionId }
    }
    Write-Host "Found $($rawVersions.DeleteMarkers.Count) delete markers." -ForegroundColor Yellow
}

if ($objects.Count -eq 0) {
    Write-Host "Bucket is already empty." -ForegroundColor Green
    exit 0
}

# Write delete payload to a temp file (avoids quoting issues)
$payload = @{ Objects = $objects; Quiet = $true } | ConvertTo-Json -Depth 5
$tmpFile = "$env:TEMP\s3_delete_payload.json"
$payload | Out-File -FilePath $tmpFile -Encoding utf8 -NoNewline

Write-Host "Deleting $($objects.Count) objects/versions..." -ForegroundColor Cyan
aws s3api delete-objects --bucket $bucket --delete "file://$tmpFile"

Remove-Item $tmpFile -Force
Write-Host "Done. Bucket is now empty." -ForegroundColor Green
