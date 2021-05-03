import urllib3
import os
from errors import StatusError
from log import log


class Downloader:
    def __init__(self):
        self.retryMap = {}
        self.fragRetryMax = 3
        self.http = urllib3.PoolManager()

    def downloadFrag(self, remoteUrl, storagePath, referer=''):
        storageDir = '/'.join(storagePath.split('/')[:-1])
        if not os.path.exists(storageDir):
            os.mkdir(storageDir)
        try:
            headers = None
            if referer:
                headers = {'Referer': referer, 'Origin': referer}
            r = self.http.request('GET', remoteUrl, preload_content=False, headers=headers, timeout=15)
            if r.status >= 400:
                raise StatusError(r.status, r.data.decode("utf-8"), r.reason)
            chunk_size = 56384
            with open(storagePath, 'wb') as out:
                for chunk in r.stream(chunk_size):
                    out.write(chunk)
            r.release_conn()
            return True
        except StatusError as statusError:
            log(f'Response returned status {statusError.status} for {storagePath}')
            log(statusError.body)
            return False # self.handleRetry(remoteUrl, storagePath, referer)
        except urllib3.exceptions.HTTPError as e:
            log(f'Frag response error {storagePath}')
            log(str(e))
            return False # self.handleRetry(remoteUrl, storagePath, referer)
        except Exception as e:
            log(f'Error downloading Frag {storagePath}')
            log(str(e))
            return False

    def handleRetry(self, remoteUrl, storagePath, referer):
        if remoteUrl in self.retryMap and self.retryMap[remoteUrl] >= self.fragRetryMax:
            log(f'Max retry exceeded for frag {storagePath}')
            return False
        else:
            log('Retrying...')
            if remoteUrl not in self.retryMap:
                self.retryMap[remoteUrl] = 0
            self.retryMap[remoteUrl] += 1
            return self.downloadFrag(remoteUrl, storagePath, referer)

