import os
import json
import base64
from glob import glob


class FileInterface:
    def __init__(self):
        os.chdir('files/')

    def list(self, params=[]):
        try:
            filelist = glob('*.*')
            return dict(status='OK', data=filelist)
        except Exception as e:
            return dict(status='ERROR', data=str(e))

    def get(self, params=[]):
        try:
            filename = params[0]
            if filename == '':
                return None
            with open(f"{filename}", 'rb') as fp:
                isifile = base64.b64encode(fp.read()).decode()
            return dict(status='OK', data_namafile=filename, data_file=isifile)
        except Exception as e:
            return dict(status='ERROR', data=str(e))

    def upload(self, params=[]):
        try:
            filename = params[0]
            filecontent = params[1]
            if filename == '':
                return dict(status='ERROR', data='Filename cannot be empty')
            with open(f"{filename}", 'wb') as fp:
                fp.write(base64.b64decode(filecontent))
            return dict(status='OK', data=f"File {filename} uploaded successfully")
        except Exception as e:
            return dict(status='ERROR', data=str(e))

    def delete(self, params=[]):
        try:
            filename = params[0]
            if filename == '':
                return dict(status='ERROR', data='Filename cannot be empty')
            if not os.path.exists(filename):
                return dict(status='ERROR', data=f"File {filename} does not exist")
            os.remove(filename)
            return dict(status='OK', data=f"File {filename} deleted successfully")
        except Exception as e:
            return dict(status='ERROR', data=str(e))


if __name__ == '__main__':
    f = FileInterface()
    print(f.list())
    print(f.get(['pokijan.jpg']))