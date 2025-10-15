import random, uuid, os, requests, yaml
from datetime import datetime, timedelta

totaldata = 0
for i in range(5):
    # API URL
    count = str(random.randint(1,50))
    url = "https://fakerapi.it/api/v2/texts?_quantity="+count+"&_characters=2048"
    base_dir = "/var/lib/smandacikpus/page/content"
    totaldata = totaldata + int(count)

    # Fetch
    res = requests.get(url)
    data = res.json()["data"]

    # Random datetime generator
    def random_datetime(start, end):
        delta = end - start
        seconds = random.randint(0, int(delta.total_seconds()))
        return start + timedelta(seconds=seconds)

    end_date = datetime.now()
    start_date = end_date - timedelta(days=60)

    # Namespace for uuid5
    NAMESPACE = uuid.NAMESPACE_URL

    for entry in data:
        rand_dt = random_datetime(start_date, end_date)

        # Folder path from random datetime
        try:
            folder_path = os.path.join(base_dir, str(rand_dt.year), f"{rand_dt.month:02}", f"{rand_dt.day:02}")
            os.makedirs(folder_path, exist_ok=True)
        except PermissionError as e:
            print(f"Permission error: {e}")
            exit()


        # Generate UUID5 using title + timestamp
        file_uuid = str(uuid.uuid5(NAMESPACE, entry['title'] + str(rand_dt.timestamp())))

        # Markdown content with YAML front matter
        yaml_config = {
            "uuid": file_uuid,
            "title": entry['title'],
            "date": rand_dt.strftime("%Y-%m-%d %H:%M:%S"),
        }
        md_content = f"---\n{yaml.safe_dump(yaml_config)}---\n\n{entry['content']}"

        # Save file with UUID as filename and .md extension
        filepath = os.path.join(folder_path, f"{file_uuid}.md")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(md_content)

    print(f"| {len(data)}")

print(f"\n| {totaldata} Scrapped")