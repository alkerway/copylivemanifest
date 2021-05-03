from downloader import Downloader
from log import log

downloader = Downloader()
MAX_STALL_COUNT = 30

class FragQueue:
    def __init__(self, outDir, finishCallback):
        self.lastQueueIdx = -1
        self.lastDownloadedIdx = -1
        self.frags = []
        self.outDir = outDir
        self.finishCallback = finishCallback
        self.wrapUpAndFinish = False
        self.idxOffset = 0
        self.manifestLength = 0
        self.referer = ''
        self.stallCount = 0

        # clear level file
        open(self.outDir + '/level.m3u8', 'w').close()

    def add(self, fragArr):
        newFrags = []
        lastIdx = self.lastQueueIdx
        for frag in fragArr:
            if frag['idx'] > lastIdx:
                newFrags.append(frag)
                log(f'Frag {frag["idx"] - self.idxOffset} added to queue')

        self.frags += newFrags
        if len(self.frags):
            self.lastQueueIdx = self.frags[-1]['idx']

        if not len(newFrags):
            log('Level stall increment')
            self.stallCount += 1
            if self.stallCount > MAX_STALL_COUNT:
                log('Level stall exceeded max stall, stopping')
                self.wrapUpAndFinish = True
                self.wrapUpLevel()
        else:
            self.stallCount = 0

        # Download new frags
        for frag in newFrags:
            # log(f'Frag {frag["idx"] - self.idxOffset} starting download')
            success = downloader.downloadFrag(frag['remoteUrl'], f'{self.outDir}/{frag["storagePath"]}', self.referer)
            if success:
                log(f'Frag {frag["idx"] - self.idxOffset} downloaded')
                frag['downloaded'] = True
                self.onFinish(frag)
            else:
                log('figure this out, frag not downloaded')


    def peek(self):
        if len(self.frags):
            return self.frags[0]
        else:
            return None

    def onFinish(self, frag):
        if frag['idx'] == self.lastDownloadedIdx + 1 or self.lastDownloadedIdx == -1:
            newManifestLines = []
            curFrag = self.peek()
            while curFrag and curFrag['downloaded'] == True:
                newManifestLines = newManifestLines + curFrag['tagLines']
                newManifestLines.append(curFrag["storagePath"])
                self.lastDownloadedIdx = curFrag['idx']
                fragLen = float(curFrag['tags']['#EXTINF'].strip(','))
                self.manifestLength += fragLen
                log(f'Frag {self.lastDownloadedIdx - self.idxOffset} writing to manifest ({round(self.manifestLength / 60, 1)} min)')
                self.frags.pop(0)
                curFrag = self.peek()
            self.addLinesToLevel(newManifestLines)
        else:
            pass
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

    def finishAndStop(self, isBecauseError):
        self.wrapUpAndFinish = True
        log('finishAndStop', len(self.frags), isBecauseError)
        if len(self.frags) == 0 or isBecauseError:
            self.wrapUpLevel()

    def setIdxOffset(self, offset):
        self.idxOffset = offset

    def setReferer(self, referer):
        self.referer = referer