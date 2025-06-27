import asyncio

class FFmpegStreamer:
    def __init__(self):
        self.proc = None

    async def start(self):
        ffmpeg_cmd = [
            "ffmpeg",
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
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        print(f"Started ffmpeg with PID {self.proc.pid}")

        asyncio.create_task(self._read_stderr())

    async def _read_stderr(self):
        assert self.proc.stderr is not None
        async for line in self.proc.stderr:
            print(f"ffmpeg: {line.decode().rstrip()}")

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
