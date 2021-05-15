import threading
import asyncio
import aiohttp

from downloader import Downloader
from log import log

downloader = Downloader()
MAX_STALL_COUNT = 20
MAX_FRAG_ERROR = 10

class FragQueue:
    def __init__(self, outDir, finishCallback, cancelTimer):
        self.lastQueueIdx = -1
        self.lastDownloadedIdx = -1
        self.frags = []
        self.outDir = outDir
        self.finishCallback = finishCallback
        self.cancelTimer = cancelTimer
        self.wrapUpAndFinish = False
        self.idxOffset = 0
        self.manifestLength = 0
        self.referer = ''
        self.stallCount = 0
        self.fragErrorCount = 0

        # clear level file
        open(self.outDir + '/level.m3u8', 'w').close()

    def add(self, fragArr):
        newFrags = []
        lastIdx = self.lastQueueIdx
        for frag in fragArr:
            if frag['idx'] > lastIdx:
                newFrags.append(frag)
                log(f'Frag {frag["idx"] - self.idxOffset} added to queue, {threading.active_count()} threads active')

        self.frags += newFrags
        if len(self.frags):
            self.lastQueueIdx = self.frags[-1]['idx']

        if not len(newFrags):
            log('Level stall increment')
            self.stallCount += 1
            if self.stallCount > MAX_STALL_COUNT:
                log('Level stall exceeded max stall, stopping')
                self.wrapUpAndFinish = True
                self.onQueueError()
            return
        else:
            self.stallCount = 0
        
        asyncio.run(self.handleNewFrags(newFrags))

    async def handleNewFrags(self, newFrags):
        results = None
        async with aiohttp.ClientSession() as session:
            fragDownloads = []
            for frag in newFrags:
                task = asyncio.ensure_future(downloader.downloadFrag(session, frag['remoteUrl'], f'{self.outDir}/{frag["storagePath"]}', self.referer, frag['fragLen']))
                fragDownloads.append(task)
            results = await asyncio.gather(*fragDownloads, return_exceptions=True)
        
        for idx, frag in enumerate(newFrags):
            if results[idx]:
                log(f'Frag {frag["idx"] - self.idxOffset} downloaded')
                frag['downloaded'] = True
                self.onDownloaded(frag)
                self.fragErrorCount = 0
            else:
                log(f'Error downloading frag {frag["idx"] - self.idxOffset}')
                self.frags.remove(frag)
                self.fragErrorCount += 1
                if self.fragErrorCount >= MAX_FRAG_ERROR:
                    log('Frag error exceeded max error count, stopping')
                    self.wrapUpAndFinish = True
                    self.onQueueError()

        self.onFragFinish()


    def peek(self):
        if len(self.frags):
            return self.frags[0]
        else:
            return None

    def onDownloaded(self, frag):
        if self.frags[0]['downloaded']:
            curFrag = self.peek()
            if frag['idx'] != self.lastDownloadedIdx + 1 and self.lastDownloadedIdx > -1:
                self.frags[0]['tagLines'].insert(0, '#EXT-X-DISCONTINUITY')
                log(f'!!! Missing frags {self.lastDownloadedIdx + 1 - self.idxOffset} to {curFrag["idx"] - self.idxOffset - 1}')
            newManifestLines = []
            while curFrag and curFrag['downloaded'] == True:
                newManifestLines = newManifestLines + curFrag['tagLines']
                newManifestLines.append(curFrag["storagePath"])
                self.lastDownloadedIdx = curFrag['idx']
                fragLen = curFrag['fragLen']
                self.manifestLength += fragLen
                log(f'Frag {self.lastDownloadedIdx - self.idxOffset} writing to manifest ({round(self.manifestLength / 60, 1)} min)')
                self.frags.pop(0)
                curFrag = self.peek()
            self.addLinesToLevel(newManifestLines)
        else:
            pass
        self.onFragFinish()
    
    def onFragFinish(self):
        if self.wrapUpAndFinish and len(self.frags) == 0:
            self.wrapUpLevel()

    def addLinesToLevel(self, newManifestLines):
        with open(self.outDir + '/level.m3u8', 'a') as levelFile:
            levelFile.write('\n'.join(newManifestLines))
            levelFile.write('\n')

    def wrapUpLevel(self):
        log('Last frag downloaded, finishing up')
        self.addLinesToLevel(['#EXT-X-ENDLIST', ''])
        self.finishCallback()

    def onQueueError(self):
        self.cancelTimer()

    def finishAndStop(self):
        self.wrapUpAndFinish = True
        log('finishAndStop', len(self.frags))
        if len(self.frags) == 0:
            self.wrapUpLevel()

    def setIdxOffset(self, offset):
        self.idxOffset = offset

    def setReferer(self, referer):
        self.referer = referer