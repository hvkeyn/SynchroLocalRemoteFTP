import os
import paramiko
from stat import S_ISDIR, S_ISREG

# Параметры подключения
hostname = 'xxx.xxx.xxx.xxx'  # Адрес удаленного сервера
port = 22  # Порт SFTP
username = 'username' # Логин SFTP
password = 'password' # Пароль SFTP
local_directory = 'E:\\WinPatch'
remote_directory = '/var/www/html/LinuxPatch'

def sftp_walk(sftp, remotepath):
    path = remotepath
    files = []
    folders = []
    for entry in sftp.listdir_attr(remotepath):
        if entry.filename in ('.', '..'):
            continue
        if S_ISDIR(entry.st_mode):
            folders.append(entry.filename)
        else:
            files.append((entry.filename, entry.st_mtime))
    yield path, folders, files
    for folder in folders:
        new_path = os.path.join(remotepath, folder).replace('\\', '/')
        for x in sftp_walk(sftp, new_path):
            yield x

def synchronize(sftp, local_dir, remote_dir):
    try:
        sftp.chdir(remote_dir)
    except IOError:
        sftp.mkdir(remote_dir)
        sftp.chdir(remote_dir)

    print(f"1. Synhro {local_dir} to {remote_dir}...\n")
    for root, dirs, files in os.walk(local_dir):
        relpath = os.path.relpath(root, local_dir)
        remote_path = os.path.join(remote_dir, relpath).replace('\\', '/')
        print(f"Syncing {relpath} to {remote_path}")

        try:
            sftp.chdir(remote_path)
        except IOError:
            sftp.mkdir(remote_path)
            sftp.chdir(remote_path)

        for file in files:
            local_file_path = os.path.join(root, file)
            remote_file_path = os.path.join(remote_path, file).replace('\\', '/')
            try:
                remote_stat = sftp.stat(remote_file_path)
                local_stat = os.stat(local_file_path)
                local_mtime = local_stat.st_mtime
                remote_mtime = remote_stat.st_mtime
                if local_mtime > remote_mtime:
                    sftp.put(local_file_path, remote_file_path)
                    print(f"Uploaded {local_file_path} (newer) to {remote_file_path}")
                # Optionally implement else branch if needed
            except IOError:
                sftp.put(local_file_path, remote_file_path)
                print(f"Uploaded {local_file_path} to {remote_file_path} (new)")

    print(f"2. Synhro {remote_dir} to {local_dir}...\n")
    for remote_root, dirs, files in sftp_walk(sftp, remote_dir):
        relpath = os.path.relpath(remote_root, remote_dir)
        local_path = os.path.join(local_dir, relpath).replace('\\', '/')
        print(f"Syncing {relpath} to {local_path}")

        if not os.path.exists(local_path):
            os.makedirs(local_path)

        for file, remote_mtime in files:
            remote_file_path = os.path.join(remote_root, file).replace('\\', '/')
            local_file_path = os.path.join(local_path, file)
            try:
                local_stat = os.stat(local_file_path)
                local_mtime = local_stat.st_mtime
                if remote_mtime > local_mtime:
                    sftp.get(remote_file_path, local_file_path)
                    print(f"Downloaded {remote_file_path} (newer) to {local_file_path}")
                # Optionally implement else branch if needed
            except FileNotFoundError:
                sftp.get(remote_file_path, local_file_path)
                print(f"Downloaded {remote_file_path} to {local_file_path} (new)")

# Установка подключения
transport = paramiko.Transport((hostname, port))
transport.connect(username=username, password=password)

sftp = paramiko.SFTPClient.from_transport(transport)

try:
    synchronize(sftp, local_directory, remote_directory)
finally:
    sftp.close()
    transport.close()

print(">>> Synchronization complete <<<")