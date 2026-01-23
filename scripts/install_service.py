import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import sys
import os
import subprocess
import logging

class EduraSyncService(win32serviceutil.ServiceFramework):
    _svc_name_ = "EduraSyncService"
    _svc_display_name_ = "EduraSync Attendance Service"
    _svc_description_ = "Synchronizes attendance data from ZKTeco devices to the cloud."

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)
        self.process = None

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        if self.process:
            self.process.terminate()

    def SvcDoRun(self):
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_, ''))
        self.main()

    def main(self):
        # Path to the executable
        # If running from source, this would be python main.py --service
        # If running from bundled exe, this should be the exe path
        
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        exe_path = os.path.join(exe_dir, "EduraSync.exe")
        
        if not os.path.exists(exe_path):
            # Fallback for development
            script_path = os.path.join(os.path.dirname(os.getcwd()), "main.py")
            cmd = f'python "{script_path}" --service'
        else:
            cmd = f'"{exe_path}" --service'

        self.process = subprocess.Popen(cmd, shell=True)
        
        # Wait for stop event
        win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)

if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(EduraSyncService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(EduraSyncService)
