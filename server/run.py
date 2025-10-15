from app import create_app as sman2cikpus

app = sman2cikpus()

if __name__ == "__main__":
# change debug/host/port as needed
    app.run(host="0.0.0.0", port=3293)
    