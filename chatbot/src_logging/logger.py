import logging
import os
from datetime import datetime

LOG_FILE=f"{datetime.now().strftime('%m__%d__%Y__%H__%M__%S')}.log"

log_path=os.path.join(os.getcwd(), "logs", LOG_FILE)
os.makedirs(log_path, exist_ok=True)

LOG_PATH_FILE=os.path.join(log_path, LOG_FILE)

logging.basicConfig(
    filename=LOG_PATH_FILE,
    format="[%(asctime)s] %(lineno)d %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)