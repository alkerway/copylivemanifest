from downloader import Downloader

downloader = Downloader()


class FragQueue:
    def __init__(self, outDir):
        self.lastQueueIdx = -1
        self.lastDownloadedIdx = -1
        self.frags = []
        self.outDir = outDir
        self.finishCallback = None
        self.idxOffset = 0

        # clear level file
        open(self.outDir + '/level.m3u8', 'w').close()

    def add(self, fragArr):
        newFrags = []
        lastIdx = self.lastQueueIdx
        for frag in fragArr:
            if frag['idx'] > lastIdx:
                newFrags.append(frag)
                print(f'Frag {frag["idx"] - self.idxOffset} added to queue')

        self.frags += newFrags
        if len(self.frags):
            self.lastQueueIdx = self.frags[-1]['idx']

        # Download new frags
        for frag in newFrags:
            success = downloader.downloadFrag(frag['remoteUrl'], f'{self.outDir}/{frag["storagePath"]}')
            if success:
                print(f'Frag {frag["idx"] - self.idxOffset} downloaded')
                frag['downloaded'] = True
                self.onFinish(frag)
            else:
                print('figure this out, frag not downloaded')


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
                print(f'Frag {self.lastDownloadedIdx - self.idxOffset} writing to manifest')
                self.frags.pop(0)
                curFrag = self.peek()
            self.addLinesToLevel(newManifestLines)
            if self.finishCallback and not curFrag:
                self.wrapUpLevel()
        else:
            pass

    def addLinesToLevel(self, newManifestLines):
        with open(self.outDir + '/level.m3u8', 'a') as levelFile:
            levelFile.write('\n'.join(newManifestLines))
            levelFile.write('\n')

    def wrapUpLevel(self):
        print('Last frag downloaded, finishing up')
        self.addLinesToLevel(['#EXT-X-ENDLIST', ''])
        self.finishCallback()

    def finishAndStop(self, callback):
        self.finishCallback = callback
        if len(self.frags) == 0:
            self.wrapUpLevel()

    def setIdxOffset(self, offset):
        self.idxOffset = offset