import socket
import json
import base64
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from multiprocessing import Manager
from io import BufferedWriter

class FileServer:
    def __init__(self, host='0.0.0.0', port=8686, workers=1):
        self.host = host
        self.port = port
        self.my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)  # 64 KB
        self.my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)  # 64 KB
        self.storage_dir = "./storedfiles"
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)
        self.workers = workers
        self.manager = Manager()
        self.successful_operations = self.manager.Value('i', 0)
        self.failed_operations = self.manager.Value('i', 0)
        logging.basicConfig(level=logging.WARNING)

    def configure(self, mode, workers):
        # Abaikan perubahan workers dari client
        logging.warning(f"Configuration ignored, workers set to {self.workers} at startup")
        return {"status": "OK", "data": f"Configuration accepted with {self.workers} workers"}

    def list_files(self):
        files = [f for f in os.listdir(self.storage_dir) if os.path.isfile(os.path.join(self.storage_dir, f))]
        return {"status": "OK", "data": files}

    def get_file(self, filename):
        full_path = os.path.join(self.storage_dir, filename)
        if os.path.isfile(full_path):
            with open(full_path, 'rb') as fp:
                file_content = base64.b64encode(fp.read()).decode()
            return {"status": "OK", "data_namafile": filename, "data_file": file_content}
        else:
            return {"status": "ERROR", "data": f"File {filename} not found"}

    def upload_file(self, filename, filecontent):
        full_path = os.path.join(self.storage_dir, filename)
        total_size = len(base64.b64decode(filecontent))
        chunk_size = 4 * 1024 * 1024  # 4 MB chunks
        decoded_content = base64.b64decode(filecontent)

        with open(full_path, 'wb') as fp:
            buffered_fp = BufferedWriter(fp, buffer_size=8192 * 1024)  # 8 MB buffer
            for i in range(0, total_size, chunk_size):
                chunk = decoded_content[i:i + chunk_size]
                buffered_fp.write(chunk)
                progress = min((i + len(chunk)) / total_size * 100, 100)
                bar_length = 50
                filled_length = int(bar_length * progress / 100)
                bar = '#' * filled_length + '-' * (bar_length - filled_length)
                print(f'\rUploading {filename}: [{bar}] {progress:.1f}%', end='', flush=True)
            buffered_fp.flush()
        print()
        return {"status": "OK", "data": f"File {filename} uploaded successfully"}

    def process_request(self, connection):
        data_received = ""
        while True:
            data = connection.recv(1048576)  # 16 KB buffer
            if data:
                data_received += data.decode()
                if "\r\n\r\n" in data_received:
                    break
            else:
                break

        try:
            command = data_received.strip().split()
            response = {"status": "ERROR", "data": "Unknown command"}

            if not command:
                response = {"status": "ERROR", "data": "Empty command"}
            elif command[0] == "CONFIG":
                response = self.configure(command[1], int(command[2]))
            elif command[0] == "LIST":
                response = self.list_files()
            elif command[0] == "GET":
                response = self.get_file(command[1])
            elif command[0] == "UPLOAD":
                filename = command[1]
                filecontent = " ".join(command[2:]).strip()
                response = self.upload_file(filename, filecontent)
            else:
                response = {"status": "ERROR", "data": "Invalid command"}

            connection.sendall(json.dumps(response).encode() + b"\r\n\r\n")
            return True
        except Exception as e:
            logging.warning(f"Error processing client {connection.getpeername()}: {str(e)}")
            response = {"status": "ERROR", "data": str(e)}
            connection.sendall(json.dumps(response).encode() + b"\r\n\r\n")
            return False
        finally:
            connection.close()

    def update_counters(self, future):
        if future.result():
            self.successful_operations.value += 1
        else:
            self.failed_operations.value += 1

    def run(self):
        self.my_socket.bind((self.host, self.port))
        self.my_socket.listen(5)
        logging.warning(f"Server listening on {self.host}:{self.port} with {self.workers} workers")

        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            while True:
                try:
                    connection, client_address = self.my_socket.accept()
                    logging.warning(f"Connection from {client_address}")
                    future = executor.submit(self.process_request, connection)
                    future.add_done_callback(self.update_counters)
                    logging.warning(f"Server - Successful Operations: {self.successful_operations.value}, Failed Operations: {self.failed_operations.value}")
                except KeyboardInterrupt:
                    logging.warning("Server shutting down")
                    break
                except Exception as e:
                    logging.warning(f"Error: {str(e)}")
        self.my_socket.close()

def main():
    if len(sys.argv) != 2:
        print("Usage: python file_server.py <workers: 1/5/50>")
        sys.exit(1)
    workers = int(sys.argv[1])
    if workers not in [1, 5, 50]:
        print("Workers must be 1, 5, or 50")
        sys.exit(1)
    svr = FileServer(workers=workers)
    svr.run()

if __name__ == '__main__':
    main()