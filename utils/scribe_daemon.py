import subprocess
import sys
import os

def daemon_whisper(cycle_stamp=None):
    cycle_stamp = "Next scheduled run in "
    transcribe_cycle = []
    
    # Ensure we're running from the correct directory
    esddns_path = os.path.join(os.path.dirname(__file__), "..", "esddns.py")
    execute_command = subprocess.Popen(
        [sys.executable, esddns_path],
        text=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
        universal_newlines=True)
    while True:
        output_line = execute_command.stdout.readline()
        transcribe_cycle.append(str(output_line).strip("\n"))        
        if not output_line: 
            transcribe_cycle.append(str(output_line).strip("\n"))        
            return transcribe_cycle
        if cycle_stamp in output_line:
            return transcribe_cycle
