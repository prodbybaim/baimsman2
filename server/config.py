from pathlib import Path
from datetime import timezone, timedelta


ROOT = Path(__file__).parent
USERDATA = Path("/var/lib/smandacikpus/")
DB_FILE = USERDATA / "data.db"
PAGEDIR = USERDATA / "page/content"
PREVIEWLIMIT = 10
PREVIEWWORD = 200


# Admin registration token -- change this to a strong secret in production.
ADMIN_REGISTER_TOKEN = "sman2cikpus@admin"

# Session lifetime (days) when 'remember me' is checked
SESSION_LIFETIME_DAYS = 14


# timezone placeholder if needed elsewhere
UTC = timezone.utc
WIB = timezone(timedelta(hours=7), "WIB")