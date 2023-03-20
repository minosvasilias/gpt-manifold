import logging
import os
from datetime import datetime


class LogSession:
    def __init__(self):
        self.logfile = None
        self.logger = None

    def start_session(self):
        date_str = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        log_filename = f"gpt_manifold_{date_str}.log"
        self.logfile = os.path.join(os.getcwd(), log_filename)

        logging.basicConfig(filename=self.logfile, level=logging.INFO,
                            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S')
        self.logger = logging.getLogger('Log Session')

    def write_message(self, tag, message):
        if self.logger is None:
            return
        self.logger.info(f"[{tag}]\n\n{message}\n\n")

    def end_session(self):
        if self.logger is None:
            return

        logging.shutdown()
        self.logger = None
