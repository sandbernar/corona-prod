from app import constants as c
from app import db
from datetime import datetime
from flask_babelex import _
import dateparser

from app.main.downloads.models import Download

def start_task(user, download_name, task_id):
    download = Download(user_id = user.id, download_name = download_name, task_id = task_id)
    
    db.session.add(download)
    db.session.commit()

    return download

def finish_task(data, task_id, filename):
    pass
    # output = io.BytesIO()
    # writer = pd.ExcelWriter(output, engine='xlsxwriter')
    # data.to_excel(writer, index=False)

    # writer.save()
    # xlsx_data = output.getvalue()