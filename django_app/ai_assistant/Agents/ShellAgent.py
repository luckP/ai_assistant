import subprocess

class ShellAgent:
    async def execute(self, command):
        try:
            result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
            return {"success": result.stdout.strip()}
        except subprocess.CalledProcessError as e:
            return {"error": e.stderr.strip()}
