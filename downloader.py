import asyncio
import httpx
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
            async with session.stream('GET', remoteUrl, headers=headers, timeout=timeoutLen) as fragResponse:
                fragResponse.raise_for_status()
                with open(storagePath, 'wb') as out:
                    async for chunk in fragResponse.aiter_bytes():
                        if not chunk:
                            break
                        out.write(chunk)
            return True
        except httpx.HTTPStatusError as exc:
            log(f'Response returned status {exc.response.status_code} for {storagePath}')
            return await self.handleRetry(session, remoteUrl, storagePath, referer, fragLen)
        except httpx.TimeoutException as timeoutError:
            log(f'Response timed out for {storagePath}')
            log(timeoutError)
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

