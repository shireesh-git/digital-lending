# Consolidate all test documents into a single organized folder structure
# This copies (not moves) files to preserve original locations

$root = "c:\Working\Corportate Lending"
$dest = "$root\test-documents"

# Clean and recreate
if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }

# Entity-to-company mapping
$entities = @{
    "APOL001" = @{ Name = "Apollo_Hospitals"; Pattern = "Apollo Hosp*" }
    "IHCL001" = @{ Name = "IHCL";            Pattern = "IHCL*" }
    "INFY001" = @{ Name = "Infosys";         Pattern = "Infy*" }
    "MFL001"  = @{ Name = "Madras_Fertilisers"; Pattern = "Madras Fert*" }
    "MRF001"  = @{ Name = "MRF";             Pattern = "MRF*" }
}

foreach ($entity in $entities.Keys) {
    $info = $entities[$entity]
    $companyDir = "$dest\$($entity)_$($info.Name)"

    # 1. Copy real annual reports from downloaded document/CAM/
    $arDir = "$companyDir\annual-reports"
    New-Item -ItemType Directory -Path $arDir -Force | Out-Null
    $arFiles = Get-ChildItem "$root\downloaded document\CAM\$($info.Pattern).pdf" -ErrorAction SilentlyContinue
    foreach ($f in $arFiles) {
        Copy-Item $f.FullName "$arDir\$($f.Name)"
    }
    Write-Host "  $entity annual-reports: $($arFiles.Count) files"

    # 2. Copy synthetic optional inputs
    $optDir = "$companyDir\optional-inputs"
    $srcOpt = "$root\synthetic-assets\optional_inputs\$entity"
    if (Test-Path $srcOpt) {
        New-Item -ItemType Directory -Path $optDir -Force | Out-Null
        Copy-Item "$srcOpt\*" $optDir -Force
        $optCount = (Get-ChildItem $optDir).Count
        Write-Host "  $entity optional-inputs: $optCount files"
    }

    # 3. Copy platform-generated document pack (from storage/documents/)
    $storDir = "$root\storage\documents\$entity"
    if (Test-Path $storDir) {
        $packDir = "$companyDir\platform-document-pack"
        # Copy entire subdirectory structure
        Copy-Item $storDir $packDir -Recurse -Force
        $pdfCount = (Get-ChildItem $packDir -Recurse -Filter "*.pdf").Count
        Write-Host "  $entity platform-pack: $pdfCount PDFs"
    }
}

# TVS Motors (no entity ID in synthetic-assets, only real annual reports)
$tvsDir = "$dest\TVS_Motors"
$tvsArDir = "$tvsDir\annual-reports"
New-Item -ItemType Directory -Path $tvsArDir -Force | Out-Null
$tvsFiles = Get-ChildItem "$root\downloaded document\CAM\TVS Mot*.pdf" -ErrorAction SilentlyContinue
foreach ($f in $tvsFiles) {
    Copy-Item $f.FullName "$tvsArDir\$($f.Name)"
}
Write-Host "  TVS Motors annual-reports: $($tvsFiles.Count) files"

# Reference CAMs
$refDir = "$dest\reference-cams"
New-Item -ItemType Directory -Path $refDir -Force | Out-Null
if (Test-Path "$root\refer") {
    Copy-Item "$root\refer\*" $refDir -Force
    Write-Host "  reference-cams: $((Get-ChildItem $refDir).Count) files"
}

# ETB overlays
$etbDir = "$dest\etb-overlays"
New-Item -ItemType Directory -Path $etbDir -Force | Out-Null
if (Test-Path "$root\synthetic-assets\etb_overlays") {
    Copy-Item "$root\synthetic-assets\etb_overlays\*" $etbDir -Force
    Write-Host "  etb-overlays: $((Get-ChildItem $etbDir).Count) files"
}

Write-Host "`nConsolidation complete. Structure:"
Get-ChildItem $dest -Recurse | ForEach-Object {
    $indent = "  " * ($_.FullName.Replace($dest, "").Split("\").Length - 1)
    if ($_.PSIsContainer) {
        Write-Host "$indent$($_.Name)/"
    } else {
        Write-Host "$indent$($_.Name)"
    }
}
