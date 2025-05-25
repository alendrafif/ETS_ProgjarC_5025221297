import socket
import json
import base64
import logging
import shlex
import os
import time
from concurrent.futures import ThreadPoolExecutor
from multiprocessing import Pool, Manager
import sys
import random

server_address = ('172.16.16.101', 8686)

# Direktori untuk menyimpan file dummy dan file yang diunduh
DUMMY_DIR = "dummyfiles"
if not os.path.exists(DUMMY_DIR):
    os.makedirs(DUMMY_DIR)

# Fungsi untuk mengirim perintah ke server
def send_command(command_str=""):
    global server_address
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect(server_address)
        logging.warning(f"Connecting to {server_address}")
        logging.warning(f"Sending command: {command_str[:50]}...")  # Log hanya 50 karakter pertama
        sock.sendall(command_str.encode())
        data_received = ""
        loading_dots = 0
        while True:
            data = sock.recv(1048576)
            if data:
                data_received += data.decode()
                loading_dots = (loading_dots + 1) % 4
                print(f"\rLoading{'.' * loading_dots}", end="", flush=True)
                if "\r\n\r\n" in data_received:
                    break
            else:
                break
        print("\rDone          ")  # Bersihkan baris dan hapus loading dots
        logging.warning(f"Received raw: {data_received[:50]}...")  # Log hanya 50 karakter pertama
        hasil = json.loads(data_received)
        return hasil
    except Exception as e:
        logging.warning(f"Error during data receiving: {str(e)}")
        return {'status': 'ERROR', 'data': str(e)}
    finally:
        sock.close()

# Fungsi untuk mengirim konfigurasi ke server
def send_config(mode, workers):
    command_str = f"CONFIG {mode} {workers}\r\n\r\n"
    result = send_command(command_str)
    if result['status'] != 'OK':
        logging.warning(f"Failed to configure server: {result['data']}")
        sys.exit(1)
    logging.warning("Server configured successfully")

# Fungsi untuk operasi LIST
def remote_list():
    command_str = "LIST\r\n\r\n"  # Pastikan ada \r\n\r\n untuk konsistensi protokol
    hasil = send_command(command_str)
    if hasil['status'] == 'OK':
        logging.warning("Daftar file:")
        for nmfile in hasil['data']:
            logging.warning(f"- {nmfile}")
        return hasil
    else:
        logging.warning(f"Gagal: {hasil['data']}")
        return False

# Fungsi untuk operasi GET (download)
def remote_get(filename=""):
    start_time = time.time()
    command_str = f"GET {filename}\r\n\r\n"
    logging.warning(f"Attempting to download: {filename}")
    hasil = send_command(command_str)
    end_time = time.time()
    if hasil['status'] == 'OK':
        namafile = hasil['data_namafile']
        isifile = base64.b64decode(hasil['data_file'])
        full_path = os.path.join(DUMMY_DIR, f"downloaded_{namafile}")
        with open(full_path, 'wb') as fp:
            fp.write(isifile)
        total_time = end_time - start_time
        file_size = len(isifile)
        throughput = file_size / total_time if total_time > 0 else 0
        logging.warning(f"Successfully downloaded: {full_path}")
        logging.warning(f"Downloaded file size: {file_size} bytes ({file_size / (1024 * 1024):.2f}MB)")
        return True, total_time, throughput
    else:
        logging.warning(f"Failed to download {filename}: {hasil['data']}")
        return False, end_time - start_time, 0

# Fungsi untuk operasi UPLOAD
def remote_upload(filename=""):
    start_time = time.time()
    try:
        full_path = os.path.join(DUMMY_DIR, filename)
        with open(full_path, 'rb') as fp:
            filecontent = base64.b64encode(fp.read()).decode()
        command_str = f"UPLOAD {filename} {shlex.quote(filecontent)}\r\n\r\n"
        logging.warning(f"Starting upload for: {filename} (size: {os.path.getsize(full_path)} bytes)")
        hasil = send_command(command_str)
        end_time = time.time()
        if hasil['status'] == 'OK':
            logging.warning(f"Upload completed: {filename}")
            file_size = os.path.getsize(full_path)
            total_time = end_time - start_time
            throughput = file_size / total_time if total_time > 0 else 0
            return True, total_time, throughput
        else:
            logging.warning(f"Upload failed for {filename}: {hasil['data']}")
            return False, end_time - start_time, 0
    except Exception as e:
        logging.warning(f"Error uploading {filename}: {str(e)}")
        end_time = time.time()
        return False, end_time - start_time, 0

# Fungsi untuk menjalankan operasi (digunakan oleh thread/process) dengan retry
def run_operation(op_type, filename, success_counter=None, failure_counter=None, max_retries=3):
    for attempt in range(max_retries):
        try:
            if op_type == "upload":
                success, total_time, throughput = remote_upload(filename)
            elif op_type == "download":
                success, total_time, throughput = remote_get(filename)
            else:
                raise ValueError(f"Unknown operation: {op_type}")
            
            if success:
                if success_counter is not None:
                    success_counter.value += 1  # Hapus get_lock(), gunakan value langsung
                return total_time, throughput
            else:
                if failure_counter is not None and attempt == max_retries - 1:
                    failure_counter.value += 1  # Hapus get_lock(), gunakan value langsung
                time.sleep(1)  # Tunggu sebelum mencoba ulang
        except Exception as e:
            logging.warning(f"Error in {op_type} for {filename} (attempt {attempt + 1}/{max_retries}): {e}")
            if failure_counter is not None and attempt == max_retries - 1:
                failure_counter.value += 1  # Hapus get_lock(), gunakan value langsung
            time.sleep(1)  # Tunggu sebelum mencoba ulang
    return time.time() - time.time(), 0

# Fungsi untuk stress test
def stress_test(mode, workers, op_type, file_size_mb, num_files=1):
    filenames = []
    if op_type == "upload":
        for i in range(num_files):
            filename = f"dummy_{file_size_mb}mb_{i}.dat"
            full_path = os.path.join(DUMMY_DIR, filename)
            if os.path.exists(full_path):
                filenames.append(filename)
            else:
                logging.warning(f"File {full_path} not found. Please create dummy files using create_dummy.py first.")
                return None
    else:
        list_result = remote_list()
        if list_result and 'data' in list_result:
            filenames = [f for f in list_result['data'] if f.startswith('dummy_') and str(file_size_mb).lower() + 'mb' in f.lower()]
            if not filenames:
                logging.warning(f"No files available for download with size {file_size_mb}MB. Please upload files first.")
                return None
            filenames = [filenames[0]] * workers if filenames else []
        else:
            logging.warning("Failed to get file list from server.")
            return None

    manager = Manager()
    success_counter = manager.Value('i', 0)
    failure_counter = manager.Value('i', 0)

    total_times = []
    throughputs = []

    start_time = time.time()
    logging.warning(f"Starting {op_type} operation with {workers} {mode} workers for {file_size_mb}MB file(s)")

    if mode == 'thread':
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = []
            for _ in range(workers):
                futures.append(executor.submit(run_operation, op_type, filenames[0], success_counter, failure_counter))
            for future in futures:
                total_time, throughput = future.result()
                total_times.append(total_time)
                throughputs.append(throughput)

    elif mode == 'process':
        with Pool(processes=workers) as pool:
            results = []
            for _ in range(workers):
                results.append(pool.apply_async(run_operation, (op_type, filenames[0], success_counter, failure_counter)))
            for r in results:
                total_time, throughput = r.get()
                total_times.append(total_time)
                throughputs.append(throughput)

    else:
        raise ValueError("Mode must be 'thread' or 'process'")

    end_time = time.time()
    total_duration = end_time - start_time
    avg_time = sum(total_times) / len(total_times) if total_times else 0
    avg_throughput = sum(throughputs) / len(throughputs) if throughputs and sum(throughputs) > 0 else 0

    return {
        'total_time': total_duration,
        'avg_time_per_client': avg_time,
        'avg_throughput_per_client': avg_throughput,
        'successful_clients': success_counter.value,
        'failed_clients': failure_counter.value
    }

def main():
    import logging  # Impor logging di sini untuk memastikan tersedia
    logging.basicConfig(level=logging.WARNING)
    if len(sys.argv) != 5:
        print("Usage: python client.py <mode: thread/process> <workers: 1/5/50> <operation: upload/download> <file_size_mb: 10/50/100>")
        sys.exit(1)

    mode = sys.argv[1].lower()
    workers = int(sys.argv[2])
    op_type = sys.argv[3].lower()
    file_size_mb = int(sys.argv[4])

    if mode not in ["thread", "process"]:
        print("Mode must be 'thread' or 'process'")
        sys.exit(1)
    if workers not in [1, 5, 50]:
        print("Workers must be 1, 5, or 50")
        sys.exit(1)
    if op_type not in ["upload", "download"]:
        print("Operation must be 'upload' or 'download'")
        sys.exit(1)
    if file_size_mb not in [10, 50, 100]:
        print("File size must be 10, 50, or 100 MB")
        sys.exit(1)

    # Kirim konfigurasi ke server (meskipun diabaikan, untuk kompatibilitas)
    send_config(mode, workers)

    num_files = 1
    result = stress_test(mode, workers, op_type, file_size_mb, num_files)
    if result:
        print(f"Task: {op_type}")
        print(f"File Size: {file_size_mb}MB")
        print(f"Mode: {mode}")
        print(f"Workers: {workers}")
        print(f"Total Time: {result['total_time']:.2f} seconds")
        print(f"Average Time per Client: {result['avg_time_per_client']:.2f} seconds")
        print(f"Average Throughput per Client: {result['avg_throughput_per_client']:.2f} bytes/second")
        print(f"Successful Clients: {result['successful_clients']}")
        print(f"Failed Clients: {result['failed_clients']}")

if __name__ == '__main__':
    main()