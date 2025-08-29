import logging
import os

def setup_logging():
    # Use user's home directory for logs instead of app bundle
    user_home = os.path.expanduser('~')
    log_dir = os.path.join(user_home, '.stampz', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'plot3d.log')

    logging.basicConfig(
        filename=log_file,
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

