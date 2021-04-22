import os
import xbmc
import xbmcvfs
import xbmcgui
import xbmcplugin
import xbmcaddon
import shutil
from urllib.parse import quote_plus, unquote_plus
from pdf2image import convert_from_path
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

root_list = {'30000': 0, '30001': 1, '30002': 2}
addon_id = 'plugin.image.pdf2reader'

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
            self._tmpDir = xbmcvfs.translatePath(self._addon.getAddonInfo('profile')) + 'tmp'
            if not os.path.exists(self._tmpDir):
                os.makedirs(self._tmpDir)
            self._isdebug = SettingBoolToInt(self._addon.getSetting('use_debug'))
            self._dpi = self._addon.getSetting('dpi_pdf')
            self._thread_count = int(self._addon.getSetting('thread_count'))
            self._two_page = SettingBoolToInt(self._addon.getSetting('two_page'))
            self._main_page = SettingBoolToInt(self._addon.getSetting('main_page'))
            self._cropimage = SettingBoolToInt(self._addon.getSetting('cropimage'))
            self._offset = int(self._addon.getSetting('offset'))
            self.parseNodes()

    def getLang(self, lcode):
        return self._addon.getLocalizedString(lcode)

    def addLog(self, source, text=''):
        if self._isdebug == 0:
            return
        xbmc.log('## ' + self._addon.getAddonInfo('name') + ' - ' + source + ' ## ' + text, xbmc.LOGINFO)
        
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
            params = params + '&title=' + quote_plus(title)
        if url != '':
            params = params + '&url=' + quote_plus(url)
        if img != '':
            params = params + '&img=' + quote_plus(img)
        return params

    def addFolder(self, localpath, handle, url, mode, title, img='DefaultFolder.png'):
        Item = xbmcgui.ListItem(title, title)
        Item.setArt({'icon': img, 'thumb' : img, 'fanart' : self._fanart})
        Item.setInfo(type = 'pictures', infoLabels = {'title':title})
        params = self.buildParams(title, url) 
        Path = self.buildPath(localpath, mode, params)        
        xbmcplugin.addDirectoryItem(handle, Path, Item, True, 1000)
        
    def addItem(self, localpath, handle, url, mode, title, img='DefaultPicture.png'):
        Item = xbmcgui.ListItem(title, title)
        Item.setArt({'icon': unquote_plus(img), 'thumb' : unquote_plus(img), 'fanart' : unquote_plus(img)})
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
            path = os.path.join(self._tmpDir, f)
            while os.path.exists(path): 
                try: 
                    shutil.rmtree(path)
                    break 
                except Exception as e:
                    self.addLog('clearTMP', 'ERROR: (' + repr(e) + ')')
                
    def showPDF2Image(self, localpath, handle, url, mode):
        xbmcplugin.setContent(handle, 'images')
        n = 0
        rt = url
        for f in sorted(os.listdir(rt)):
            n += 1
            self.addLog('showPDF2Image', 'file ' + str(n) + ' = ' + f)
            img = os.path.join(rt, f)
            title = self.getLang(30004) + ' ' + str(n)
            self.addItem(localpath, handle, url, mode, title, img)
        xbmcplugin.endOfDirectory(handle)
        if int(self._addon.getSetting('content_view')) != 0:
            xbmc.executebuiltin('Container.SetViewMode(' + str(self._addon.getSetting('content_view')) + ')')
            
    def numToStr(self, num):
        if num < 10:
            return '00' + str(num)
        elif num >= 10 and num < 100:
            return '0' + str(num)
        else:
            return str(num)
            
    def saveImage(self, folder, index, arrImage):
        img = arrImage[index]
        
        if self._cropimage == 1:
            w, h = img.size
            img_area = (self._offset, self._offset, w - self._offset, h - self._offset)
            img = img.crop(img_area)
            
        fname = 'page_' + self.numToStr(index + 1) + '.jpg'
        img.save(os.path.join(folder, fname))
        
    def saveTwoImage(self, folder, index, arrImage):
        img1 = arrImage[index]
        
        if self._cropimage == 1:
            w1, h1 = img1.size
            img_area = (self._offset, self._offset, w1 - self._offset, h1 - self._offset)
            img1 = img1.crop(img_area)
                        
        w1, h1 = img1.size
        
        img2 = arrImage[index + 1]
        
        if self._cropimage == 1:
            w2, h2 = img2.size
            img_area = (self._offset, self._offset, w2 - self._offset, h2 - self._offset)
            img2 = img2.crop(img_area)
            
        w2, h2 = img2.size
            
        if h1 > h2:
            h = h1
        elif h1 < h2:
            h = h2
        else:
            h = h1
            
        img12 = Image.new('RGB', (w1 + w2, h))
        img12.paste(img1, (0, 0))
        img12.paste(img2, (w1, 0))
        fname = 'page_' + self.numToStr(index + 1) + '-' + self.numToStr(index + 2) + '.jpg'
        img12.save(os.path.join(folder, fname))
        
    def readPDF(self, localpath, handle, url, mode, file_patch):
        try:
            xbmc.executebuiltin('ActivateWindow(busydialognocancel)')
            base=os.path.splitext(os.path.basename(file_patch))[0]
            self.addLog('Read PDF', base)
            foutput=os.path.join(self._tmpDir, base)
            if os.path.exists(foutput):
                shutil.rmtree(foutput)
            os.makedirs(foutput)
            images = convert_from_path(file_patch, output_folder=None, dpi=self._dpi, fmt='jpg', thread_count=self._thread_count, output_file=base)
            self.addLog('Read PDF IMAGES COUNT', str(len(images)))
            
            i = 0
            while i < len(images):
                if self._two_page == 0:
                    self.saveImage(foutput, i, images)
                    i += 1 
                else:
                    if i + 1 > len(images) - 1:
                        if i == len(images) - 1:
                            self.saveImage(foutput, i, images)
                            i += 1  
                        break
                    if self._main_page == 1 and i == 0:
                        self.saveImage(foutput, i, images)
                        i += 1 
                    else:
                        self.saveTwoImage(foutput, i, images)
                        i += 2
                    
            self.showPDF2Image(localpath, handle, foutput, mode)
            xbmc.executebuiltin('Dialog.Close(busydialognocancel)')
        except Exception as e:
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
        self.addLog('showLast')
        xbmcplugin.setContent(handle, 'files')
        rt = url
        for f in sorted(os.listdir(rt)):
            self.addLog('showLast', 'folder = ' + f)
            file_path = os.path.join(rt, f)
            title = f
            self.addFolder(localpath, handle, file_path, mode, title)
        xbmcplugin.endOfDirectory(handle)
        
    def showImage(self, localpath, handle, url, title, img):
        command = 'SlideShow(' + url + ', pause, beginslide=' + unquote_plus(img) + ')'
        self.addLog('showImage', command)
        xbmc.executebuiltin(command)
    
    def parseNodes(self):
        params = self.getParams(sys.argv)
        mode = None
        url = ''
        title = ''
        img = ''

        try:
            url = unquote_plus(params['url'])
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
            self.showLast(sys.argv[0], int(sys.argv[1]), self._tmpDir, 9)
        elif mode == 2:
            self.clearTMP()
        elif mode == 9:
            self.showPDF2Image(sys.argv[0], int(sys.argv[1]), url, 10)
        elif mode == 10:
            self.showImage(sys.argv[0], int(sys.argv[1]), url, title, img)
            
if __name__ == '__main__':
    PdfReader(addon_id)