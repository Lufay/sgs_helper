from configparser import ConfigParser
from pathlib import Path

root_path = Path(__file__).parent

conf = ConfigParser()
conf.read(root_path / 'conf.ini')