import pty, os, time, sys

pid, fd = pty.fork()
if pid == 0:
    os.execvp("ssh", ["ssh", "-o", "StrictHostKeyChecking=no", "snp@192.168.10.25", "/usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate; /usr/libexec/ApplicationFirewall/socketfilterfw --getstealthmode; pmset -g | grep tcpkeepalive"])

time.sleep(2)
os.write(fd, b"snp1\n")
out = b""
start = time.time()
while time.time() - start < 5:
    try:
        data = os.read(fd, 1024)
        if not data: break
        out += data
    except Exception:
        break
print(out.decode('utf-8', 'ignore'))
