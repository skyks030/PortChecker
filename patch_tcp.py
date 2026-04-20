import os

with open('monitor.py', 'r') as f:
    content = f.read()

old_tcp = """    async def execute(self) -> CheckResult:
        host = self.config.get("host")
        port = self.config.get("port")
        description = self.config.get("description", f"Port {port}")
        
        if not host or not port:
            return CheckResult(CheckStatus.UNKNOWN, error="Host oder Port nicht angegeben")
        
        try:
            start_time = asyncio.get_event_loop().time()
            
            # TCP Verbindung versuchen
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=5.0
            )
            
            response_time = (asyncio.get_event_loop().time() - start_time) * 1000
            
            writer.close()
            await writer.wait_closed()
            
            return CheckResult(
                CheckStatus.UP,
                response_time=response_time,
                details=f"{description} erreichbar ({response_time:.1f}ms)"
            )
        
        except asyncio.TimeoutError:
            return CheckResult(CheckStatus.DOWN, error=f"{description} Timeout")
        except ConnectionRefusedError:
            return CheckResult(CheckStatus.DOWN, error=f"{description} abgelehnt")
        except Exception as e:
            return CheckResult(CheckStatus.DOWN, error=f"Fehler: {str(e)}")"""

new_tcp = """    async def execute(self) -> CheckResult:
        host = self.config.get("host")
        port = self.config.get("port")
        description = self.config.get("description", f"Port {port}")
        
        if not host or not port:
            return CheckResult(CheckStatus.UNKNOWN, error="Host oder Port nicht angegeben")
            
        for attempt in range(3):
            try:
                start_time = asyncio.get_event_loop().time()
                
                # TCP Verbindung versuchen
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port),
                    timeout=5.0
                )
                
                response_time = (asyncio.get_event_loop().time() - start_time) * 1000
                
                writer.close()
                await writer.wait_closed()
                
                return CheckResult(
                    CheckStatus.UP,
                    response_time=response_time,
                    details=f"{description} erreichbar ({response_time:.1f}ms)"
                )
            
            except (asyncio.TimeoutError, ConnectionRefusedError, OSError) as e:
                import asyncio
                if attempt == 2:
                    if isinstance(e, asyncio.TimeoutError):
                        return CheckResult(CheckStatus.DOWN, error=f"{description} Timeout")
                    elif isinstance(e, ConnectionRefusedError):
                        return CheckResult(CheckStatus.DOWN, error=f"{description} abgelehnt")
                    else:
                        return CheckResult(CheckStatus.DOWN, error=f"Fehler: {str(e)}")
                await asyncio.sleep(1.0)
                
        return CheckResult(CheckStatus.DOWN, error="Unknown Failure")"""

content = content.replace(old_tcp, new_tcp)

with open('monitor.py', 'w') as f:
    f.write(content)
