@echo off
setlocal
if exist "%~dp0research\versioning\git_metadata\HEAD" (
  git --git-dir="%~dp0research\versioning\git_metadata" --work-tree="%~dp0." %*
) else (
  git -C "%~dp0." %*
)
