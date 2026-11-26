param(
    [string]$PackDirectory = $PSScriptRoot,
    [string]$AtlasDirectory = '',
    [ValidateSet('', 'magyar', 'latinos')]
    [string]$Variant = '',
    [string]$OutputDirectory = '',
    [switch]$Restore
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2
if (!$PackDirectory) { $PackDirectory = $env:ATLAS_PACK_DIRECTORY }
if (!$PackDirectory) { throw 'PackDirectory is required.' }
$PackDirectory = [IO.Path]::GetFullPath($PackDirectory)
$manifest = Get-Content -LiteralPath (Join-Path $PackDirectory 'manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$allowed = @('Human Anatomy Atlas_Data/resources.assets', 'Human Anatomy Atlas_Data/Managed/Assembly-UnityScript.dll')
if ($manifest.schema -ne 2) { throw 'Unsupported pack manifest.' }
$variantNames = @('magyar', 'latinos')
foreach ($v in $variantNames) {
    $files = @($manifest.variants.$v.files)
    if ($files.Count -ne 2) { throw ('Unsupported pack manifest variant: ' + $v) }
    if (@(Compare-Object @($files | ForEach-Object { $_.path } | Sort-Object) @($allowed | Sort-Object)).Count) { throw 'Unexpected target paths.' }
}
function Get-Hash([string]$Path) { return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() }
function Get-Entry([string]$v, [string]$path) { return @($manifest.variants.$v.files | Where-Object { $_.path -eq $path })[0] }
# Find Atlas 7.4.01 automatically: candidate folders from the uninstall registry and Program Files,
# accepted only if resources.assets is the original 7.4.01 file or one of this pack's patched versions.
function Find-Atlas {
    $assetsPath = 'Human Anatomy Atlas_Data/resources.assets'
    $known = @((Get-Entry 'magyar' $assetsPath).source_sha256) + @($variantNames | ForEach-Object { (Get-Entry $_ $assetsPath).target_sha256 })
    $candidates = New-Object 'System.Collections.Generic.List[string]'
    foreach ($key in @('HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*', 'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*', 'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*')) {
        foreach ($e in @(Get-ItemProperty $key -ErrorAction SilentlyContinue)) {
            $name = $e.PSObject.Properties['DisplayName']; $loc = $e.PSObject.Properties['InstallLocation']
            if ($name -and $loc -and $loc.Value -and ([string]$name.Value) -like '*Anatomy Atlas*') { $candidates.Add(([string]$loc.Value).Trim('"')) }
        }
    }
    foreach ($root in @(${env:ProgramFiles(x86)}, $env:ProgramFiles)) {
        if ($root -and (Test-Path -LiteralPath $root)) {
            foreach ($d in @(Get-ChildItem -LiteralPath $root -Directory -Filter '*Anatomy Atlas*' -ErrorAction SilentlyContinue)) { $candidates.Add($d.FullName) }
        }
    }
    $found = @()
    foreach ($c in ($candidates | Sort-Object -Unique)) {
        $f = Join-Path $c $assetsPath
        if ((Test-Path -LiteralPath (Join-Path $c 'Human Anatomy Atlas.exe')) -and (Test-Path -LiteralPath $f) -and ($known -contains (Get-Hash $f))) { $found += [IO.Path]::GetFullPath($c) }
    }
    $found = @($found | Sort-Object -Unique)
    if ($found.Count -eq 1) { return $found[0] }
    if ($found.Count -eq 0) { throw 'Nem találom az Atlas 7.4.01 telepítését. Adja meg: -AtlasDirectory "<mappa>" / Atlas 7.4.01 not found; pass -AtlasDirectory.' }
    throw ('Több Atlas-telepítést találtam, adja meg melyiket (-AtlasDirectory) / Several installs found: ' + ($found -join '; '))
}
if (!$AtlasDirectory) { $AtlasDirectory = Find-Atlas; Write-Output ('Atlas mappa / folder: ' + $AtlasDirectory) }
$AtlasDirectory = [IO.Path]::GetFullPath($AtlasDirectory)
function Copy-Range($Source, $Destination, [long]$Offset, [long]$Length) {
    if ($Offset -lt 0 -or $Length -lt 0 -or $Offset -gt $Source.Length -or $Length -gt ($Source.Length-$Offset)) { throw 'Delta range is out of bounds.' }
    $Source.Position = $Offset
    $buffer = New-Object byte[] 65536
    while ($Length -gt 0) {
        $wanted = [int][Math]::Min([long]$buffer.Length, $Length)
        $read = $Source.Read($buffer, 0, $wanted)
        if ($read -le 0) { throw 'Truncated source or patch data.' }
        $Destination.Write($buffer, 0, $read)
        $Length -= $read
    }
}
function Write-PatchedFile($Entry, [string]$SourcePath, [string]$DestinationPath) {
    if ((Get-Hash $SourcePath) -ne $Entry.source_sha256) { throw ('Wrong source hash: '+$Entry.path) }
    if ([IO.Path]::GetFileName($Entry.literal_file) -ne $Entry.literal_file) { throw 'Invalid literal filename.' }
    $literalPath = Join-Path $PackDirectory $Entry.literal_file
    if ((Get-Hash $literalPath) -ne $Entry.literal_sha256) { throw 'Patch data checksum mismatch.' }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $DestinationPath) | Out-Null
    $source = [IO.File]::OpenRead($SourcePath)
    $literal = [IO.File]::OpenRead($literalPath)
    $destination = [IO.File]::Open($DestinationPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write)
    try {
        [long]$total = 0
        foreach ($op in $Entry.operations) {
            if (@($op).Count -ne 3) { throw 'Invalid operation.' }
            [long]$offset = $op[1]; [long]$length = $op[2]
            if ($length -lt 0 -or $total -gt ([long]$Entry.target_size-$length)) { throw 'Invalid target length.' }
            if ($op[0] -eq 'copy') { Copy-Range $source $destination $offset $length }
            elseif ($op[0] -eq 'data') { Copy-Range $literal $destination $offset $length }
            else { throw 'Unknown delta operation.' }
            $total += $length
        }
        if ($total -ne $Entry.target_size) { throw 'Target length mismatch.' }
    } finally { $source.Dispose(); $literal.Dispose(); $destination.Dispose() }
    if ((Get-Hash $DestinationPath) -ne $Entry.target_sha256) { throw ('Reconstructed checksum mismatch: '+$Entry.path) }
}
# Classify a current file: 'source', a variant name, or $null (unknown).
function Get-State([string]$path, [string]$hash) {
    $src = (Get-Entry 'magyar' $path).source_sha256
    if ($hash -eq $src) { return 'source' }
    foreach ($v in $variantNames) { if ($hash -eq (Get-Entry $v $path).target_sha256) { return $v } }
    return $null
}
$backupRoot = Join-Path $AtlasDirectory 'HungarianLatinPack-backup-7.4.01'
$runningAtlas = @(Get-Process -Name 'Human Anatomy Atlas' -ErrorAction SilentlyContinue | Where-Object { !$_.Path -or $_.Path -eq (Join-Path $AtlasDirectory 'Human Anatomy Atlas.exe') })
if (!$OutputDirectory -and $runningAtlas.Count -gt 0) { throw 'Zárja be a Human Anatomy Atlas programot a telepítés/visszaállítás előtt. / Close Human Anatomy Atlas first.' }

$states = @{}
foreach ($p in $allowed) { $states[$p] = Get-State $p (Get-Hash (Join-Path $AtlasDirectory $p)) }
foreach ($p in $allowed) { if ($null -eq $states[$p]) { throw ('Nem támogatott vagy módosított fájl / Unsupported or modified file: ' + $p + ' (Atlas 7.4.01 szükséges)') } }

if ($Restore) {
    if ($OutputDirectory) { throw 'Restore cannot be combined with OutputDirectory.' }
    foreach ($p in $allowed) {
        if ($states[$p] -eq 'source') { continue }
        $backup = Join-Path $backupRoot $p
        if (!(Test-Path -LiteralPath $backup) -or (Get-Hash $backup) -ne (Get-Entry 'magyar' $p).source_sha256) { throw ('Missing/invalid original backup: '+$p) }
    }
    foreach ($p in $allowed) {
        if ($states[$p] -eq 'source') { continue }
        $current = Join-Path $AtlasDirectory $p
        Copy-Item -LiteralPath (Join-Path $backupRoot $p) -Destination $current -Force
        if ((Get-Hash $current) -ne (Get-Entry 'magyar' $p).source_sha256) { throw 'Restore verification failed.' }
    }
    Write-Output 'VISSZAÁLLÍTVA / RESTORED: az eredeti angol fájlok ellenőrizve; a beállítások (pl. joystick) nem változtak.'
    return
}

if (!$Variant) {
    Write-Output ''
    Write-Output 'Válassza ki a nevek stílusát / Choose the naming style:'
    Write-Output '  1 = magyaros (oldalsó / belső)       pl. "Oldalsó combcsont körüli ér"'
    Write-Output '  2 = latinos  (laterális / mediális)  pl. "Laterális combcsont körüli ér"'
    $answer = ([string](Read-Host 'Választás / Choice [1/2]')).Trim().ToLowerInvariant()
    if ($answer -eq '1' -or $answer -eq 'magyar') { $Variant = 'magyar' } elseif ($answer -eq '2' -or $answer -eq 'latinos') { $Variant = 'latinos' } else { throw 'Érvénytelen választás / Invalid choice.' }
}

$already = $true
foreach ($p in $allowed) { if ($states[$p] -ne $Variant) { $already = $false } }
if ($already -and !$OutputDirectory) { Write-Output ('MÁR TELEPÍTVE / ALREADY INSTALLED: ' + $Variant); return }

# Patch from the original: either the current file (if original) or the verified backup (if another variant is installed).
$sources = @{}
foreach ($p in $allowed) {
    $current = Join-Path $AtlasDirectory $p
    if ($states[$p] -eq 'source') { $sources[$p] = $current }
    else {
        $backup = Join-Path $backupRoot $p
        if (!(Test-Path -LiteralPath $backup) -or (Get-Hash $backup) -ne (Get-Entry 'magyar' $p).source_sha256) { throw ('Missing/invalid original backup; cannot switch variant: '+$p) }
        $sources[$p] = $backup
    }
}
$stageRoot = if ($OutputDirectory) { [IO.Path]::GetFullPath($OutputDirectory) } else { Join-Path $AtlasDirectory ('HU-Latin-stage-'+[Guid]::NewGuid().ToString('N')) }
if (Test-Path -LiteralPath $stageRoot) { throw 'Output/staging directory must not exist.' }
New-Item -ItemType Directory -Path $stageRoot | Out-Null
$committed = New-Object 'System.Collections.Generic.List[string]'
try {
    foreach ($p in $allowed) { Write-PatchedFile (Get-Entry $Variant $p) $sources[$p] (Join-Path $stageRoot $p) }
    if ($OutputDirectory) { Write-Output ('STAGED AND VERIFIED: '+$stageRoot+' ('+$Variant+')'); return }
    # Do not touch current files until both reconstructions and all backups verify.
    foreach ($p in $allowed) {
        $backup = Join-Path $backupRoot $p
        if (Test-Path -LiteralPath $backup) {
            if ((Get-Hash $backup) -ne (Get-Entry 'magyar' $p).source_sha256) { throw 'Existing backup hash mismatch.' }
        } else {
            if ($states[$p] -ne 'source') { throw 'No backup for a patched file.' }
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $backup) | Out-Null
            Copy-Item -LiteralPath (Join-Path $AtlasDirectory $p) -Destination $backup
            if ((Get-Hash $backup) -ne (Get-Entry 'magyar' $p).source_sha256) { throw 'Backup verification failed.' }
        }
    }
    foreach ($p in $allowed) {
        $current = Join-Path $AtlasDirectory $p
        [IO.File]::Replace((Join-Path $stageRoot $p), $current, [System.Management.Automation.Language.NullString]::Value)
        $committed.Add($p)
        if ((Get-Hash $current) -ne (Get-Entry $Variant $p).target_sha256) { throw 'Installed hash mismatch.' }
    }
    Write-Output ('TELEPÍTVE ÉS ELLENŐRIZVE / INSTALLED AND VERIFIED: ' + $Variant + '. A programban az English nyelvet kell választani (ennek helyén jelenik meg a magyar). A latin nevek és a beállítások változatlanok.')
} catch {
    foreach ($p in $committed) { Copy-Item -LiteralPath (Join-Path $backupRoot $p) -Destination (Join-Path $AtlasDirectory $p) -Force }
    throw
} finally {
    if (!$OutputDirectory -and (Test-Path -LiteralPath $stageRoot)) { Remove-Item -LiteralPath $stageRoot -Recurse -Force }
}
