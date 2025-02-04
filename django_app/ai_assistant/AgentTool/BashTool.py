import subprocess
import os
import logging
from .AgentTool import AgentTool

class BashTool(AgentTool):
    """
    Tool for executing Bash commands.
    """

    def process_task(self, task: str) -> str:
        """
        Execute a Bash command and return the output.
        """
        try:
            # Log the task
            logging.info(f"Executing Bash command: {task}")

            # Execute the Bash command
            result = subprocess.run(
                task,
                shell=True,
                check=True,
                capture_output=True,
                text=True,
                cwd=self.work_dir
            )

            # Log and return the result
            logging.info(f"Bash command executed successfully: {result.stdout.strip()}")
            return result.stdout.strip()

        except subprocess.CalledProcessError as e:
            error_message = f"Error executing Bash command: {e.stderr.strip()}"
            logging.error(error_message)
            return error_message

        except FileNotFoundError:
            error_message = f"Error: The directory '{self.work_dir}' does not exist. Please create it."
            logging.error(error_message)
            return error_message
