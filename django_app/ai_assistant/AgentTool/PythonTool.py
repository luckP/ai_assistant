import subprocess
import os
import logging
from .AgentTool import AgentTool

class PythonTool(AgentTool):
    """
    Tool for executing Python code.
    """

    def process_task(self, task: str) -> str:
        """
        Execute a Python script and return the output.
        """
        script_path = os.path.join(self.work_dir, "script.py")
        try:
            # Write the task (Python code) to a script file
            with open(script_path, "w") as file:
                file.write(task)

            # Log the task
            logging.info(f"Executing Python script:\n{task}")

            # Execute the Python script
            result = subprocess.run(
                ["python3", script_path],
                shell=False,
                check=True,
                capture_output=True,
                text=True,
                cwd=self.work_dir
            )

            # Log and return the result
            logging.info(f"Python script executed successfully: {result.stdout.strip()}")
            return result.stdout.strip()

        except subprocess.CalledProcessError as e:
            error_message = f"Error executing Python script: {e.stderr.strip()}"
            logging.error(error_message)
            return error_message

        except Exception as e:
            error_message = f"Error: {str(e)}"
            logging.error(error_message)
            return error_message

        finally:
            # Clean up the script file
            if os.path.exists(script_path):
                try:
                    os.remove(script_path)
                    logging.info(f"Deleted temporary Python script: {script_path}")
                except OSError as e:
                    logging.warning(f"Failed to delete script file: {e}")
