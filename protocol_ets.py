import json
import logging

from file_interface import FileInterface

class FileProtocol:
    def __init__(self):
        self.filehandler = FileInterface()

    def proses_string(self, string_datamasuk=''):
        logging.warning(f"string diproses: {string_datamasuk}")

        if not string_datamasuk:
            return json.dumps(dict(status='ERROR', data='Empty command'))

        tokens = string_datamasuk.strip().split(" ", 2)
        command = tokens[0].upper()

        try:
            if command == "LIST":
                result = self.filehandler.list()
                if result['status'] == 'OK':
                    return json.dumps(dict(status='OK', data=result['data']))
                return json.dumps(result)

            elif command == "GET":
                if len(tokens) < 2:
                    return json.dumps(dict(status='ERROR', data='GET but no filename'))
                filename = tokens[1]
                result = self.filehandler.get([filename])
                if result['status'] == 'OK':
                    return json.dumps(dict(status='OK', data_namafile=result['data_namafile'], data_file=result['data_file']))
                return json.dumps(result)

            elif command == "DELETE":
                if len(tokens) < 2:
                    return json.dumps(dict(status='ERROR', data='DELETE but no filename'))
                filename = tokens[1]
                result = self.filehandler.delete([filename])
                return json.dumps(result)

            elif command == "UPLOAD":
                if len(tokens) < 3:
                    return json.dumps(dict(status='ERROR', data='UPLOAD format salah'))
                filename = tokens[1]
                filedata = tokens[2]
                result = self.filehandler.upload([filename, filedata])
                return json.dumps(result)

            else:
                return json.dumps(dict(status='ERROR', data=f'Unknown command: {command}'))

        except AttributeError as e:
            logging.warning(f"Error saat proses: {e}")
            return json.dumps(dict(status='ERROR', data=f'Method not implemented: {str(e)}'))
        except Exception as e:
            logging.warning(f"Error saat proses: {e}")
            return json.dumps(dict(status='ERROR', data='request tidak dikenali'))