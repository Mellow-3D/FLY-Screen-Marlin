# Copyright (c) 2017 Looming
# Cura is released under the terms of the LGPLv3 or higher.

import os
import sys

from PyQt5.QtCore import QUrl,Qt
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from UM.Application import Application
from UM.Logger import Logger
from UM.Mesh.MeshWriter import MeshWriter
from UM.FileHandler.WriteFileJob import WriteFileJob
from UM.Message import Message

from UM.OutputDevice.OutputDevice import OutputDevice
from UM.OutputDevice import OutputDeviceError
from UM.OutputDevice.OutputDeviceError import WriteRequestFailedError #For when something goes wrong.
from UM.OutputDevice.OutputDevicePlugin import OutputDevicePlugin #The class we need to extend.

from UM.PluginRegistry import PluginRegistry #Getting the location of Hello.qml.

from UM.i18n import i18nCatalog

from cura.CuraApplication import CuraApplication

from PyQt5.QtCore import QByteArray
from cura.Snapshot import Snapshot
from cura.Utils.Threading import call_on_qt_thread

catalog = i18nCatalog("uranium")

def i4b(n):
    return [n >> 24 & 0xFF,n >> 16 & 0xFF,n >> 8 & 0xFF,n >> 0 & 0xFF]

def i2b(n):
    return [n >> 8 & 0xFF,n >> 0 & 0xFF]

class FLY3DStorePlugin(OutputDevicePlugin): #We need to be an OutputDevicePlugin for the plug-in system.
    ##  Called upon launch.
    #
    #   You can use this to make a connection to the device or service, and
    #   register the output device to be displayed to the user.
    def start(self):
        self.getOutputDeviceManager().addOutputDevice(FLY3DStore()) #Since this class is also an output device, we can just register ourselves.
        #You could also add more than one output devices here.
        #For instance, you could listen to incoming connections and add an output device when a new device is discovered on the LAN.

    ##  Called upon closing.
    #
    #   You can use this to break the connection with the device or service, and
    #   you should unregister the output device to be displayed to the user.
    def stop(self):
        self.getOutputDeviceManager().removeOutputDevice("FLY3D_store_gcode") #Remove all devices that were added. In this case it's only one.

class FLY3DStore(OutputDevice): #We need an actual device to do the writing.
    def __init__(self):
        super().__init__("FLY3D_store_gcode") #Give an ID which is used to refer to the output device.

        #Optionally set some metadata.
        self.setName("FLY3D Store Gcode") #Human-readable name (you may want to internationalise this). Gets put in messages and such.
        self.setShortDescription("Save as FLY3D format") #This is put on the save button.
        self.setDescription("Save as FLY3D format")
        self.setIconName("save")

        self._writing = False

    ##  Request the specified nodes to be written to a file.
    #
    #   \param nodes A collection of scene nodes that should be written to the
    #   file.
    #   \param file_name \type{string} A suggestion for the file name to write
    #   to. Can be freely ignored if providing a file name makes no sense.
    #   \param limit_mimetypes Should we limit the available MIME types to the
    #   MIME types available to the currently active machine?
    #   \param kwargs Keyword arguments.
    def requestWrite(self, nodes, file_name = None, limit_mimetypes = None, file_handler = None, **kwargs):
        if self._writing:
            raise OutputDeviceError.DeviceBusyError()

        # Set up and display file dialog
        dialog = QFileDialog()

        dialog.setWindowTitle(catalog.i18nc("@title:window", "Save to File"))
        dialog.setFileMode(QFileDialog.AnyFile)
        dialog.setAcceptMode(QFileDialog.AcceptSave)

        # Ensure platform never ask for overwrite confirmation since we do this ourselves
        dialog.setOption(QFileDialog.DontConfirmOverwrite)

        if sys.platform == "linux" and "KDE_FULL_SESSION" in os.environ:
            dialog.setOption(QFileDialog.DontUseNativeDialog)

        filters = []
        mime_types = []
        selected_filter = None

        if "preferred_mimetypes" in kwargs and kwargs["preferred_mimetypes"] is not None:
            preferred_mimetypes = kwargs["preferred_mimetypes"]
        else:
            preferred_mimetypes = Application.getInstance().getPreferences().getValue("local_file/last_used_type")
        preferred_mimetype_list = preferred_mimetypes.split(";")

        if not file_handler:
            file_handler = Application.getInstance().getMeshFileHandler()

        file_types = file_handler.getSupportedFileTypesWrite()

        file_types.sort(key = lambda k: k["description"])
        if limit_mimetypes:
            file_types = list(filter(lambda i: i["mime_type"] in limit_mimetypes, file_types))

        file_types = [ft for ft in file_types if not ft["hide_in_file_dialog"]]

        if len(file_types) == 0:
            Logger.log("e", "There are no file types available to write with!")
            raise OutputDeviceError.WriteRequestFailedError(catalog.i18nc("@info:warning", "There are no file types available to write with!"))

        # Find the first available preferred mime type
        preferred_mimetype = None
        for mime_type in preferred_mimetype_list:
            if any(ft["mime_type"] == mime_type for ft in file_types):
                preferred_mimetype = mime_type
                break

        for item in file_types:
            type_filter = "{0} (*.{1})".format(item["description"], item["extension"])
            filters.append(type_filter)
            mime_types.append(item["mime_type"])
            if preferred_mimetype == item["mime_type"]:
                selected_filter = type_filter
                if file_name:
                    file_name += "." + item["extension"]

        # Add the file name before adding the extension to the dialog
        if file_name is not None:
            dialog.selectFile(file_name)

        dialog.setNameFilters(filters)
        if selected_filter is not None:
            dialog.selectNameFilter(selected_filter)

        stored_directory = Application.getInstance().getPreferences().getValue("local_file/dialog_save_path")
        dialog.setDirectory(stored_directory)

        if not dialog.exec_():
            raise OutputDeviceError.UserCanceledError()

        save_path = dialog.directory().absolutePath()
        Application.getInstance().getPreferences().setValue("local_file/dialog_save_path", save_path)

        selected_type = file_types[filters.index(dialog.selectedNameFilter())]
        Application.getInstance().getPreferences().setValue("local_file/last_used_type", selected_type["mime_type"])

        # Get file name from file dialog
        file_name = dialog.selectedFiles()[0]
        Logger.log("d", "Writing to [%s]..." % file_name)
        
        if os.path.exists(file_name):
            result = QMessageBox.question(None, catalog.i18nc("@title:window", "File Already Exists"), catalog.i18nc("@label Don't translate the XML tag <filename>!", "The file <filename>{0}</filename> already exists. Are you sure you want to overwrite it?").format(file_name))
            if result == QMessageBox.No:
                raise OutputDeviceError.UserCanceledError()

        self.writeStarted.emit(self)

        # Actually writing file
        if file_handler:
            file_writer = file_handler.getWriter(selected_type["id"])
        else:
            file_writer = Application.getInstance().getMeshFileHandler().getWriter(selected_type["id"])

        try:
            mode = selected_type["mode"]
            if mode == MeshWriter.OutputMode.TextMode:
                Logger.log("d", "Writing to Local File %s in text mode", file_name)
                stream = open(file_name, "wt", encoding = "utf-8")
            elif mode == MeshWriter.OutputMode.BinaryMode:
                Logger.log("d", "Writing to Local File %s in binary mode", file_name)
                stream = open(file_name, "wb")
            else:
                Logger.log("e", "Unrecognised OutputMode.")
                return None

            job = WriteFileJob(file_writer, stream, nodes, mode)
            job.setFileName(file_name)
            job.setAddToRecentFiles(True)  # The file will be added into the "recent files" list upon success
            job.progress.connect(self._onJobProgress)
            job.finished.connect(self._onWriteJobFinished)

            message = Message(catalog.i18nc("@info:progress Don't translate the XML tags <filename>!", "Saving to <filename>{0}</filename>").format(file_name),
                              0, False, -1 , catalog.i18nc("@info:title", "Saving"))
            message.show()

            job.setMessage(message)
            self._writing = True
            job.start()
        except PermissionError as e:
            Logger.log("e", "Permission denied when trying to write to %s: %s", file_name, str(e))
            raise OutputDeviceError.PermissionDeniedError(catalog.i18nc("@info:status Don't translate the XML tags <filename>!", "Permission denied when trying to save <filename>{0}</filename>").format(file_name)) from e
        except OSError as e:
            Logger.log("e", "Operating system would not let us write to %s: %s", file_name, str(e))
            raise OutputDeviceError.WriteRequestFailedError(catalog.i18nc("@info:status Don't translate the XML tags <filename> or <message>!", "Could not save to <filename>{0}</filename>: <message>{1}</message>").format()) from e

    def _onJobProgress(self, job, progress):
        self.writeProgress.emit(self, progress)

    def _onWriteJobFinished(self, job):
        self._writing = False
        self.writeFinished.emit(self)
        wirte_succ = False
        if job.getResult():
            self.writeSuccess.emit(self)
            wirte_succ = True
        else:
            message = Message(catalog.i18nc("@info:status Don't translate the XML tags <filename> or <message>!", "Could not save to <filename>{0}</filename>: <message>{1}</message>").format(job.getFileName(), str(job.getError())), lifetime = 0, title = catalog.i18nc("@info:title", "Warning"))
            message.show()
            self.writeError.emit(self)
        try:
            job.getStream().close()
            if wirte_succ:
                self.do_snap(job.getFileName())
        except (OSError, PermissionError): #When you don't have the rights to do the final flush or the disk is full.
            message = Message(catalog.i18nc("@info:status", "Something went wrong saving to <filename>{0}</filename>: <message>{1}</message>").format(job.getFileName(), str(job.getError())), title = catalog.i18nc("@info:title", "Error"))
            message.show()
            self.writeError.emit(self)

    def _onMessageActionTriggered(self, message, action):
        if action == "open_folder" and hasattr(message, "_folder"):
            QDesktopServices.openUrl(QUrl.fromLocalFile(message._folder))

    def trans(self,m,w,h):
        d = [2]
        d.extend(i2b(w))
        d.extend(i2b(h))
        d.extend(i2b(0))
        for i in range(0,h):
            for j in range(0,w):
                c = m.pixelColor(j,i)
                r = c.red()
                g = c.green()
                b = c.blue()
                a = c.alpha()/255.0
                r = int((r * a) + (255 * (1.0 - a)))
                g = int((g * a) + (255 * (1.0 - a)))
                b = int((b * a) + (255 * (1.0 - a)))
                c888 = (r << 16) | (g << 8) | b
                rr = (c888 >> 19) & 0x1F
                gg = (c888 >> 10) & 0x3F
                bb = (c888 >> 3) & 0x1F
                n = (rr << 11) | (gg << 5) | bb
                d.extend(i2b(n))  
        return d

    @call_on_qt_thread
    def do_snap(self,gfile):
        m0 = Snapshot.snapshot(width = 900, height = 900)
        m1 = m0.scaled(240,240,Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        # Logger.log("i", m1.supportedImageFormats())
        if m1:
            hd = []
            db = self.trans(m1,240,240)

            size0 = len(db)
            size1 = os.path.getsize(gfile)

            offset = 0
            hd.append(1)
            offset = 17
            hd.extend(i4b(offset))
            hd.extend(i4b(size0))
            offset += size0
            hd.extend(i4b(offset))
            hd.extend(i4b(size1))

            fg = []
            f = open(gfile, 'rb+')
            fg = f.read()
            f.close()

            fly3dfile = os.path.splitext(gfile)[0]+".fly3d"
            f = open(fly3dfile, 'wb+')
            f.write(bytes(hd))
            f.write(bytes(db))
            f.write(fg)
            f.close()
            os.remove(gfile)
            message = Message(catalog.i18nc("@info:status Don't translate the XML tags <filename>!", "Saved to <filename>{0}</filename>").format(fly3dfile), title = catalog.i18nc("@info:title", "File Saved"))
            message.addAction("open_folder", catalog.i18nc("@action:button", "Open Folder"), "open-folder", catalog.i18nc("@info:tooltip", "Open the folder containing the file"))
            message._folder = os.path.dirname(fly3dfile)
            message.actionTriggered.connect(self._onMessageActionTriggered)
            message.show()


## 文件读取，按照以下顺序读取
# 1字节：块类型。固定值:1；值1:地址表块，2:图片块
# 4字节（大端）：图片1地址偏移的开始位置
# 4字节（大端）：图片1大小
# 4字节（大端）：Gcode地址偏移的开始位置
# 4字节（大端）：Gcode大小
# 1字节：块类型。固定值:2；值1:地址表块，2:图片块
# 2字节（大端）：图片宽度
# 2字节（大端）：图片高度
# 2字节（大端）：0
# 图片1内容：2字节*宽*高（大端）：每像素占2字节，int16，RGB565


