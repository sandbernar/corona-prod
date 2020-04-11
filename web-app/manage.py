import os
from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand

from config import config_dict
from run import app, db


get_config_mode = os.environ.get('CONFIG_MODE', 'Debug')
config_mode = config_dict[get_config_mode.capitalize()]

app.config.from_object(config_mode)

migrate = Migrate(app, db)
manager = Manager(app)

manager.add_command('db', MigrateCommand)

if __name__ == '__main__':
    manager.run()
