from pathlib import Path
from datetime import timezone


ROOT = Path(__file__).parent
USERDATA = Path("/var/lib/smandacikpus/")
DB_FILE = USERDATA / "articles.db"
DB_AUTH_FILE = USERDATA / "auth.db"
PAGEDIR = USERDATA / "page/content"
PAGESHOW = 10
PAGEPREVIEW = 200


# timezone placeholder if needed elsewhere
UTC = timezone.utc