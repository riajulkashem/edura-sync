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
        # Set up a simple logger for the service
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs", "service_runtime.log")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        logging.basicConfig(filename=log_path, level=logging.INFO, 
                            format='%(asctime)s - %(levelname)s - %(message)s')
        
        logging.info("Service main thread started")
        
        try:
            # Path to the executable/script
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(script_dir)
            
            exe_path = os.path.join(project_root, "EduraSync.exe")
            main_py_path = os.path.join(project_root, "main.py")
            
            if os.path.exists(exe_path):
                cmd = f'"{exe_path}" --service'
                logging.info(f"Using bundled executable: {exe_path}")
            elif os.path.exists(main_py_path):
                # Use sys.executable to ensure we use the same environment
                cmd = f'"{sys.executable}" "{main_py_path}" --service'
                logging.info(f"Using source script: {main_py_path} with {sys.executable}")
            else:
                logging.error(f"Could not find main.py or EduraSync.exe in {project_root}")
                return

            # Add creationflags to hide the console window on Windows
            creationflags = 0
            if sys.platform == "win32":
                import subprocess as sp
                creationflags = sp.CREATE_NO_WINDOW

            self.process = subprocess.Popen(cmd, shell=True, creationflags=creationflags)
            logging.info(f"Background process started with PID: {self.process.pid}")
            
            # Wait for stop event
            win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)
            logging.info("Service stop signal received")
            
        except Exception as e:
            logging.error(f"Error in service main loop: {e}", exc_info=True)

if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(EduraSyncService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(EduraSyncService)
