from datetime import datetime as dt
import json
import logging
import logging.handlers
import os
import pprint


class Logger:
    def __init__(self, name, streamHandler=True):

        self.makeFolder()
        filePath = "log/{}.txt".format(dt.now().strftime("%Y%m%d"))

        # 로깅용 설정파일
        self.__logger = logging.getLogger(name)
        self.__logger.setLevel(logging.DEBUG)

        fileHandler = logging.FileHandler(filePath)
        self.__logger.addHandler(fileHandler)

        if streamHandler:
            streamHandler = logging.StreamHandler()
            self.__logger.addHandler(streamHandler)

    def makeFolder(self):
        try:
            os.mkdir("log")
        except FileExistsError:
            pass

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
        return pprint.pformat(msg)
