$ErrorActionPreference = "Stop"

python -m PyInstaller `
  --noconfirm `
  --windowed `
  --name "FormatConverterAssistant" `
  --add-data "README.md;." `
  --paths "src" `
  "launcher.py"

Write-Host "PyInstaller build complete: dist\FormatConverterAssistant"
Write-Host "Use NSIS with packaging\installer.nsi to build the installer."
