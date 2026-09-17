Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
strDir = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = strDir

If fso.FileExists(strDir & "\venv\Scripts\pythonw.exe") Then
    WshShell.Run Chr(34) & strDir & "\venv\Scripts\pythonw.exe" & Chr(34) & " main.py", 0, False
Else
    WshShell.Run "cmd /c run.bat", 1, False
End If
