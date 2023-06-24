from configparser import ConfigParser
from pathlib import Path

root_path = Path(__file__).parent

conf = ConfigParser()
conf.read(root_path / 'conf.ini')

if __name__ == '__main__':
    from biz.user import UserMgr
    UserMgr.load(conf['Local']['UserRcordPath'])
    print(UserMgr.user_dict)