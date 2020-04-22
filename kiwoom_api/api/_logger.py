from datetime import datetime as dt
import json
import logging
import logging.handlers
import os
import pprint
import queue


class Logger:
    def __init__(self, path, name=""):
        self.propagate = 0
        self.makeLogFolder(path)

        filePath = "{}/{}.txt".format(path, dt.now().strftime("%Y%m%d"))

        # 로깅용 설정파일
        self.__logger = logging.getLogger(name)
        self.__logger.setLevel(logging.DEBUG)

        fileHandler = logging.FileHandler(filePath)
        self.__logger.addHandler(fileHandler)

        streamHandler = logging.StreamHandler()
        self.__logger.addHandler(streamHandler)

        #log_que = queue.Queue(-1)
        #queueListener = logging.handlers.QueueListener(log_que, streamHandler, fileHandler, streamHandler)
        #queueListener.start()

        #queueHandler = logging.handlers.QueueHandler(log_que)
        #self.__logger.addHandler(queueHandler)

    def makeLogFolder(self, path):
        if not os.path.exists(path):
            os.mkdir(path)

    def debug(self, msg, pretty=True):
        if pretty:
            msg = self.make_pretty(msg)

        self.__logger.debug(msg)

    def info(self, msg, pretty=True):
        if pretty:
            msg = self.make_pretty(msg)

        self.__logger.info(msg)

    def warning(self, msg, pretty=True):
        if pretty:
            msg = self.make_pretty(msg)

        self.__logger.warning(msg)

    def error(self, msg, pretty=True):
        if pretty:
            msg = self.make_pretty(msg)

        self.__logger.error(msg)

    def critical(self, msg, pretty=True):
        if pretty:
            msg = self.make_pretty(msg)

        self.__logger.critical(msg)

    def make_pretty(self, msg):
        if isinstance(msg, str):
            return msg
        return pprint.pformat(msg)
