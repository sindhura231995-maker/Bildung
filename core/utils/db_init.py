import logging
from django.conf import settings
import MySQLdb

logger = logging.getLogger(__name__)

def ensure_database_exists():
    db_settings = settings.DATABASES['default']
    db_name = db_settings['NAME']

    try:
        conn = MySQLdb.connect(
            host=db_settings['HOST'],
            user=db_settings['USER'],
            passwd=db_settings['PASSWORD'],
        )
        cursor = conn.cursor()

        cursor.execute(f"SHOW DATABASES LIKE '{db_name}';")
        result = cursor.fetchone()

        if result:
            logger.info(f"[DB CHECK] Database '{db_name}' exists.")
        else:
            cursor.execute(f"CREATE DATABASE {db_name};")
            logger.info(f"[DB CREATED] Database '{db_name}' created successfully.")

        cursor.close()
        conn.close()

    except Exception as e:
        logger.error(f"[DB ERROR] {str(e)}")
