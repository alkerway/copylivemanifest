import sys
import urllib3
import subprocess
from parser import Parser
from fragQueue import FragQueue
from errors import StatusError, NotManifestError
from interval import RepeatedTimer
http = urllib3.PoolManager(cert_reqs='CERT_NONE')
urllib3.disable_warnings()


outDir = './manifest'
parser = Parser()
fragQueue = FragQueue(outDir)

fragStorageBase = 'frags'

urlInput = input('Enter Manifest Url: ')
if not urlInput:
    urlInput = 'https://ngx.cr2.streamzilla.xlcdn.com/session/ec3f186d5a165af51f6a8a94d1e2a955/sz/streamdays/wowza4/live/bognor-pier/chunklist.m3u8'
recordTime = input('Input Recording time in hours (default 6): ')
if recordTime:
    RECORDING_TIME = float(recordTime)
if input('Log to file? '):
    sys.stdout = open('./log/python-output.txt', 'w+')

stopAfter = 60 * 60 * RECORDING_TIME

POLL_INTERVAL = 4

isFirstParse = True

def requestLevel():
    global urlInput
    levelUrl = urlInput
    try:
        manifestRequest = http.request('GET', levelUrl, headers=None)
        manifestText = manifestRequest.data.decode("utf-8")
        if manifestRequest.status >= 400:
            raise StatusError(manifestRequest.status, manifestText, manifestRequest.reason)
        handleLevelManifestText(manifestText, levelUrl)
    except StatusError as err:
        print(err)
    except NotManifestError:
        print('Level request returned not manifest')
    # except Exception as err:
    #     print(f'Error building Level Manifest: {str(err)}')
    sys.stdout.flush()


def handleLevelManifestText(manifestText, levelUrl):
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
        fragQueue.setIdxOffset(lastFrag['idx'])

    fragQueue.add(remoteFrags)


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
    sys.exit()

def onStop():
    fragQueue.finishAndStop(afterStop)


def cancelTimer():
    k.stop()


k = RepeatedTimer(requestLevel, onStop, POLL_INTERVAL, stopAfter)
