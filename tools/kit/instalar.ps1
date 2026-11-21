# Lanza el asistente de instalacion del kit de Atalaya (tools/kit/instalar.py).
# Launches the Atalaya kit installation assistant.  Uso / Usage:  .\tools\kit\instalar.ps1 [opciones / options]
# Solo busca Python 3.9+; si falta, explica como obtenerlo y NO descarga ni instala nada.
$ErrorActionPreference = 'Stop'
$aqui = Split-Path -Parent $MyInvocation.MyCommand.Path
$script = Join-Path $aqui 'instalar.py'
$check = 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)'

# (ejecutable, argumentos previos). `py -3` es el lanzador oficial de Windows; se ignora el atajo vacio de la Tienda.
$candidatos = @(@('py', '-3'), @('python'), @('python3'))
foreach ($c in $candidatos) {
    $cmd = Get-Command $c[0] -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $cmd) { continue }
    $previos = @($c | Select-Object -Skip 1)
    & $cmd.Source @previos -c $check 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        & $cmd.Source @previos $script @args
        exit $LASTEXITCODE
    }
}

$en = ($env:ATALAYA_LANG -like 'en*') -or (($args -contains '--lang') -and ($args -contains 'en'))
if ($en) {
    [Console]::Error.WriteLine("Python 3.9 or newer was not found. This assistant installs nothing by itself.`nGet it from https://www.python.org/downloads/ (or: winget install Python.Python.3.12) and run this script again.")
} else {
    [Console]::Error.WriteLine("No se encontro Python 3.9 o superior. Este asistente no instala nada por su cuenta.`nObtenlo en https://www.python.org/downloads/ (o: winget install Python.Python.3.12) y vuelve a ejecutar este script.")
}
exit 1
