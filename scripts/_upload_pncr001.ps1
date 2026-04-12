$BASE = "https://camdemo-228620181301.asia-south1.run.app"
$ENTITY = "PNCR001"
$DOCROOT = "c:\Working\Corportate Lending\test-documents\PNCR001_PNC_Roads\platform-document-pack"

$files = Get-ChildItem $DOCROOT -Recurse -File
$total = $files.Count
$i = 0

foreach ($f in $files) {
    $i++
    $rel = $f.FullName.Substring($DOCROOT.Length + 1).Replace('\', '/')
    $folder = if ($rel -match '/') { ($rel -split '/')[0] } else { "root" }
    Write-Host "[$i/$total] $rel -> $folder"

    $result = curl.exe -s -X POST "$BASE/api/companies/$ENTITY/documents" `
        -F "file=@$($f.FullName)" `
        -F "category=$folder" `
        -F "subcategory=platform_upload"
    
    if ($result -match '"status"\s*:\s*"error"') {
        Write-Host "  ERROR: $result" -ForegroundColor Red
    }
}

Write-Host "`nDone. Uploaded $total files."
