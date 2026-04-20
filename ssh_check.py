import pty
import os
import time

commands = [
    "pmset -g custom",
    "ifconfig",
    "arp -a | grep 192.168.10",
    "netstat -rn",
    "/usr/libexec/ApplicationFirewall/socketfilterfw --getstealthmode",
    "system_profiler SPNetworkDataType"
]

pid, fd = pty.fork()
if pid == 0:
    os.environ["TERM"] = "dumb"
    os.execlp("ssh", "ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=10", "snp@192.168.10.25", "; ".join(commands))
else:
    time.sleep(2) # wait for ssh prompt
    os.write(fd, b"snp1\n")
    output = b""
    start = time.time()
    while True:
        try:
            data = os.read(fd, 4096)
            if not data:
                break
            output += data
        except OSError:
            break
        if time.time() - start > 15:
            break
    print("TARGET OUTPUT:\n" + output.decode(errors="replace"))
