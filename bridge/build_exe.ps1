# Збірка одного exe для розповсюдження (Windows).
# Запуск: cd bridge; .\build_exe.ps1
# Результат: dist\TradeTrackSync.exe

# Запускати з папки bridge: cd bridge; .\build_exe.ps1
Set-Location $PSScriptRoot
pip install -r requirements.txt pyinstaller --quiet
pyinstaller TradeTrackSync.spec
Write-Host "Done. Exe: dist\TradeTrackSync.exe"
