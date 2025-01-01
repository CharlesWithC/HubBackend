# Copyright (C) 2022-2025 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import logging

from uvicorn import logging as ulg

logger = logging.getLogger("uvicorn")
logger.setLevel(logging.INFO)
logger.propagate = False

handler = logging.StreamHandler()
handler.setLevel(logging.INFO)

handler.setFormatter(ulg.ColourizedFormatter(fmt="%(levelprefix)s %(message)s", use_colors=True))

logger.addHandler(handler)
