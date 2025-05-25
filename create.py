import os
import logging
import sys

# Direktori untuk menyimpan file dummy
DUMMY_DIR = "dummyfiles"

# Fungsi untuk membuat file dummy dengan ukuran tertentu (dalam MB)
def create_dummy_file(filename, size_mb):
    if not os.path.exists(DUMMY_DIR):
        os.makedirs(DUMMY_DIR)
    
    size_bytes = size_mb * 1024 * 1024  # Konversi MB ke bytes
    full_path = os.path.join(DUMMY_DIR, filename)
    
    with open(full_path, 'wb') as f:
        # Tulis data dummy hingga mencapai ukuran yang diinginkan
        bytes_written = 0
        chunk_size = 1024 * 1024  # Tulis 1MB per iterasi
        while bytes_written < size_bytes:
            remaining = min(chunk_size, size_bytes - bytes_written)
            f.write(os.urandom(remaining))
            bytes_written += remaining
    
    # Verifikasi ukuran file
    actual_size = os.path.getsize(full_path)
    logging.warning(f"Created dummy file: {full_path}, size: {actual_size} bytes ({actual_size / (1024 * 1024):.2f}MB)")
    return actual_size

def main():
    logging.basicConfig(level=logging.WARNING)
    
    if len(sys.argv) != 2:
        print("Usage: python create_dummy.py <prefix>")
        print("Example: python create_dummy.py dummy")
        print("This will create one file each of sizes 10MB, 50MB, and 100MB with the given prefix.")
        sys.exit(1)

    prefix = sys.argv[1]

    # Daftar ukuran file yang akan dibuat (10MB, 50MB, 100MB)
    file_sizes_mb = [10, 50, 100]

    # Buat satu file untuk setiap ukuran
    for size_mb in file_sizes_mb:
        filename = f"{prefix}_{size_mb}mb_0.dat"
        create_dummy_file(filename, size_mb)

if __name__ == "__main__":
    main()