# Record the mega demo from Windows.
#
#   powershell -File demo/record/record.ps1               # 120x36, the default
#   powershell -File demo/record/record.ps1 -Cols 100 -Rows 30
#
# The recorder drives the app under a POSIX pty, which Windows does not have,
# so this hands record.sh to WSL. The checkout is reached through /mnt/c; gala,
# Go, python3 + pyte and agg must be installed inside WSL — see
# demo/record/README.md.
param(
    [int]$Cols = 120,
    [int]$Rows = 36,
    [string]$Cast = "docs/demo.cast",
    [string]$Gif = "docs/gala-tui-demo.gif"
)
$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path

# A login shell, so ~/.profile puts ~/.local/bin (gala, go, agg) on PATH.
wsl.exe --cd "$repo" -e env "COLS=$Cols" "ROWS=$Rows" "CAST=$Cast" "GIF=$Gif" `
    bash -lc "demo/record/record.sh"
exit $LASTEXITCODE
