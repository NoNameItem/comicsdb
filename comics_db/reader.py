import re
import zipfile
import tarfile
import rarfile


CBR, CBT, CBZ = range(3)


class WrongFileTypeError(Exception):
    pass


def file_type(name):
    try:
        if zipfile.is_zipfile(name):
            return CBZ
        elif rarfile.is_rarfile(name):
            return CBR
        else:
            raise WrongFileTypeError('Unknown archive format')
    except WrongFileTypeError:
        raise
    except Exception as err:
        raise WrongFileTypeError('Wrong file %0s' % name)


class ComicsReader:
    """
    Class for working with comics cbr/cbz/cbt files
    """
    def __init__(self, filename):
        """
        Construictor

        :param filename: Python file-like object with comic archive
        """
        self._type = file_type(filename)
        self._files = []
        self._image_re = re.compile(r'\.(jpg|jpeg|png|gif|tif|tiff|bmp)\s*$', re.I)

        if self._type == CBZ:
            self._zip_file = zipfile.ZipFile(filename)
            self._files = [x.filename for x in self._zip_file.infolist() if not x.is_dir()
                           and self._image_re.search(x.filename)]
        elif self._type == CBT:
            self._tar_file = tarfile.TarFile.open(filename)
            self._files = [x.filename for x in self._tar_file.getmembers() if x.isfile()
                           and self._image_re.search(x.filename)]
        elif self._type == CBR:
            self._rar_file = rarfile.RarFile(filename)
            self._files = [x.filename for x in self._rar_file.infolist() if not x.isdir()
                           and self._image_re.search(x.filename)]
        self._files.sort()

    def get_file_list(self):
        return self._files

    def get_page_file(self, page_number=0):
        if self._type == CBZ:
            return self._zip_file.open(self._files[page_number])
        elif self._type == CBT:
            return self._tar_file.extractfile(self._files[page_number])
        elif self._type == CBR:
            return self._rar_file.open(self._files[page_number])
        return None

    def close(self):
        if self._type == CBZ:
            self._zip_file.close()
        elif self._type == CBT:
            return self._tar_file.close()
        elif self._type == CBR:
            return self._rar_file.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

