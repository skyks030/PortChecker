import pty
import os
import time

pid, fd = pty.fork()
if pid == 0:
    os.environ["TERM"] = "dumb"
    os.execlp("ssh", "ssh", "-o", "StrictHostKeyChecking=no", "snp@192.168.10.25", "pmset -g custom | grep -i tcpkeepalive; pmset -g | grep -i sleep; uptime")
else:
    time.sleep(2)
    os.write(fd, b"snp1\n")
    output = b""
    while True:
        try:
            data = os.read(fd, 1024)
            if not data:
                break
            output += data
            if b"closed" in data:
                break
        except OSError:
            break
    print("TARGET OUTPUT:\n" + output.decode(errors="replace"))
