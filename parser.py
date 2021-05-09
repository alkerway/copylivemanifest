from dateutil import parser as DateParser
from urllib.parse import urlparse
import os

class Parser:
    def __init__(self):
        pass

    def isLevelManifest(self, manifest):
        if not manifest.startswith('#EXTM3U'):
            raise Exception('Level Text File Not Manifest')
        return '#EXTINF:' in manifest or '#EXT-X-TARGETDURATION:' in manifest

    def parseLevelManifest(self, manifest, manifestUrl, fragStorageBase):
        lines = manifest.split('\n')
        endlistTag = None
        frags = []
        currentTags = {}
        currentTagLines = []
        currentFragNumber = 0
        for line in lines:
            if line.startswith('#EXT'):
                currentTagLines.append(line)
                tagInfo = self.getTagObj(line)
                if not tagInfo:
                    pass
                else:
                    if '#EXT-X-MEDIA-SEQUENCE' in tagInfo:
                        mediaSequence = int(tagInfo['#EXT-X-MEDIA-SEQUENCE'])
                        currentFragNumber = mediaSequence
                    elif '#EXT-X-ENDLIST' in tagInfo:
                        endlistTag = line
                    currentTags.update(tagInfo)
            elif line and not line.startswith('#'):
                fullUrl = line
                storagePath = line
                if line.startswith('/'):
                    parseObj = urlparse(manifestUrl)
                    fullUrl = parseObj.scheme + '://' + parseObj.netloc + line
                    storagePath = line.split('?')[0].split('/')[-1]
                elif line.startswith('http'):
                    storagePath = line.split('?')[0].split('/')[-1]
                else:
                    storagePath = '-'.join(line.split('?')[0].split('/'))
                    urlWithoutEnd = os.path.dirname(manifestUrl.split('?')[0])
                    fullUrl = urlWithoutEnd + '/' + line
                frags.append({
                    'storagePath': fragStorageBase + '/' + storagePath,
                    'remoteUrl': fullUrl,
                    'tags': currentTags,
                    'tagLines': currentTagLines,
                    'idx': currentFragNumber,
                    'downloaded': False
                })
                currentTags = {}
                currentTagLines = []
                currentFragNumber += 1
            else:
                # Ignore, not tag or url
                pass
        return frags, endlistTag

    def getTagObj(self, line):
        tagAndData = line.split(':')
        tag = tagAndData[0]
        store = {}
        if len(tagAndData) > 1:
            data = ':'.join(tagAndData[1:])
            store[tag] = data
            # attributes = data.split(',')
            # if len(list(filter(lambda x: x, attributes))) > 1:
            #     keyDict = {}
            #     for pair in attributes:
            #         nameAndVal = pair.split('=')
            #         name = nameAndVal[0]
            #         val = '='.join(nameAndVal[1:])
            #         if val[0] == '"' and val[-1] == '"':
            #             val = val[1:-1]
            #         keyDict[name] = val
            #     store[tag] = keyDict
            # else:
        else:
            store[tag] = ''
        return store