import sys
import urllib3
import subprocess
from parser import Parser
from fragQueue import FragQueue
from errors import StatusError, NotManifestError
from interval import RepeatedTimer
from log import log
http = urllib3.PoolManager(cert_reqs='CERT_NONE')
urllib3.disable_warnings()


outDir = './manifest'
parser = Parser()

fragStorageBase = 'frags'
RECORDING_TIME = 6

urlInput = input('Enter Manifest Url: ')
if not urlInput:
    urlInput = 'http://cdn.maskamr.xyz/live/NBA5/chunks.m3u8'
referer = input('Enter Referer (optional): ')
recordTime = input('Input Recording time in hours (default 6): ')
if recordTime:
    RECORDING_TIME = float(recordTime)
if input('Log to file? '):
    sys.stdout = open('./python-output.txt', 'w+')

stopAfter = 60 * 60 * RECORDING_TIME

POLL_INTERVAL = 3
MAX_LEVEL_ERROR = 10

isFirstParse = True
levelErrorCount = 0
fatalErrorState = False
startRequestCount = 1
finishRequestCount = 0

def requestLevel():
    global urlInput
    global referer
    global startRequestCount
    global finishRequestCount
    global fatalErrorState
    levelUrl = urlInput

    if fatalErrorState or startRequestCount > finishRequestCount + 1:
        return
    
    log(f'Poll {startRequestCount} start')
    startRequestCount += 1
    try:
        headers = None
        if referer:
            headers = {'Referer': referer, 'Origin': referer}
        manifestRequest = http.request('GET', levelUrl, headers=headers, timeout=5)
        manifestText = manifestRequest.data.decode("utf-8")
        if manifestRequest.status >= 400:
            raise StatusError(manifestRequest.status, manifestText, manifestRequest.reason)
    except StatusError as err:
        print('StatusError requesting level', err)
        incrementLevelError()
    except NotManifestError:
        print('Level request returned not manifest')
        cancelTimer()
    except urllib3.exceptions.HTTPError as err:
        print(f'HTTP error requesting Level Manifest: {str(err)}')
        incrementLevelError()
        property_names=[p for p in dir(err) if isinstance(getattr(err,p),property)]
        print(property_names)
    except Exception as err:
        print('Unknown Error', str(err))
    else:
        if not fatalErrorState:
            print(f'Poll {finishRequestCount} handling text')
            handleLevelManifestText(manifestText, levelUrl, referer)
            levelErrorCount = 0

    finishRequestCount += 1
    print(f'Poll {finishRequestCount} done')
    print()
    sys.stdout.flush()


def handleLevelManifestText(manifestText, levelUrl, referer):
    global isFirstParse
    global originalMediaSequence
    remoteFrags, enlistTag = parser.parseLevelManifest(manifestText, levelUrl, fragStorageBase)

    if isFirstParse:
        isFirstParse = False
        firstFrag = remoteFrags[0]
        lastFrag = remoteFrags[-1]
        firstTagLines = []
        for tagLine in firstFrag['tagLines']:
            if '#EXTINF:' in tagLine:
                break
            elif '#EXT-X-MEDIA-SEQUENCE' in tagLine:
                # add correct frag number later
                pass
            else:
                firstTagLines.append(tagLine)
        firstTagLines.append(f'#EXT-X-MEDIA-SEQUENCE:{lastFrag["idx"]}')
        firstTagLines.insert(1, '#EXT-X-PLAYLIST-TYPE:EVENT')
        remoteFrags[-1]['tagLines'] = firstTagLines + remoteFrags[-1]['tagLines']
        remoteFrags = [remoteFrags[-1]]
        fragQueue.setReferer(referer)
        fragQueue.setIdxOffset(lastFrag['idx'])

    fragQueue.add(remoteFrags)

def incrementLevelError():
    global levelErrorCount
    global MAX_LEVEL_ERROR
    global fatalErrorState
    levelErrorCount += 1
    if levelErrorCount > MAX_LEVEL_ERROR:
        print('Errors exceeded max, stopping')
        fatalErrorState = True
        cancelTimer()

def formatDownloadedVideo():
    outputFormat = 'mkv'
    print('\n\n')
    print('=============Starting Fomat================')
    inputPath = outDir + '/level.m3u8'
    ffmpegCommand = ['ffmpeg',
                     '-v',
                     'verbose',
                     '-allowed_extensions',
                     'ALL',
                     '-protocol_whitelist', 'file,http,https,tcp,tls',
                     '-y',
                     '-fflags',
                     '+genpts+igndts',
                     '-i',
                     inputPath,
                     '-c', 'copy',
                     outDir + '/video.' + outputFormat
                     ]
    subprocess.call(ffmpegCommand)
    print(' '.join(ffmpegCommand))

def afterStop():
    formatDownloadedVideo()
    sys.stdout.flush()
    sys.exit()

def onStop():
    global fatalErrorState
    fragQueue.finishAndStop(fatalErrorState)


def cancelTimer():
    k.stop()

fragQueue = FragQueue(outDir, afterStop)

k = RepeatedTimer(requestLevel, onStop, POLL_INTERVAL, stopAfter)
