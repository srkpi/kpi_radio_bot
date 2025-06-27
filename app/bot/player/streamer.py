import asyncio

class FFmpegStreamer:
    def __init__(self):
        self.proc = None

    async def start(self):
        ffmpeg_cmd = [
            "ffmpeg",
            "-nostdin",
            "-f",
            "alsa",
            "-ac",
            "2",
            "-ar",
            "48000",
            "-i",
            "hw:Loopback,1",
            "-c:a",
            "libopus",
            "-b:a",
            "128k",
            "-vbr",
            "on",
            "-content_type",
            "application/ogg",
            "-f",
            "ogg",
            "icecast://source:RadioKPI@localhost:8001/stream",
        ]

        self.proc = await asyncio.create_subprocess_exec(
            *ffmpeg_cmd,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        print(f"Started ffmpeg with PID {self.proc.pid}")

        asyncio.create_task(self._read_stderr())

    async def _read_stderr(self):
        assert self.proc.stderr is not None
        buffer = b""
        while True:
            chunk = await self.proc.stderr.read(1024)
            if not chunk:
                break
            buffer += chunk
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                print(f"ffmpeg: {line.decode(errors='ignore').rstrip()}")

    async def stop(self):
        if self.proc and self.proc.returncode is None:
            print("Stopping ffmpeg process...")
            self.proc.terminate()
            try:
                await asyncio.wait_for(self.proc.wait(), timeout=5)
            except asyncio.TimeoutError:
                print("ffmpeg did not exit, killing it...")
                self.proc.kill()
                await self.proc.wait()
            print("ffmpeg stopped")


ffmpeg_streamer = FFmpegStreamer()
