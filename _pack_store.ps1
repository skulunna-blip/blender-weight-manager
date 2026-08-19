# 打包官方扩展 zip（平级，不套 store/ 文件夹）
$src = (Join-Path $PSScriptRoot "store")
$out = (Join-Path $src "weight_manager.zip")
Add-Type -AssemblyName System.IO.Compression.FileSystem
if (Test-Path $out) { Remove-Item $out -Force }
$zip = [System.IO.Compression.ZipFile]::Open($out, 'Create')
foreach ($f in @('blender_manifest.toml','__init__.py','weight_tools.py','README.md','LICENSE')) {
    $p = Join-Path $src $f
    if (-not (Test-Path $p)) { Write-Host "MISSING: $f"; continue }
    $entry = $zip.CreateEntry($f)   # 平级，不带 id/ 前缀
    $es = $entry.Open()
    $bytes = [System.IO.File]::ReadAllBytes($p)
    $es.Write($bytes, 0, $bytes.Length); $es.Close()
}
$zip.Dispose()
Write-Host "OK -> $out"
