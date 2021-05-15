import asyncio
import aiohttp
import os
from errors import StatusError
from log import log


class Downloader:
    def __init__(self):
        self.retryMap = {}
        self.fragRetryMax = 3

    async def downloadFrag(self, session, remoteUrl, storagePath, referer, fragLen):
        storageDir = '/'.join(storagePath.split('/')[:-1])
        if not os.path.exists(storageDir):
            os.mkdir(storageDir)
        try:
            timeoutLen = max(fragLen * 3, 15)
            headers = None
            if referer:
                headers = {'Referer': referer, 'Origin': referer}
            chunk_size = 56384
            async with session.get(remoteUrl, headers=headers, raise_for_status=True, timeout=timeoutLen) as fragResponse:
                with open(storagePath, 'wb') as out:
                    while True:
                        chunk = await fragResponse.content.read(chunk_size)
                        if not chunk:
                            break
                        out.write(chunk)
            return True
        except aiohttp.ClientResponseError as statusError:
            log(f'Response returned status {statusError.status} for {storagePath}')
            log(statusError.message)
            return await self.handleRetry(session, remoteUrl, storagePath, referer, fragLen)
        except aiohttp.TimeoutError as timeoutError:
            log(f'Response timed out for {storagePath}')
            log(statusError.message)
            return await self.handleRetry(session, remoteUrl, storagePath, referer, fragLen)
        except Exception as e:
            log(f'Error downloading Frag {storagePath}')
            log(str(e))
            log(e.__class__.__name__)
            return False

    async def handleRetry(self, session, remoteUrl, storagePath, referer, fragLen):
        if remoteUrl in self.retryMap and self.retryMap[remoteUrl] >= self.fragRetryMax:
            log(f'Max retry exceeded for frag {storagePath}')
            return False
        else:
            log('Retrying...')
            if remoteUrl not in self.retryMap:
                self.retryMap[remoteUrl] = 0
            self.retryMap[remoteUrl] += 1
            return await self.downloadFrag(session, remoteUrl, storagePath, referer, fragLen)

