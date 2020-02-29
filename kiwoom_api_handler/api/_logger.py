import logging
import logging.handlers


class Logger():

    def __init__(self, name, filePath, streamHandler=False):
        # 로깅용 설정파일
        self.__logger = logging.getLogger(name)
        self.__logger.setLevel(logging.DEBUG)

        fileHandler = logging.FileHandler(filePath)
        self.__logger.addHandler(fileHandler)

        if streamHandler:
            streamHandler = logging.StreamHandler()
            self.__logger.addHandler(streamHandler)

    def debug(self, msg):
        self.__logger.debug(msg)

    def info(self, msg):
        self.__logger.info(msg)

    def warning(self, msg):
        self.__logger.warning(msg)

    def error(self, msg):
        self.__logger.error(msg)

    def critical(self, msg):
        self.__logger.critical(msg)
