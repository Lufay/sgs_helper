from configparser import ConfigParser
import logging.config
from pathlib import Path

root_path = Path(__file__).parent

conf = ConfigParser()
conf.optionxform = str
conf.read(root_path / 'conf.ini')

logging.config.fileConfig(root_path / 'log/log_conf.ini')

process_pool = None
manager = None

runtime_env = {}

if __name__ == '__main__':
    from biz.user import UserMgr
    UserMgr.load(conf['Local']['UserRcordPath'])
    print(UserMgr.user_dict)