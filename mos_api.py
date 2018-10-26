# coding: utf-8
from __future__ import unicode_literals

import settings
from emp_mos_api import MosAPI

mos_api = MosAPI(token=settings.EMP_MOS_RU_TOKEN,
                 user_agent=settings.EMP_MOS_RU_USER_AGENT,
                 guid=settings.EMP_MOS_RU_GUID,
                 dev_user_agent=settings.EMP_MOS_RU_DEV_USER_AGENT,
                 dev_app_version=settings.EMP_MOS_RU_APP_VER,
                 https_verify=True)