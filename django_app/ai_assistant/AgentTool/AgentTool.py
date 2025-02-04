from abc import ABC, abstractmethod
import logging
import os

# Set up logging
logging.basicConfig(level=logging.INFO)

class AgentTool(ABC):
    """
    Abstract base class for Agent Tools.
    """

    def __init__(self, work_dir='./work_directory/'):
        self.work_dir = work_dir
        self._validate_work_dir()

    def _validate_work_dir(self):
        """Ensure the working directory exists."""
        if not os.path.exists(self.work_dir):
            os.makedirs(self.work_dir)
            logging.info(f"Created working directory: {self.work_dir}")

    @abstractmethod
    def process_task(self, task: str) -> str:
        """
        Process the task and return the result.
        """
        pass
