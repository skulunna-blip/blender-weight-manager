$ErrorActionPreference = "Stop"
$src = "C:\Users\hasee\blender-weight-manager\weight_manager"
$out = "C:\Users\hasee\blender-weight-manager\weight_manager.zip"
Add-Type -AssemblyName System.IO.Compression.FileSystem
if (Test-Path $out) { Remove-Item $out -Force }
$zip = [System.IO.Compression.ZipFile]::Open($out, 'Create')
foreach ($f in @('__init__.py','weight_tools.py','README.md')) {
    $pf = Join-Path $src $f
    $entry = $zip.CreateEntry("weight_manager/$f")
    $es = $entry.Open()
    $bytes = [System.IO.File]::ReadAllBytes($pf)
    $es.Write($bytes, 0, $bytes.Length)
    $es.Close()
    Write-Host "packed weight_manager/$f"
}
$zip.Dispose()
Write-Host "OK -> $out"