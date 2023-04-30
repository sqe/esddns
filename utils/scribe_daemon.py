import subprocess

def daemon_whisper(cycle_stamp=None):
    cycle_stamp = "Next scheduled run in "
    transcribe_cycle = []
    execute_command = subprocess.Popen(
        ["/usr/bin/python3", "esddns.py"],
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
