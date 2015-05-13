from urllib import urlencode
# from progress import Progress
import os
import optparse

from speechDownloader import SpeechDownloader

from redis import Redis
from rq import Queue

CWD = os.getcwd()


# This part enables using Pool.map and Pool.apply on
# a function defined in a class
import copy_reg
import types


def _pickle_method(m):
    if m.im_self is None:
        return getattr, (m.im_class, m.im_func.func_name)
    else:
        return getattr, (m.im_self, m.im_func.func_name)

copy_reg.pickle(types.MethodType, _pickle_method)


def parse_args():
    usage = """
        usage: %prog [options]
    """
    parser = optparse.OptionParser(usage)

    help = 'The language of speech to get from text'
    parser.add_option('--lang', type='str', default='es', help=help)

    help = 'The task destination folder'
    parser.add_option('--dir', type='str', help=help)

    options, args = parser.parse_args()

    if len(args):
        parser.error('Bad Arguments')

    if options.dir[-1] != '/':
        options.dir += '/'

    download_path = os.path.join(CWD, options.dir)
    if not os.path.exists(download_path):
        os.mkdir(download_path)

    return options


class SpeechDownloadService(object):

    SPEECH_URL = 'http://translate.google.com/translate_tts?'
    TEXT_FILE_NAME = 'vocabulary.txt'
    DOWNLOAD_DIR_NAME = 'Files'
    DOWNLOAD_FILE_TYPE = '.mp3'
    REQUEST_HEADER = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.90 Safari/537.36'
    }

    # config.vm.network = 'public_network'
    # forwarded ports will not work
    RQWORKER_HOST = '192.168.0.210'
    RQWORKER_PORT = 6379

    # not using public_network
    # use forwarded ports
    RQWORKER_HOST_LOCAL = 'localhost'
    RQWORKER_PORT_LOCAL = 16379

    def __init__(self, language, task_path):
        self._language = language
        self._task_path = task_path
        self._text_file_path = self._task_path + self.TEXT_FILE_NAME
        self._download_dir = self._task_path + self.DOWNLOAD_DIR_NAME

    def setup_download_dir(self):
        download_dir = self._download_dir
        if not os.path.exists(download_dir):
            os.mkdir(download_dir)
        return download_dir

    def start(self):

        print 'Start Speech Download Service...'

        language = self._language
        download_dir = self.setup_download_dir()

        with open(self._text_file_path, 'r') as f:

            # queue = Queue('rqworker', connection=Redis(host=self.RQWORKER_HOST, port=self.RQWORKER_PORT))
            queue = Queue('rqworker', connection=Redis(host=self.RQWORKER_HOST_LOCAL, port=self.RQWORKER_PORT_LOCAL))

            # progress = Progress(len(f.readlines()))
            f.seek(0)
            # results = []

            for text in f:
                text = text.rstrip('\n')
                encoded_args = urlencode({
                    'tl': language,
                    'q': text
                })

                url = self.SPEECH_URL + encoded_args
                download_path = os.path.join(download_dir, text + self.DOWNLOAD_FILE_TYPE)

                downloader = SpeechDownloader(url, self.REQUEST_HEADER, download_path)
                queue.enqueue(downloader.download)

            # print 'Done, Downloaded %d Speeches' % len(results)


def main():
    options = parse_args()
    service = SpeechDownloadService(options.lang, options.dir)
    service.start()


if __name__ == '__main__':
    main()
