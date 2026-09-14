' Google Photos ReVanced - Silent Launcher (No Console Window)
Set WshShell = CreateObject("WScript.Shell")
Dim fso, scriptDir
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

Dim pythonwExe, mainScript
pythonwExe = scriptDir & "\venv\Scripts\pythonw.exe"
mainScript = scriptDir & "\main.py"

If Not fso.FileExists(pythonwExe) Then
    ' Fallback to run.bat if venv is not ready
    WshShell.Run """" & scriptDir & "\run.bat""", 1, True
Else
    WshShell.CurrentDirectory = scriptDir
    WshShell.Run """" & pythonwExe & """ """ & mainScript & """", 0, False
End If
Set WshShell = Nothing
Set fso = Nothing
