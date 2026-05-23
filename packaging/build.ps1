$ErrorActionPreference = "Stop"

python -m PyInstaller `
  --noconfirm `
  --windowed `
  --name "FormatConverterAssistant" `
  --add-data "README.md;." `
  --paths "src" `
  --exclude-module "IPython" `
  --exclude-module "matplotlib" `
  --exclude-module "pandas" `
  --exclude-module "pytest" `
  --exclude-module "scipy" `
  --exclude-module "sqlalchemy" `
  --exclude-module "torch" `
  --exclude-module "torchaudio" `
  --exclude-module "torchvision" `
  "launcher.py"

Write-Host "PyInstaller build complete: dist\FormatConverterAssistant"
Write-Host "Use NSIS with packaging\installer.nsi to build the installer."
