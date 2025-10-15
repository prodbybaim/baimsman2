from app import create_app as sman2cikpus
import logging, time, threading, os
from collections import deque
from flask import request, g

logging.getLogger("werkzeug").setLevel(logging.ERROR)

app = sman2cikpus()
reqTimes = deque(maxlen=10000)

@app.before_request
def beforeRequest():
    g.start = time.time()

@app.after_request
def afterRequest(response):
    reqTimes.append(time.time())
    return response

def liveMonitor():
    while True:
        now = time.time()
        rps = len([t for t in reqTimes if now - t < 1])
        print(f"{time.strftime('%H:%M:%S')} | {rps} req/s")
        time.sleep(1)

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(message)s")
    app.logger.setLevel(logging.DEBUG)

    # start monitor only in reloader child
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug:
        threading.Thread(target=liveMonitor, daemon=True).start()

    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
