import os
import xbmc
import xbmcvfs
import xbmcgui
import xbmcplugin
import xbmcaddon
import urllib
from pdf2image import convert_from_bytes, convert_from_path

root_list = {'30000': 0, '30001': 1, '30002': 2}
addon_id = 'plugin.image.pdf2reader'
last_file = 'last-list'

def SettingBoolToInt(val):
    if val == 'true':
        return 1
    else:
        return 0

class PdfReader(object):

    def __init__(self, addon_id):
        self._addon_id = addon_id
        if addon_id != None:
            self._addon = xbmcaddon.Addon(addon_id)
            self._fanart = self._addon.getAddonInfo('fanart')
            self._profile = xbmcvfs.translatePath(self._addon.getAddonInfo('profile'))
            #data dir
            dataDir = xbmcvfs.translatePath(self._addon.getAddonInfo('profile')) + 'data'
            if not os.path.exists(dataDir):
                os.makedirs(dataDir)
            #files
            self._fileLast = dataDir + os.path.sep + last_file
            self._listLast = {}
            self._tmpDir = xbmcvfs.translatePath(self._addon.getAddonInfo('profile')) + 'tmp'
            if not os.path.exists(self._tmpDir):
                os.makedirs(self._tmpDir)
            self._isdebug = SettingBoolToInt(self._addon.getSetting('use_debug'))
            self._dpi = self._addon.getSetting('dpi_pdf')
            self._thread_count = self._addon.getSetting('thread_count')
            self.parseNodes()

    def getLang(self, lcode):
        return self._addon.getLocalizedString(lcode)

    def addLog(self, source, text=''):
        if self._isdebug == 0:
            return
        xbmc.log('## ' + self._addon.getAddonInfo('name') + ' ## ' + source + ' ## ' + text)
        
    def getParams(self, args):
        param=[]
        self.addLog('getParams','PARSING ARGUMENTS: ' + str(args))
        paramstring=args[2]
        if len(paramstring)>=2:
            params=args[2]
            cleanedparams=params.replace('?', '')
            if (params[len(params)-1]=='/'):
                params=params[0:len(params)-2]
            pairsofparams=cleanedparams.split('&')
            param={}
            for i in range(len(pairsofparams)):
                splitparams={}
                splitparams=pairsofparams[i].split('=')
                if (len(splitparams))==2:
                    param[splitparams[0]]=splitparams[1]
            return param

    def buildPath(self, localpath, mode, params=''):
        if params == '':
            build_path = localpath + '?mode=' + str(mode)
        else:
            build_path = localpath + '?mode=' + str(mode) + params
        return  build_path
        
    def buildParams(self, title, url='', img=''):
        params = ''
        if title != '':
            params = params + '&title=' + urllib.quote_plus(title)
        if url != '':
            params = params + '&url=' + urllib.quote_plus(url)
        if img != '':
            params = params + '&img=' + urllib.quote_plus(img)
        return params

    def addFolder(self, localpath, handle, url, mode, title, img='DefaultFolder.png'):
        Item = xbmcgui.ListItem(title, title, img, img)
        Item.setProperty( 'fanart_image', self._fanart )
        Item.setInfo(type = 'pictures', infoLabels = {'title':title})
        params = self.buildParams(title, url) 
        Path = self.buildPath(localpath, mode, params)        
        xbmcplugin.addDirectoryItem(handle, Path, Item, True, 1000)
        
    def addItem(self, localpath, handle, url, mode, title, img='DefaultPicture.png'):
        Item = xbmcgui.ListItem(title, title, urllib.unquote_plus(img), urllib.unquote_plus(img))
        Item.setProperty( 'fanart_image', urllib.unquote_plus(img))
        Item.setInfo(type = 'pictures', infoLabels = {'title':title})
        params = self.buildParams(title, url, img)
        Path = self.buildPath(localpath, mode, params)
        self.addLog('addItem', 'Path - ' + Path)
        xbmcplugin.addDirectoryItem(handle, Path, Item, False, 1000)
            
    def showRoot(self, localpath, handle):
        self.addLog('showRoot')
        xbmcplugin.setContent(handle, 'files')
        for title, mode in sorted(root_list.items()):
            self.addFolder(localpath, handle, '', mode, self.getLang(int(title)).encode('utf-8'))
        xbmcplugin.endOfDirectory(handle)
        xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_NONE)
                
    def clearTMP(self):
        for f in os.listdir(self._tmpDir):
            file_path = os.path.join(self._tmpDir, f)
            while os.path.exists(file_path): 
                try: os.remove(file_path); break 
                except: pass
                
    def showPDF2Image(self, localpath, handle, url, mode):
        xbmcplugin.setContent(handle, 'images')
        n = 0
        for f in sorted(os.listdir(self._tmpDir)):
            n += 1
            self.addLog('showPDF2Image', 'file ' + str(n) + ' = ' + f)
            file_path = os.path.join(self._tmpDir, f)
            title = self.getLang(30004).encode('utf-8') + ' ' + str(n)
            self.addItem(localpath, handle, url, mode, title, file_path)
        xbmcplugin.endOfDirectory(handle)
        if self._addon.getSetting('content_view') <> 0:
            xbmc.executebuiltin('Container.SetViewMode(' + str(self._addon.getSetting('content_view')) + ')')
        
    def readPDF(self, localpath, handle, url, mode, file_patch):
        try:
            xbmc.executebuiltin('ActivateWindow(busydialognocancel)')
            self.clearTMP()
            base=os.path.basename(file_patch)
            pages = convert_from_path(file_patch, output_folder=self._tmpDir, dpi=self._dpi, fmt='jpg', thread_count=self._thread_count, output_file=os.path.splitext(base)[0])
            self.showPDF2Image(localpath, handle, url, mode)
            xbmc.executebuiltin('Dialog.Close(busydialognocancel)')
        except Exception, e:
            xbmc.executebuiltin('Dialog.Close(busydialognocancel)')
            dialog = xbmcgui.Dialog()
            ok = dialog.ok('Read PDF', 'ERROR: ' + repr(e))
            self.addLog('Read PDF', 'ERROR: (' + repr(e) + ')')
                    
    def openPDF(self, localpath, handle, url, mode):        
        dialog = xbmcgui.Dialog()
        file = dialog.browse(1, self.getLang(30000).encode('utf-8'), 'files', '.pdf', False, False, self._addon.getSetting('folder_pdf'), False)        
        if file != self._addon.getSetting('folder_pdf'):
            self.addLog('openPDF','PDF Folder: ' + file)
            self.readPDF(localpath, handle, url, mode, file)
    
    def showLast(self, localpath, handle, url, mode):
        self.showPDF2Image(localpath, handle, url, mode)
        
    def showImage(self, localpath, handle, url, title, img):
        command = 'SlideShow(' + self._tmpDir + ', pause, beginslide=' + urllib.unquote_plus(img) + ')'
        self.addLog('showImage', command)
        xbmc.executebuiltin(command)
    
    def parseNodes(self):
        params = self.getParams(sys.argv)
        mode = None
        url = ''
        title = ''
        img = ''

        try:
            url = urllib.unquote_plus(params['url'])
        except:
            pass
        try:
            mode = int(params['mode'])
        except:
            pass
        try:
            title = params['title']
        except:
            pass
        try:
            img = params['img']
        except:
            pass
            
        if mode == None:
            self.showRoot(sys.argv[0], int(sys.argv[1]))
        elif mode == 0:
            self.openPDF(sys.argv[0], int(sys.argv[1]), self._tmpDir, 10)
        elif mode == 1:
            self.showLast(sys.argv[0], int(sys.argv[1]), self._tmpDir, 10)
        elif mode == 2:
            self._addon.openSettings()
        elif mode == 10:
            self.showImage(sys.argv[0], int(sys.argv[1]), url, title, img)
            
if __name__ == '__main__':
    PdfReader(addon_id)