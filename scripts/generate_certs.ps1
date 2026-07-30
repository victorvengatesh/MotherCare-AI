# generate_certs.ps1 — Generate self-signed SSL certificates using Python on Windows

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonBin = "$ScriptDir/../backend/.venv/Scripts/python.exe"

if (Test-Path $PythonBin -PathType Leaf) {
    & $PythonBin "$ScriptDir/generate_certs.py"
} else {
    python "$ScriptDir/generate_certs.py"
}
