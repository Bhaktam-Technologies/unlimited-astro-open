# astro-wrapper — Copyright (C) 2026 Bhaktam Technologies
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE and NOTICE in the project root for full terms.

import logging
import logging.handlers as handlers


def getLoggerForApp():
    logger = logging.getLogger('astro_open')
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    logHandler = handlers.TimedRotatingFileHandler('logger/normal.log', when='D', interval=1, backupCount=0)
    logHandler.setLevel(logging.INFO)
    logHandler.setFormatter(formatter)

    errorLogHandler = handlers.RotatingFileHandler('logger/error.log', maxBytes=5000, backupCount=0)
    errorLogHandler.setLevel(logging.ERROR)
    errorLogHandler.setFormatter(formatter)

    logger.addHandler(logHandler)
    logger.addHandler(errorLogHandler)
    return logger
