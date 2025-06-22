import uplink_python

ACCESS_GRANT = "твой_access_grant_сюда"
bucket_name = "videobucket"
filename = "example_video.mp4"
local_path = "/путь/к/локальному/файлу/example_video.mp4"

def upload_file():
    access = uplink_python.Access.from_access_grant(ACCESS_GRANT)
    uplink = uplink_python.Uplink(access)

    with uplink.open_bucket(bucket_name) as bucket:
        with open(local_path, "rb") as f:
            with bucket.upload_object(filename) as upload:
                while True:
                    chunk = f.read(4096)
                    if not chunk:
                        break
                    upload.write(chunk)
                print(f"Файл {filename} загружен!")

if __name__ == "__main__":
    upload_file()
