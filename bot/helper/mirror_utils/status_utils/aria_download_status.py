from time import time

from bot import LOGGER, aria2
from bot.helper.ext_utils.bot_utils import (MirrorStatus, get_readable_time,
                                            sync_to_async)


def get_download(gid):
    try:
        return aria2.get_download(gid)
    except Exception as e:
        LOGGER.error(f'{e}: Aria2c, Error while getting torrent info')
        return get_download(gid)

engine_ = f"Aria2c v{aria2.client.get_version()['version']}"

class AriaDownloadStatus:

    def __init__(self, gid, listener, seeding=False):
        self.__gid = gid
        self.__download = get_download(gid)
        self.__listener = listener
        self.start_time = 0
        self.seeding = seeding
        self.message = listener.message
        self.startTime = self.__listener.startTime
        self.mode = self.__listener.mode
        self.source = self.__listener.source
        self.engine = engine_

    def __update(self):
        if self.__download is None:
            self.__download = get_download(self.__gid)
        elif self.__download.followed_by_ids:
            self.__gid = self.__download.followed_by_ids[0]
            self.__download = get_download(self.__gid)
        else:
            self.__download = self.__download.live

    def progress(self):
        """
        Calculates the progress of the mirror (upload or download)
        :return: returns progress in percentage
        """
        return self.__download.progress_string()

    def size_raw(self):
        """
        Gets total size of the mirror file/folder
        :return: total size of mirror
        """
        return self.__download.total_length

    def processed_bytes(self):
        return self.__download.completed_length

    def speed(self):
        self.__update()
        return self.__download.download_speed_string()

    def name(self):
        return self.__download.name

    def size(self):
        return self.__download.total_length_string()

    def eta(self):
        return self.__download.eta_string()

    def status(self):
        self.__update()
        download = self.__download
        if download.is_waiting:
            return MirrorStatus.STATUS_QUEUEDL
        elif download.is_paused:
            return MirrorStatus.STATUS_PAUSED
        elif download.seeder and self.seeding:
            return MirrorStatus.STATUS_SEEDING
        else:
            return MirrorStatus.STATUS_DOWNLOADING

    def seeders_num(self):
        return self.__download.num_seeders

    def leechers_num(self):
        return self.__download.connections

    def uploaded_bytes(self):
        return self.__download.upload_length_string()

    def upload_speed(self):
        self.__update()
        return self.__download.upload_speed_string()

    def ratio(self):
        return f"{round(self.__download.upload_length / self.__download.completed_length, 3)}"

    def seeding_time(self):
        return f"{get_readable_time(time() - self.start_time)}"

    def download(self):
        return self

    def listener(self):
        return self.__listener

    def gid(self):
        self.__update()
        return self.__gid

    async def cancel_download(self):
        await sync_to_async(self.__update)
        if self.__download.seeder and self.seeding:
            LOGGER.info(f"Cancelling Seed: {self.name()}")
            await self.__listener.onUploadError(f"Seeding stopped with Ratio: {self.ratio()} and Time: {self.seeding_time()}")
            await sync_to_async(aria2.remove, [self.__download], force=True, files=True)
        elif downloads := self.__download.followed_by:
            LOGGER.info(f"Cancelling Download: {self.name()}")
            await self.__listener.onDownloadError('Download cancelled by user!')
            downloads.append(self.__download)
            await sync_to_async(aria2.remove, downloads, force=True, files=True)
        else:
            LOGGER.info(f"Cancelling Download: {self.name()}")
            await self.__listener.onDownloadError('Download stopped by user!')
            await sync_to_async(aria2.remove, [self.__download], force=True, files=True)