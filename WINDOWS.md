# Windows portable app

For 64-bit Windows 10/11. The ZIP includes Python 3.12.10 and the Qt6 / PySide6 Essentials runtime, with their upstream licenses. No Python installation or dependency download is needed on the target machine.

1. Extract the entire ZIP to a folder you can keep.
2. Double-click `launch-native.cmd` inside `WingsOfFreedomTracker`.
3. Click **Open save or tracker** and choose `ATWIN0000.dat` or `ATWIN0001.dat` from `Documents\KoeiTecmo\Attack on Titan\SAVEDATA`. You can also import a tracker JSON exported on Linux.
4. Choose **Farming plan**, set the goal and mode, and enable **Buy shop materials** if preferred. Record full runs in **Run log** for observed yields.

After saving in-game, use **Reload source save**. Source saves are read-only; manual corrections affect only the tracker. Export tracker JSON to transfer corrections, settings and run logs between computers. Help → About shows your local session storage location.

If the window does not appear, open a terminal in the extracted folder and run `runtime\python.exe desktop_app.py` to see startup errors. This is an unsigned portable folder, not a Windows installer or a signed executable. Keep the runtime directory beside the application files.

The Windows runtime can be smoke-tested under Wine on Linux. This does not replace verification on a physical Windows machine.

Validation: the bundled Windows Python and Qt DLLs loaded under Wine 11.20 on Linux. All nine views rendered against a real save without changing its hash. Real Windows 10/11 hardware has not been tested.
