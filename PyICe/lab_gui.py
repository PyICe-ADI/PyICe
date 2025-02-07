'''Graphical Interface to Channel Objects'''

from . import lab_core
from PyICe.lab_utils.column_formatter import column_formatter
from PyICe.lab_utils.clean_unicode import clean_unicode
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape as escape
import sys
import os
from PySide2 import QtGui
from PySide2 import QtWidgets
from PySide2 import QtCore
from PySide2.QtCore import SIGNAL, SLOT, QObject, Signal, Slot
import queue
import datetime
import collections
import numbers
import time
import traceback
import re
import textwrap

try:
    import numpy
except ImportError:
    numpymissing = True
else:
    numpymissing = False

import logging
from functools import reduce
debug_logging = logging.getLogger(__name__)
# logfile_handler = logging.FileHandler(filename="lab_gui.debug.log", mode="w")
# debug_logging.addHandler(logfile_handler)

MAX_TAG_ROWS = 4

class data_store():
    ''' this is a very simple hierarchy of key/value pairs. Each can have an ordered list of children. Only int/float/str should be stored
    each pair must have a name but a value is optional'''
    def __init__(self,name=None,value=None,parent=None):
        self._children = []
        self.set_name(name)
        self.set_value(value)
        if parent != None:
            parent.add_child(self)
    def _check_value_ok(self,value):
        if value == None:
            return
        if isinstance(value,str):
            return
        if isinstance(value,int):
            return
        if isinstance(value,float):
            return
        raise DataStoreException('Bad Value')
    def _check_name_ok(self,name):
        if name == None:
            raise DataStoreException('Bad Name {}'.format(name))
        try:
            self._check_value_ok(name)
        except DataStoreException as e:
            raise DataStoreException('Bad Name {}'.format(name))
    def set_name(self,name):
        self._check_value_ok(name)
        self._name = name
    def __getitem__(self,key):
        for child in self._children:
            if child.get_name() == key:
                return child.get_value()
        return None
    def __contains__(self,key):
        for child in self._children:
            if child.get_name() == key:
                return True
        return False
    def __iter__(self):
        for child in self._children:
            yield child
    def __setitem__(self, key, value):
        for child in self._children:
            if child.get_name() == key:
                child.set_value(value)
                return
        data_store(key,value,self)
    def get_name(self):
        return self._name
    def set_value(self,value):
        self._check_value_ok(value)
        self._value = value
    def get_value(self):
        return self._value
    def add_child(self,data_store_object):
        if not isinstance(data_store_object,data_store):
            raise DataStoreException('Addind a non-data_store as a child')
        self._children.append(data_store_object)
    def get_child(self,child_name):
        for child in self._children:
            if child.get_name() == child_name:
                return child
    def _to_xml(self,parent_xml=None):
        if parent_xml == None:
            element = ET.Element('pair')
        else:
            element = ET.SubElement(parent_xml,'pair')
        element.attrib['name'] = self._name
        if self._value:
            element.attrib['value'] = self._value
        for child in self._children:
            child._to_xml(element)
        return element
    def _from_xml(self,element):
        if 'name' in list(element.attrib.keys()):
            self.set_name(element.attrib['name'])
        if 'value' in list(element.attrib.keys()):
            self.set_value(element.attrib['value'])
        for child_xml in element:
            child = data_store()
            child._from_xml(child_xml)
            self.add_child(child)
    def save(self,filename):
        root = self._to_xml()
        tree = ET.ElementTree(root)
        tree.write(filename)
    def load(self,filename):
        tree = ET.parse(filename)
        root = tree.getroot()
        data_store.__init__(self) #clear all data
        self._from_xml(root)
class DataStoreException(Exception):
    pass

class channel_wrapper(object):
    def __init__(self,channel):
        self._channel = channel
        self._name = self._channel.get_name()
        self._tag = self._channel.get_category()
    def get_default_format(self):
        if self.get_formats():
            if self._channel.get_format() is not None:
                return self._channel.get_format()
            elif len(self.get_formats()) > 4:
                return self.get_formats()[4] #Default to first user (non-generic) format if not otherwise specified.
            else:
                try:
                    signed = self.get_attribute('signed')
                except lab_core.ChannelAttributeException as e:
                    signed = False
                if signed:
                    return 'signed dec'
        return None
    def get_channel(self):
        return self._channel
    def get_formats(self):
        try:
            return self._channel.get_formats()
        except AttributeError:
            return []
    def get_presets(self):
        try:
            return self._channel.get_presets()
        except AttributeError:
            return []
    def get_presets_dict(self):
        try:
            return self._channel.get_presets_dict()
        except AttributeError:
            return {}
    def get_preset_description(self, preset_name):
        try:
            return self._channel.get_preset_description(preset_name)
        except AttributeError:
            return None
    def has_preset_descriptions(self):
        try:
            return self._channel.has_preset_descriptions()
        except AttributeError:
            return False
    def get_write_history(self):
        return self._channel.get_write_history()
    def get_tag(self):
        return self._tag
    def set_tag(self,tag):
        self._tag = tag
    def get_name(self):
        return self._name
    def get_description(self):
        return self._channel.get_description()
    def get_attribute(self,attribute_name):
        return self._channel.get_attribute(attribute_name)
    def get_attributes(self):
        return self._channel.get_attributes()
    def get_units(self, format):
        if format is not None:
            return self._channel.get_units(format)
        return ''
    def set_change_callback(self, enable):
        if enable:
            try:
                self._channel.add_change_callback()
            except Exception as e:
                print(e)
        else:
            try:
                self._channel.remove_change_callback()
            except Exception as e:
                print(e)
    def format(self,data,format,use_presets):
        if data is None:
            return 'None'
        if isinstance(data, lab_core.ChannelReadException):
            return data
        if hasattr(self._channel, 'format'):
            data = self._channel.format(data,format,use_presets)
        return data
    def unformat(self,data,format,use_presets):
        if data == "None":
            return None
        if hasattr(self._channel, 'unformat'):
            data = self._channel.unformat(data,format,use_presets)
        else:
            #convert string to number if underlying channel doesn't do format/unformat
            try:
                data = int(data)
            except ValueError:
                try:
                    data = float(data)
                    try:
                        if data == int(data):
                            data = int(data)
                    except (OverflowError, ValueError) as e:
                        #+/-Inf, Nan
                        pass
                except ValueError:
                    try:
                        data = str(data)
                    except:
                        pass
        return data

class display_item(QtWidgets.QLabel,channel_wrapper):
    SI_request_read_channel_list = QtCore.Signal(object)
    SI_request_write_channel_list = QtCore.Signal(object)
    def __init__(self,channel_object):
        QtWidgets.QLabel.__init__(self)
        self._alpha = 0
        #https://en.wikipedia.org/wiki/Web_colors
        self.highlight_color_unfilt = (180,255,0) #Safety
        self.highlight_color_filt = (100,255,100) #Nuclear
        self.highlight_color_avg = (255,150,255) #Light Magenta
        #self.highlight_color_trans = (255,150,150) #Now animated
        # [255,182,192] #LightPink
        # [255,162,172] #LT
        # [180,180,255] #ADI
        self.palette = QtGui.QPalette()
        self.setAutoFillBackground(True)
        self.setPalette(self.palette)
        self.highlight = QtCore.QPropertyAnimation(self, QtCore.QByteArray("alpha".encode("utf-8")))
        self.highlight.setDuration(3500) #msecs
        self.highlight.setStartValue(255)
        self.highlight.setEasingCurve(QtCore.QEasingCurve.OutCirc)
        # self.highlight.setEndValue(80) # green
        self.highlight.setEndValue(40) # safety yellow is more visible, so can be faded further
        channel_wrapper.__init__(self,channel_object)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.connect(self,SIGNAL("customContextMenuRequested(QPoint)"),self, SLOT("contextMenuRequested(QPoint)"))
        self._use_presets_read = True #False
        self._use_presets_write = True
        self._current_raw_data = None
        self._prev_raw_data = None
        self.set_iir("Disabled")
        self._iir_rampto = self._iir_setting
        self._iir_data = None
        self._format = self.get_default_format()
        self._displayed2 = False
        self._wcd = None
        self._flash = True
        self._print = False
        self._data_changed = False
        self._history_length = 40
        self._history = collections.deque(maxlen=self._history_length + 1)
        ttip = "<p><b>{}</b></p>".format(self.get_name())
        if self.get_description():
            ttip += "<p>{}</p>".format(escape(self.get_description())) #put a paragraph in to make it rich text and get the wrapping
        if len(self.get_attributes()) != 0:
            ttip += '<p><table border="0.2">'
            ttip += '<tr><th>Attribute Name:</th><th>Attribute Value:</th></tr>'
            for attribute in self.get_attributes():
                ttip += '<tr><td>{}</td><td>{}</td></tr>'.format(attribute, self.get_attribute(attribute))
            ttip += '</table></p>'
        if self.get_presets_dict():
            ttip += '<p><table border="0.2">' #width="800"
            if self.has_preset_descriptions():
                ttip += '<tr><th>Preset Name:</th><th>Preset Value:</th><th width=700>Preset Description:</th></tr>' #width=80%
            else:
                ttip += '<tr><th>Preset Name:</th><th>Preset Value:</th></tr>'
            for preset, value in self.get_presets_dict().items():
                if self.get_preset_description(preset) is not None:
                    desc_abbrev = self.get_preset_description(preset)
                    max_len = 500 #250
                    if len(desc_abbrev) > max_len:
                        desc_abbrev = desc_abbrev[:max_len-4]+'...'
                    preset_desc = '<td>{}</td>'.format(desc_abbrev)
                else:
                    preset_desc = ''
                ttip += '<tr><td>{}</td><td>{}</td>{}</tr>'.format(preset, value, preset_desc)
            ttip += '</table></p>'
        ttip += '<p><table border="0.2"><tr><th>tag:</th><td>{}</td></tr></table></p>'.format(self.get_tag())
        self.setToolTip(ttip)
        self.update_display(force = True)
    def _get_alpha(self):
        return self._alpha
    def _set_alpha(self, value):
        self._alpha = value
        if self._iir_setting == "Disabled":
            color = self.highlight_color_unfilt
        elif self._iir_setting != self._iir_rampto:
            try:
                color = [255,
                         min(int(round(255.0 * self._iir_rampto / self._iir_setting)),255), #Fade red to yellow.
                         0
                        ]
            except TypeError:
                color = self.highlight_color_avg
        else:
            color = self.highlight_color_filt
        self.palette.setColor(self.backgroundRole(),
                              QtGui.QColor(*color,
                                           a=self._alpha)
                             )
        self.setPalette(self.palette)
    alpha = QtCore.Property(int, _get_alpha, _set_alpha)
    def get_formatted_data(self, raw_data=None):
        formatted_data = self.format(self._current_raw_data if raw_data is None else raw_data,
                                     format=self._format,
                                     use_presets=self._use_presets_read
                                    )
        if self._use_presets_read and not isinstance(formatted_data, numbers.Number):
            units = ""
        elif isinstance(self._format, str) \
                and len(self._format) != 0:
            # A non-null format was specified and numeric data given.
            units = self.get_units(self._format)
        else:
            units = ""
        if isinstance(formatted_data, Exception):
            debug_logging.debug("{} while reading '{}'".format(repr(formatted_data), self.get_name()))
            formatted_data = str(formatted_data)
            if len(formatted_data) > 30:
                formatted_data = "{}...".format(formatted_data[:27])
        if formatted_data is None:
            formatted_data = str(formatted_data)
        elif not isinstance(formatted_data, str):
            try:
                formatted_data = self._channel.format_display(formatted_data)
            except Exception as e:
                debug_logging.warn(e)
                debug_logging.warn(traceback.format_exc())
        debug_logging.debug("GUI display item %s formatted raw data to %s.", self.get_name(), formatted_data)
        result = u'{}{}'.format(formatted_data, units)
        return result
    def set_format(self,new_format):
        self._format = new_format
        self.update_display()
    def set_iir(self,iir):
        self._iir_setting = iir
        #Flush data when changing from signed to unsigned format? TBD...
    def update_display(self,force=False):
        if self.displayed() or force or True:
            txt = "{}: {}".format(self.get_name(),self.get_formatted_data())
            if self._data_changed and self._flash:
                self.highlight.stop()
                self.highlight.start(QtCore.QPropertyAnimation.KeepWhenStopped)
            else:
                if self.highlight.state() == QtCore.QAbstractAnimation.Stopped:
                    self.alpha = 0
            self.setText(txt)
    def update_from_dict(self,data_dict):
        if self.get_name() in list(data_dict.keys()):
            data = data_dict[self.get_name()]
            if hasattr(self._channel,"format") and not isinstance(data_dict[self.get_name()], lab_core.ChannelReadException):
                #channel read data may be pre-formatted by underlying channel.
                #need to un-do before reformatting with GUI settings
                raw_data = self._channel.unformat(data_dict[self.get_name()],format=self._channel.get_format(),use_presets=self._channel.using_presets_read())
            else:
                raw_data = data_dict[self.get_name()]
            debug_logging.debug("GUI display item %s received data %s (%s raw).", self.get_name(), data, raw_data)
            try:
                self._data_changed = bool(raw_data != self._prev_raw_data)
            except ValueError as e:
                # ValueError: The truth value of an array with more than one element is ambiguous. Use a.any() or a.all()
                if not numpymissing and isinstance(raw_data, numpy.ndarray):
                    self._data_changed = (raw_data != self._prev_raw_data).any()
                else:
                    print(type(raw_data))
                    raise e
            self._prev_raw_data = raw_data
            if self._data_changed:
                self._history.append([datetime.datetime.utcnow(), raw_data, 1])
            else:
                try:
                    self._history[-1][2] += 1 #incremement value-unchanged read count
                except IndexError:
                    #if first channel read is None, _data_changed detection doesn't worker
                    self._history.append([datetime.datetime.utcnow(), raw_data, 1])
            try:
                if self._iir_setting == "Disabled":
                    self._current_raw_data = raw_data
                    self._iir_data = None
                    self._iir_rampto = 1
                elif self._iir_data is None:
                    self._current_raw_data = raw_data
                    self._iir_data = float(raw_data)
                    self._iir_rampto = 1
                else:
                    if hasattr(self._channel,"format") and self._channel.get_format() is not None and self._channel.get_format()['signed']:
                        #WARNING: Can't just average signed number!
                        raw_signed = self._channel.twosComplementToSigned(raw_data)
                        iir_signed = self._channel.twosComplementToSigned(self._iir_data)
                        filt_signed = raw_signed + (1 - 1.0/self._iir_rampto) * (iir_signed - raw_signed)
                        self._current_raw_data = self._channel.signedToTwosComplement(filt_signed)
                    else:
                        self._current_raw_data = raw_data + (1 - 1.0/self._iir_rampto) * (self._iir_data - raw_data)
                    self._iir_data = self._current_raw_data
                    if self._iir_setting == "Average" or self._iir_setting > self._iir_rampto:
                        self._iir_rampto += 1
                    elif self._iir_setting < self._iir_rampto:
                        self._iir_rampto = self._iir_setting
            except (TypeError, ValueError) as e:
                print(e, type(e))
                print(traceback.format_exc())
                self._current_raw_data = raw_data
                self._iir_data = None
            except Exception as e:
                print(e, type(e))
                print(traceback.format_exc())
                self._current_raw_data = raw_data
                self._iir_data = None
            self.update_display()
    def display(self,state):
        self._displayed2 = state
    def displayed(self):
        return self._displayed2
    @QtCore.Slot(QtCore.QPoint)
    def contextMenuRequested(self, point):
        menu = QtWidgets.QMenu()
        # presets sub menu
        if len(self.get_presets() ) and self._channel.is_writeable():
            write_preset_menu = QtWidgets.QMenu("Write Preset")
            for preset in self.get_presets():
                action_write_preset = QtWidgets.QAction(preset, write_preset_menu)
                action_write_preset.connect(action_write_preset,SIGNAL("triggered()"),lambda preset=preset: self.write_preset(preset))
                write_preset_menu.addAction(action_write_preset)
            menu.addMenu(write_preset_menu)
        # write recent sub menu
        if len(self.get_write_history() ) and self._channel.is_writeable():
            write_recent_menu = QtWidgets.QMenu("Write Recent")
            for item in reversed(self.get_write_history()):
                action_write_hist = QtWidgets.QAction(str(item), write_recent_menu)
                action_write_hist.connect(action_write_hist,SIGNAL("triggered()"),lambda item=item: self.write([(self.get_name(),item)]))
                write_recent_menu.addAction(action_write_hist)
            menu.addMenu(write_recent_menu)
        # write menu item
        if self._channel.is_writeable():
            action_write = QtWidgets.QAction("Write...",menu)
            self.connect(action_write,SIGNAL("triggered()"),self,SLOT("display_write_dialog()"))
            menu.addAction(action_write)
        # read menu item
        action_read = QtWidgets.QAction("Read",menu)
        self.connect(action_read,SIGNAL("triggered()"),self,SLOT("read_now()"))
        menu.addAction(action_read)
        # copy menu item
        action_copy = QtWidgets.QAction("Copy",menu)
        self.connect(action_copy,SIGNAL("triggered()"),self.copy_clipboard)
        menu.addAction(action_copy)
        # history menu item
        action_print_history = QtWidgets.QAction("Print History",menu)
        self.connect(action_print_history,SIGNAL("triggered()"),self.print_history)
        menu.addAction(action_print_history)
        #print tooltip menu item - some tooltips are so big, they don't fit on the screen
        action_print_tooltip = QtWidgets.QAction("Print Info",menu)
        self.connect(action_print_tooltip,SIGNAL("triggered()"),self.print_tooltip)
        menu.addAction(action_print_tooltip)
        # formats sub menu
        if len(self.get_formats()):
            format_menu = QtWidgets.QMenu("Select Format")
            action_set_format = QtWidgets.QAction("None",format_menu,checkable=True)
            if self._format == None:
                action_set_format.setChecked(True)
            self.connect(action_set_format,SIGNAL("triggered()"), lambda : self.set_format(None))
            format_menu.addAction(action_set_format)
            for reg_format in self.get_formats():
                action_set_format = QtWidgets.QAction(reg_format,format_menu,checkable=True)
                if reg_format == self._format:
                    action_set_format.setChecked(True)
                action_set_format.connect(action_set_format,SIGNAL("triggered()"),lambda reg_format=reg_format: self.set_format(reg_format))
                format_menu.addAction(action_set_format)
            menu.addMenu(format_menu)
        # iir filter sub menu
        iir_menu = QtWidgets.QMenu("IIR Filter")
        for iir in ["Disabled",2,4,8,16,32,64,128,256,512,1024,2048,4096,8192,16384,32768,65536,"Average"]:
            action_set_iir = QtWidgets.QAction(str(iir),iir_menu,checkable=True)
            if iir == self._iir_setting:
                action_set_iir.setChecked(True)
            action_set_iir.connect(action_set_iir,SIGNAL("triggered()"),lambda iir=iir: self.set_iir(iir))
            iir_menu.addAction(action_set_iir)
        menu.addMenu(iir_menu)
        # use presets read menu item
        action_use_read_presets = QtWidgets.QAction("Use Read Presets",menu,checkable=True)
        menu.addAction(action_use_read_presets)
        if self._use_presets_read:
            action_use_read_presets.setChecked(True)
        self.connect(action_use_read_presets,SIGNAL("toggled(bool)"),self,SLOT("setUseReadPresets(bool)"))
        # use presets write menu item
        if self._channel.is_writeable():
            action_use_write_presets = QtWidgets.QAction("Use Write Presets",menu,checkable=True)
            menu.addAction(action_use_write_presets)
            if self._use_presets_write:
                action_use_write_presets.setChecked(True)
            self.connect(action_use_write_presets,SIGNAL("toggled(bool)"),self,SLOT("setUseWritePresets(bool)"))
        # flash on change menu item
        action_flash_on_change = QtWidgets.QAction("Flash on Change",menu,checkable=True)
        menu.addAction(action_flash_on_change)
        if self._flash:
            action_flash_on_change.setChecked(True)
        self.connect(action_flash_on_change,SIGNAL("toggled(bool)"),self,SLOT("setFlash(bool)"))
        # print on change menu item
        action_print_on_change = QtWidgets.QAction("Print on Change",menu,checkable=True)
        menu.addAction(action_print_on_change)
        if self._print:
            action_print_on_change.setChecked(True)
        self.connect(action_print_on_change,SIGNAL("toggled(bool)"),self,SLOT("setPrint(bool)"))
        menu.exec_(self.mapToGlobal(point))
    def copy_clipboard(self):
        app = self.parentWidget().parentWidget().parentWidget().parentWidget().parentWidget().parentWidget().parentWidget().parentWidget().parentWidget()
        app.cb.setText(str(self.get_formatted_data()))
    def print_history(self):
        request_time = datetime.datetime.utcnow()
        if not len(self._history):
            debug_logging.info(("{} has no change history at "
                                "{}").format(self.get_name(), request_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ')))
            return
        debug_logging.info("{} change history at {}".format(self.get_name(),
                                                            request_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ')))
        row_col_data = [["ID:","TIME_REL_NOW","DURATION","FMT","RAW","COUNT"]]
        def hms(seconds):
                minutes = int(seconds / 60)
                seconds = seconds - 60 * minutes
                hours = int(minutes / 60)
                minutes = minutes - 60 * hours
                return {"hours"   : hours,
                        "minutes" : minutes,
                        "seconds" : seconds
                       }
        time_fmt = "{prefix}{hours:02d}:{minutes:02d}:{seconds:06.3f}{postfix}"
        for idx, [timestamp, raw_data, read_count] in enumerate(self._history):
            prefix = ""
            if len(self._history) != self._history_length + 1:
                #dequeue not yet filled
                if idx == 0:
                    #Indicate measurment time is after signal change time by uncertain period.
                    prefix = "+"
            else:
                if idx == 0:
                    #Skip oldest reading with uncertain transisition time after dequeue fills.
                    continue
            t_rel = time_fmt.format(prefix="-",postfix="",**hms((request_time-timestamp).total_seconds()))

            try:
                t_duration = time_fmt.format(prefix=prefix,postfix=" ",**hms((self._history[idx+1][0]-timestamp).total_seconds()))
            except IndexError:
                #t_duration = " --:--:--.---"
                t_duration = time_fmt.format(prefix=prefix,postfix="+",**hms((request_time-timestamp).total_seconds()))
            row_col_data.append(["{:02d}:".format(idx), t_rel, t_duration, self.get_formatted_data(raw_data), raw_data, read_count])
        debug_logging.info(column_formatter(row_col_data,padding=2,justification="right"))
    def print_tooltip(self):
        col_widths = []
        max_width = 80
        # max_width = 132
        col_widths.append(26) #first column
        col_widths.append(15) # second column
        col_widths.append(max_width - reduce(lambda x,y: x+y, col_widths))

        infotxt = str(self.toolTip())
        infotxt = re.sub('</?b>', '', infotxt)
        infotxt = re.sub('</?p>', '\n', infotxt)
        infotxt = re.sub('</?table.*?>', '', infotxt)
        infotxt = re.sub('<tr>', '', infotxt)
        infotxt = re.sub('</tr>', '\n', infotxt)
        infotxt = re.sub('<th.*?>', '', infotxt)
        infotxt = re.sub('</th>', '\t', infotxt)
        infotxt = re.sub('<td>', '', infotxt)
        infotxt = re.sub('</td>', '\t', infotxt)
        lines = infotxt.splitlines()
        infotxt = '#' * max_width
        for line in lines:
            fields = line.split('\t')
            fields = [clean_unicode(field) for field in fields] #Remove remaining Unicode
            if len(fields) == 1:
                infotxt += textwrap.fill(fields[0], width=max_width, subsequent_indent='  ')
            else:
                if fields[-1] == '':
                    fields.pop()
                for i, field in enumerate(fields):
                    if i < len(fields) -1:
                        spacer = '\N{MIDDLE DOT}' * (col_widths[i] - len(field)) #Unicode U+00B7 Middle Dot
                        # spacer = '.' * (col_widths[i] - len(field)) #Lower 7 bits of Ascii might be safer. Period mark is bolder than Middle Dot.
                    else:
                        spacer = ''
                    if i == len(col_widths) - 1:
                        indent = ' ' * reduce(lambda x,y: x+y, col_widths[:-1])
                        field = textwrap.fill(field, width=max_width, initial_indent=indent, subsequent_indent=indent + '  ')
                        field = field[len(indent):]
                    infotxt += '{}{}'.format(field, spacer)
            infotxt += '\n'
        infotxt += '#' * max_width
        debug_logging.info(infotxt)
    @QtCore.Slot()
    def display_write_dialog(self):
        if not self._wcd: #not yet created
            self._create_write_dialog()
            self._wcd.move(300, 150)
            self._wcd.update_format(self._format)
            self._wcd.set_value(self.format(self._current_raw_data,format=self._format,use_presets=self._use_presets_read))
        else: #already exists
            if self._wcd.isHidden():
                #window was created, then closed. Re-sync with display_item settings
                self._wcd.update_format(self._format)
                self._wcd.set_value(self.format(self._current_raw_data,format=self._format,use_presets=self._use_presets_read))
        self._wcd.show()
        self._wcd.activateWindow()
        self._wcd.raise_()
    def _create_write_dialog(self):
        self._wcd = write_channel_dialog(self._channel,self._current_raw_data,self._format,self._use_presets_write)
        self._wcd.SI_request_write_channel_list.connect(self.write)
        #self.connect(self._wcd,SIGNAL('request_write_channel_list(PyQt_PyObject)'),self.write)
    def mouseDoubleClickEvent(self, event):
        self.read_now()
    @QtCore.Slot()
    def read_now(self):
        self.SI_request_read_channel_list.emit([self.get_name()])
        #self.emit(SIGNAL("request_read_channel_list(PyQt_PyObject)"), [self.get_name()] )
    @QtCore.Slot(bool)
    def setUseReadPresets(self,state):
        self._use_presets_read = state
        self.update_display()
    @QtCore.Slot(bool)
    def setUseWritePresets(self,state):
        self._use_presets_write = state
    @QtCore.Slot(bool)
    def setFlash(self,state):
        self._flash = state
    @QtCore.Slot(bool)
    def setPrint(self,state):
        self._print = state
        self.set_change_callback(state)
    def write_preset(self,preset):
        data = self.unformat(preset,format=None,use_presets=True)
        self.write( [(self.get_name(),data)] )
    def write(self,data):
        self.SI_request_write_channel_list.emit(data)
        #self.emit(SIGNAL("request_write_channel_list(PyQt_PyObject)"),data)
        if self._channel.is_readable():
            self.SI_request_read_channel_list.emit([data_pair[0] for data_pair in data])
            #self.emit(SIGNAL("request_read_channel_list(PyQt_PyObject)"),[data_pair[0] for data_pair in data])
    def save(self,ds_parent):
        di_ds = data_store('display_item',self.get_name(),ds_parent)
        di_ds['use_presets_read'] = str(self._use_presets_read)
        di_ds['use_presets_write'] = str(self._use_presets_write)
        di_ds['format'] = str(self._format) #Always save, even if None. Allows auto-format selection to be un-done in config.
        di_ds['flash'] = str(self._flash)
        di_ds['print'] = str(self._print)
        di_ds['tag'] = str(self.get_tag())
        if self._wcd:
            di_ds['write_dialog_container'] = 'True'
            self._wcd.save( di_ds.get_child('write_dialog_container') )
        di_ds['iir_setting'] = str(self._iir_setting)
    def load(self,ds_parent):
        di_ds = ds_parent.get_child('display_item')
        if di_ds:
            assert di_ds.get_value() == self.get_name()
            self._use_presets_read = di_ds['use_presets_read'] == 'True'
            self._use_presets_write = di_ds['use_presets_write'] == 'True'
            if di_ds['format'] == 'None':
                self._format = None
            elif di_ds['format'] in self.get_formats():
                self._format = di_ds['format']
            self._flash = di_ds['flash'] == 'True'
            if di_ds['print'] == 'True':
                self.setPrint(True)
            if di_ds['write_dialog_container']:
                self._create_write_dialog()
                self._wcd.load( di_ds.get_child('write_dialog_container') )
            if di_ds['iir_setting']:
                try:
                    self._iir_setting = int(di_ds['iir_setting'])
                except ValueError:
                    self._iir_setting = di_ds['iir_setting']

class display_tag(QtWidgets.QLabel):
    SI_request_read_tag =  QtCore.Signal(object)
    def __init__(self,tag_name):
        self.tag_name = tag_name
        QtWidgets.QLabel.__init__(self, "<center><u><b>{}</b></u></center>".format(self.tag_name))
        self._displayed = False
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.connect(self,SIGNAL("customContextMenuRequested(QPoint)"),self, SLOT("contextMenuRequested(QPoint)"))
    def get_name(self):
        return ''
    def get_tag(self):
        return self.tag_name
    def display(self,state):
        self._displayed = state
    def displayed(self):
        return self._displayed
    def update_from_dict(self,data_dict):
        pass
    def save(self,ds_parent):
        pass
    def load(self,ds_parent):
        pass
    def setFlash(self,bool):
        pass
    def setUseReadPresets(self,bool):
        pass
    def setUseWritePresets(self,bool):
        pass
    @QtCore.Slot(QtCore.QPoint)
    def contextMenuRequested(self, point):
        menu = QtWidgets.QMenu()
        # read menu item
        action_read = QtWidgets.QAction("Read Tag",menu)
        self.connect(action_read,SIGNAL("triggered()"),self,SLOT("read_tag()"))
        menu.addAction(action_read)
        # # use presets read menu item
        # action_use_read_presets = QtWidgets.QAction("Use Read Presets",menu,checkable=True)
        # menu.addAction(action_use_read_presets)
        # if self._use_presets_read:
        #     action_use_read_presets.setChecked(True)
        # self.connect(action_use_read_presets,SIGNAL("toggled(bool)"),self,SLOT("setUseReadPresets(bool)"))
        # # use presets write menu item
        # if self._channel.is_writeable():
        #     action_use_write_presets = QtWidgets.QAction("Use Write Presets",menu,checkable=True)
        #     menu.addAction(action_use_write_presets)
        #     if self._use_presets_write:
        #         action_use_write_presets.setChecked(True)
        #     self.connect(action_use_write_presets,SIGNAL("toggled(bool)"),self,SLOT("setUseWritePresets(bool)"))
        # # flash on change menu item
        # action_flash_on_change = QtWidgets.QAction("Flash on Change",menu,checkable=True)
        # menu.addAction(action_flash_on_change)
        # if self._flash:
        #     action_flash_on_change.setChecked(True)
        # self.connect(action_flash_on_change,SIGNAL("toggled(bool)"),self,SLOT("setFlash(bool)"))
        # # print on change menu item
        # action_print_on_change = QtWidgets.QAction("Print on Change",menu,checkable=True)
        # menu.addAction(action_print_on_change)
        # if self._print:
        #     action_print_on_change.setChecked(True)
        # self.connect(action_print_on_change,SIGNAL("toggled(bool)"),self,SLOT("setPrint(bool)"))
        menu.exec_(self.mapToGlobal(point))
    @QtCore.Slot()
    def read_tag(self):
        self.SI_request_read_tag.emit(self.get_tag())

class write_channel_dialog(QtWidgets.QDialog,channel_wrapper):
    SI_request_write_channel_list =  QtCore.Signal(object)
    def __init__(self,channel_object,current_raw_data,format,use_presets_write):
        QtWidgets.QDialog.__init__(self)
        channel_wrapper.__init__(self,channel_object)
        self.setWindowTitle("Write {}".format(self.get_name()))
        self._use_presets_write = use_presets_write
        self._format = format
        self._current_raw_data = current_raw_data
        self.init_interface()
    def init_interface(self):
        layout = QtWidgets.QVBoxLayout()
        # value box
        self.value_text_box = QtWidgets.QLineEdit(str(self.format(self._current_raw_data, self._format, self._use_presets_write)))
        self.value_text_box.setFocus()
        layout.addWidget( QtWidgets.QLabel("Value:"))
        layout.addWidget(self.value_text_box)
        # formats
        if len(self.get_formats()):
            layout.addWidget( QtWidgets.QLabel("Format:"))
            self.formats_combo  = QtWidgets.QComboBox()
            self.formats_combo.addItem("None")
            for format in self.get_formats():
                self.formats_combo.addItem(format)
            self.formats_combo.setCurrentIndex(self.formats_combo.findText("None" if self._format is None else self._format))
            layout.addWidget(self.formats_combo)
            self.connect(self.formats_combo,SIGNAL("currentIndexChanged (QString)"),self.update_format)
            self.link_format_checkbox = QtWidgets.QCheckBox('Link Format',self)
            layout.addWidget(self.link_format_checkbox)
        # presets
        if len(self.get_presets()):
            presest_checkbox = QtWidgets.QCheckBox('Use Presets',self)
            if self._use_presets_write:
                presest_checkbox.setCheckState( QtCore.Qt.Checked )
            self.connect(presest_checkbox,SIGNAL("stateChanged(int)"),self.update_use_presets_write)
            layout.addWidget(presest_checkbox)
        # increment
        layout.addWidget( QtWidgets.QLabel("Increment Value:"))
        self.increment_text_box = QtWidgets.QLineEdit("1")
        layout.addWidget(self.increment_text_box)
        increment_widget = QtWidgets.QWidget()
        increment_layout = QtWidgets.QHBoxLayout()
        dec_button = QtWidgets.QPushButton("-")
        dec_button.setDefault(False)
        dec_button.setAutoDefault(False)
        self.connect(dec_button,SIGNAL('clicked()'),self.decrement)
        increment_layout.addWidget( dec_button )
        inc_button = QtWidgets.QPushButton("+")
        inc_button.setDefault(False)
        inc_button.setAutoDefault(False)
        self.connect(inc_button,SIGNAL('clicked()'),self.increment)
        increment_layout.addWidget(inc_button)
        increment_widget.setLayout(increment_layout)
        layout.addWidget(increment_widget)
        # write close
        write_close_widget = QtWidgets.QWidget()
        write_close_layout = QtWidgets.QHBoxLayout()
        write_button = QtWidgets.QPushButton("Write")
        write_button.setDefault(True)
        write_button.setAutoDefault(True)
        self.connect(write_button,SIGNAL("clicked()"),self.write)
        write_close_layout.addWidget( write_button )
        write_close_button = QtWidgets.QPushButton("Write + Close")
        write_close_button.setDefault(False)
        write_close_button.setAutoDefault(False)
        self.connect(write_close_button,SIGNAL("clicked()"),self.write_close)
        write_close_layout.addWidget(write_close_button)
        write_close_widget.setLayout(write_close_layout)
        layout.addWidget(write_close_widget)
        self.setLayout(layout)
    def get_value(self):
        return str(self.value_text_box.displayText())
    def get_increment(self):
        return str(self.increment_text_box.displayText())
    def set_increment(self,text):
        self.increment_text_box.setText(text)
    def set_value(self,value):
        self.value_text_box.setText(str(value))
    def increment(self):
        if self.get_value() == "None":
            value = 0
        elif self.get_value() == "True":
            raise ValueError("Can't increment 'True'.")
        elif self.get_value() == "False":
            self.set_value(True)
            self.write()
            return
        elif self._format in ('hex','bin'):
            #special handling for default formats. others should tolerate float conversion.
            value = self.unformat(self.get_value(), self._format, self._use_presets_write)
        else:
            value = float(self.get_value())
        result = float(value + float(self.get_increment()))
        if result == int(result):
            result = int(result)
        if self._format in ('hex','bin'):
            #special handling for default formats. others should tolerate float conversion.
            try:
                result = self.format(result, self._format, self._use_presets_write)
            except Exception as e:
                print(e)
                print(traceback.format_exc())
                return
        self.set_value(result)
        self.write()
    def decrement(self):
        if self.get_value() == "None":
            value = 0
        elif self.get_value() == "True":
            self.set_value(False)
            self.write()
            return
        elif self.get_value() == "False":
            raise ValueError("Can't decrement 'False'.")
        elif self._format in ('hex','bin'):
            #special handling for default formats. others should tolerate float conversion.
            value = self.unformat(self.get_value(), self._format, self._use_presets_write)
        else:
            value = float(self.get_value())
        result = float(value - float(self.get_increment()))
        if result == int(result):
            result = int(result)
        if self._format in ('hex','bin'):
            #special handling for default formats. others should tolerate float conversion.
            try:
                result = self.format(result, self._format, self._use_presets_write)
            except Exception as e:
                print(e)
                print(traceback.format_exc())
                return
        self.set_value(result)
        self.write()
    def write_close(self):
        self.write()
        self.close()
    def write(self):
        data = self.unformat(self.get_value(),self._format,self._use_presets_write)
        self.SI_request_write_channel_list.emit([(self.get_name(), data)])
        #self.emit(SIGNAL("request_write_channel_list(PyQt_PyObject)"),[(self.get_name(), data)] )
    def update_use_presets_write(self,state):
        unformatted_data = self.unformat(self.get_value(), self._format, self._use_presets_write)
        self._use_presets_write = state
        self.set_value(str(self.format(unformatted_data, self._format, self._use_presets_write)))
    def update_format(self,format):
        format = str(format) #dump QString
        if format == "None":
            format = None
        try:
            if hasattr(self,'link_format_checkbox') and self.link_format_checkbox.checkState():
                old_value = self.unformat(self.get_value(),self._format,self._use_presets_write)
                new_text = self.format(old_value,format,self._use_presets_write)
                self.set_value(new_text)
        except ValueError as e:
            pass
        self._format = format
        if  hasattr(self,'formats_combo'):
            self.formats_combo.setCurrentIndex(self.formats_combo.findText("None" if format is None else str(format)))
    def save(self,ds_parent):
        dcwd_ds = data_store('write_channel_dialog_data',self.get_name(),ds_parent)
        dcwd_ds['value'] = str(self.get_value())
        dcwd_ds['use_presets_write'] = str(self._use_presets_write)
        if len(self.get_formats()):
            dcwd_ds['format'] = str(self._format)
            if self.link_format_checkbox.checkState() == 2:
                dcwd_ds['link'] = 'True'
        dcwd_ds['increment'] = str(self.get_increment())
        dcwd_ds['visible'] = str( self.isVisible() )
        dcwd_ds['xpos'] = str( self.pos().x() )
        dcwd_ds['ypos'] = str( self.pos().y() )
    def load(self,ds_parent):
        dcwd_ds = ds_parent.get_child('write_channel_dialog_data')
        if dcwd_ds:
            assert dcwd_ds.get_value() == self.get_name()
            if self._current_raw_data is None:
                self.set_value(dcwd_ds['value'])
                #default to more recently read data than saved default if available
            self._use_presets_write = dcwd_ds['use_presets_write'] == 'True'
            if dcwd_ds['format'] :
                index =  self.formats_combo.findText(dcwd_ds['format'])
                if index != -1:
                    self.formats_combo.setCurrentIndex(index)
            if len(self.get_formats()):
                if dcwd_ds['link']:
                    self.link_format_checkbox.setCheckState( QtCore.Qt.Checked )
            if dcwd_ds['increment']:
                self.set_increment( dcwd_ds['increment'] )
            if dcwd_ds['visible'] == "True":
                self.show()
                self.move(int(dcwd_ds['xpos']),int(dcwd_ds['ypos']))

class display_item_group(QtWidgets.QWidget):
    SI_request_read_channel_list = QtCore.Signal(object)
    SI_request_write_channel_list = QtCore.Signal(object)
    SI_change_font_size = QtCore.Signal(int)
    def __init__(self,channel_group_object):
        QtWidgets.QWidget.__init__(self)
        self.display_items = []
        self._filter_list = []
        self.init_interface()
        self._continuous_read = False
        self._tagged_sort = True
        self._expecting_data = False
        self._font = QtGui.QFont() #used for display items
        self._channel_group = channel_group_object
        self.populate_from_channel_group(channel_group_object)
        self.build_interface()
        self.signals = []

        self.palette = QtGui.QPalette()
        self.setAutoFillBackground(True)
        self.setPalette(self.palette)
        self._busy_alpha = 0
        self.busy_highlight = QtCore.QPropertyAnimation(self, QtCore.QByteArray("busy_alpha".encode('utf-8')))
        self.busy_highlight.setDuration(3500) #msecs
        self.busy_highlight.setStartValue(0)
        self.busy_highlight.setEasingCurve(QtCore.QEasingCurve.InCirc)
        self.busy_highlight.setEndValue(255)
    def _get_busy_alpha(self):
        return self._busy_alpha
    def _set_busy_alpha(self, value):
        self._busy_alpha = value
        color = QtGui.QColor(230,230,255,a=self._busy_alpha)
        self.palette.setColor(self.backgroundRole(), color)
        self.setPalette(self.palette)
    busy_alpha = QtCore.Property(int, _get_busy_alpha, _set_busy_alpha)
    def populate_from_channel_group(self,channel_group_object):
        tags = []
        for channel in channel_group_object:
            tags += channel.get_tags()
            for tag in channel.get_tags():
                di = display_item(channel)
                di.set_tag(tag)
                di.setFont(self._font)
                di.SI_request_read_channel_list.connect(self.read_channel_list)
                di.SI_request_write_channel_list.connect(self.write_channel_list)
                self.add_display_item(di)
        tags = set(tags)
        for tag in tags:
            dt = display_tag(tag)
            self.add_display_item(dt)
            dt.SI_request_read_tag.connect(self.read_tag)
    def add_display_item(self,item):
        self.display_items.append(item)
    def sort(self):
        if self._tagged_sort:
            key = lambda di: '{}______{}'.format(di.get_tag(),di.get_name()).upper()
        else:
            key = lambda item: item.get_name().upper()
        self.display_items.sort(key = key)
    def inclusive_filter(self,filter_list=None):
        #filter_list is a list of tag names to filter on
        if filter_list is None:
            #re-run filter when self._tagged_sort changes
            filter_list = self._filter_list
        else:
            self._filter_list = filter_list
        for di in self.display_items:
            if di.get_tag() in filter_list:
                if isinstance(di, display_tag):
                    if self._tagged_sort:
                        di.display(True)
                    else:
                        di.display(False) #False
                else:
                    di.display(True)
            else:
                di.display(False)
        self.build_interface()
    def init_interface(self):
        layout = QtWidgets.QVBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignTop)
        self.gc = QtWidgets.QWidget()
        self.grid_container_container = QtWidgets.QWidget()
        container_container_layout = QtWidgets.QHBoxLayout()
        container_container_layout.setAlignment(QtCore.Qt.AlignLeft)
        self.grid_container_container.setLayout(container_container_layout)
        container_container_layout.addWidget(self.gc)
        layout.addWidget(self.grid_container_container)
        self.setLayout(layout)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.connect(self,SIGNAL("customContextMenuRequested(QPoint)"),self.contextMenuRequested)
    @QtCore.Slot()
    def resize_main_window(self):
        self.build_interface()
    def build_interface(self):
        self._grid = QtWidgets.QGridLayout()
        self._grid.setAlignment(QtCore.Qt.AlignLeft)
        self._grid.setHorizontalSpacing(10)
        self._grid.setVerticalSpacing(5)
        self.grid_container_container.layout().removeWidget(self.gc)
        self.gc = QtWidgets.QWidget()
        self.grid_container_container.layout().addWidget(self.gc)
        self.gc.setLayout(self._grid)
        for di in self.display_items:
            di.setParent(None)
        y_pos = 0
        x_pos = 0
        column_height = 0
        self.columnWidths = []
        self.columnWidths.append(0)
        self.sort()
        for di in self.display_items:
            if di.displayed():
                if column_height > 0 and column_height + di.sizeHint().height() + self._grid.verticalSpacing() > self.parentWidget().size().height() - 60:
                    #self.frameGeometry().height()
                    #60 offset may have something to do with grid.contentsMargins() and layout placement, possibly another grid.verticalSpacing() too. Used to prevent frame from oversizing and creating vertical scroll
                    y_pos = 0
                    x_pos += 1
                    self.columnWidths.append(0)
                    column_height = 0
                self._grid.addWidget(di, y_pos, x_pos)
                di.column_placement = x_pos
                column_height += di.sizeHint().height() + self._grid.verticalSpacing()
                y_pos += 1
    @QtCore.Slot()
    def read_channel_list(self,channel_list):
        self._expecting_data = True
        self.SI_request_read_channel_list.emit(channel_list)
        self.busy_highlight.start(QtCore.QPropertyAnimation.KeepWhenStopped)
    @QtCore.Slot()
    def write_channel_list(self,channel_list):
        self.SI_request_write_channel_list.emit(channel_list)
        #self.emit(SIGNAL('request_write_channel_list(PyQt_PyObject)'),channel_list)
    def update_column_width(self, di):
        if di.displayed():
            if di.sizeHint().width() > self.columnWidths[di.column_placement]:
                self._grid.setColumnMinimumWidth(di.column_placement, di.sizeHint().width())
                self.columnWidths[di.column_placement] = di.sizeHint().width()
    def receive_channel_data(self,data_dict):
        for di in self.display_items:
            di.update_from_dict(data_dict)
            self.update_column_width(di)
        if self._expecting_data and self._continuous_read:
            self._expecting_data = False
            if len(data_dict) > 0:
                # debug_logging.debug("Issuing request_read_all() for continuous read")
                self.request_read_all()
        self.busy_highlight.stop()
        self.busy_alpha = 0
    def receive_passive_channel_data(self,data_dict):
        for di in self.display_items:
            di.update_from_dict(data_dict)
            self.update_column_width(di)
    def contextMenuRequested(self, point):
        menu = QtWidgets.QMenu()
        # write menu item
        action_read = QtWidgets.QAction("Read All",menu)
        action_read.setShortcut(QtGui.QKeySequence(QtCore.Qt.CTRL + QtCore.Qt.Key_R)) #doesn't do anything out of context, but reminds user of hotkey
        self.connect(action_read,SIGNAL("triggered()"),self.request_read_all)
        menu.addAction(action_read)
        # continuous read
        action_continuous_read = QtWidgets.QAction("Continuous Read",menu,checkable=True)
        menu.addAction(action_continuous_read)
        if self._continuous_read:
            action_continuous_read.setChecked(True)
        self.connect(action_continuous_read,SIGNAL("toggled(bool)"),self.set_continuous_read)
        menu.addSeparator()
        # all tab items menu
        tab_use_write_presets = QtWidgets.QAction("Use Write Presets",menu)
        self.connect(tab_use_write_presets,SIGNAL('triggered()'), lambda: self.use_write_presets(True))
        menu.addAction(tab_use_write_presets)
        tab_no_write_presets = QtWidgets.QAction("Don't Use Write Presets",menu)
        self.connect(tab_no_write_presets,SIGNAL('triggered()'), lambda: self.use_write_presets(False))
        menu.addAction(tab_no_write_presets)
        tab_use_read_presets = QtWidgets.QAction("Use Read Presets",menu)
        self.connect(tab_use_read_presets,SIGNAL('triggered()'), lambda: self.use_read_presets(True))
        menu.addAction(tab_use_read_presets)
        tab_no_read_presets = QtWidgets.QAction("Don't Use Read Presets",menu)
        self.connect(tab_no_read_presets,SIGNAL('triggered()'), lambda: self.use_read_presets(False))
        menu.addAction(tab_no_read_presets)
        menu.addSeparator()
        tab_flash_on_change = QtWidgets.QAction("Flash on Change",menu)
        self.connect(tab_flash_on_change,SIGNAL('triggered()'), lambda: self.flash_on_change(True))
        menu.addAction(tab_flash_on_change)
        tab_no_flash_on_change = QtWidgets.QAction("Don't Flash on Change",menu)
        self.connect(tab_no_flash_on_change,SIGNAL('triggered()'), lambda: self.flash_on_change(False))
        menu.addAction(tab_no_flash_on_change)
        menu.addSeparator()
        increase_font_size = QtWidgets.QAction("Increase Font Size",menu)
        increase_font_size.triggered.connect(lambda: self.change_font_size(1))
        menu.addAction(increase_font_size)
        decrease_font_size = QtWidgets.QAction("Decrease Font Size",menu)
        decrease_font_size.triggered.connect(lambda: self.change_font_size(-1))
        menu.addAction(decrease_font_size)
        menu.addSeparator()
        self.tagged_sort = QtWidgets.QAction("Categorized Sort",menu,checkable=True)
        self.tagged_sort.setChecked(self._tagged_sort)
        self.connect(self.tagged_sort,SIGNAL('toggled(bool)'), self.set_tagged_sort)
        menu.addAction(self.tagged_sort)
        menu.exec_(self.mapToGlobal(point))
        self.SI_change_font_size.connect(self.change_font_size)
        #self.connect(self,SIGNAL("change_font_size(int)"),self.change_font_size)
    def wheelEvent(self, QWheelEvent):
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        if modifiers == QtCore.Qt.ControlModifier:
            #15 degree physical steps * eight's of a degree resolution = +/-120 count typical single movement.
            #self.change_font_size(int(round(QWheelEvent.delta()/120.0)))
            self.change_font_size(1 if QWheelEvent.delta() > 0 else -1) #independent of mouse resolution, but doesn't support super-mega-rapid-zoom
        else:
            QWheelEvent.ignore() #allow signal to bubble up to scroll function (hold meta/alt with wheel)
    def change_font_size(self, increment):
        self._font.setPointSize(max(self._font.pointSize()+increment, 1))
        for di in self.display_items:
            di.setFont(self._font)
        self.build_interface()
        if increment != 0:
            debug_logging.info("Font changed to {}pt.".format(self._font.pointSize()))
    def request_read_all(self):
        channel_list = []
        for di in self.display_items:
            if di.displayed() and isinstance(di,display_item):
                #exclude invisible channels and tag heading labels
                channel_list.append(di.get_name())
        self.read_channel_list(channel_list)
    def read_tag(self, tag_name):
        channel_list = []
        for di in self.display_items:
            if di.displayed() and isinstance(di,display_item) and tag_name == di.get_tag():
                #exclude invisible channels and tag heading labels
                channel_list.append(di.get_name())
        self.read_channel_list(channel_list)
    def mouseDoubleClickEvent(self, event):
        self.request_read_all()
    def set_continuous_read(self,bool):
        self._continuous_read = bool
        if bool:
            self.request_read_all()
    def get_continuous_read(self):
        return self._continuous_read
    def set_tagged_sort(self, enabled):
        self._tagged_sort = enabled
        self.inclusive_filter()
        self.build_interface()
    def wake(self):
        if self._continuous_read:
            self.request_read_all()
    def save(self,ds_parent):
        dig_ds = data_store('display_group',None,ds_parent)
        dig_ds['continuous'] = str(self._continuous_read)
        dig_ds['font_size'] = str(self._font.pointSize())
        dig_ds['tagged_sort'] = str(self._tagged_sort)
        for di in self.display_items:
            di_ds = data_store('display_item',di.get_name(),dig_ds)
            di.save(di_ds)
    def load(self,ds_parent):
        dig_ds = ds_parent.get_child('display_group')
        self._continuous_read = dig_ds['continuous'] == 'True'
        if dig_ds['font_size'] is not None:
            self._font.setPointSize(int(dig_ds['font_size']))
        self.change_font_size(increment=0) #force redraw
        self.set_tagged_sort(dig_ds['tagged_sort'] == 'True')
        for di_ds in dig_ds:
            di_name = di_ds.get_value()
            for di in  self.display_items:
                if di.get_name() == di_name and di.get_tag() == di_ds.get_child('display_item')['tag']:
                    di.load(di_ds)
    def use_write_presets(self,bool):
        for di in self.display_items:
            di.setUseWritePresets(bool)
    def use_read_presets(self,bool):
        for di in self.display_items:
            di.setUseReadPresets(bool)
    def flash_on_change(self,bool):
        for di in self.display_items:
            di.setFlash(bool)
    def cleanup_upon_disconnect(self):
        self._expecting_data = False
        # FIXME FL: self._continuous_read = False  # Would be nice to be able to switch to a tab that had been continuously reading and have it resume automatically.

class display_tag_group(QtWidgets.QWidget):
    SI_stateChanged = QtCore.Signal()
    def __init__(self,channel_group_object):
        QtWidgets.QWidget.__init__(self)
        self.channel_group_object = channel_group_object
        self._tags = self._create_tag_list()
        self._check_boxes = {} #dictionary of qcheckboxes indexed by tag name
        self.suppress_update = False
        self.init_interface()
    def get_tags(self):
        return self._tags
    def get_selected_tags(self):
        selected_tags = []
        for (tag_name,check_box) in list(self._check_boxes.items()):
            if check_box.checkState():
                selected_tags.append(tag_name)
        return selected_tags
    def _create_tag_list(self):
        tags = []
        for channel in self.channel_group_object:
            tags += self._get_tags(channel)
        tags = list(set(tags))
        tags.sort(key=lambda s: str(s).upper())
        return tags
    def _get_tags(self,channel):
        try:
            return channel.get_tags()
        except AttributeError:
            return None
    def init_interface(self):
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum))
        layout = QtWidgets.QHBoxLayout()
        tagLabelwidget = QtWidgets.QLabel(self)
        tagLabelwidget.setText("<p style=font-size:16px;><b>tags:</b></p>")
        layout.addWidget(tagLabelwidget,0)
        tag_sel_group_widget = QtWidgets.QWidget(self)
        tag_layout =  QtWidgets.QGridLayout()
        tag_sel_group_widget.setLayout(tag_layout)
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidget(tag_sel_group_widget)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        layout.addWidget(self.scroll_area,0) #add the display_item_group at the top
        x_pos=0
        y_pos=0
        for tag_name in self.get_tags():
            new_tag_check_box = QtWidgets.QCheckBox(str(tag_name),tag_sel_group_widget)
            tag_layout.addWidget(new_tag_check_box,y_pos,x_pos)
            self._check_boxes[tag_name] = new_tag_check_box
            new_tag_check_box.setCheckState(QtCore.Qt.Unchecked)
            self.connect(new_tag_check_box, QtCore.SIGNAL("stateChanged(int)"), self._on_change)
            y_pos += 1
            if y_pos >= MAX_TAG_ROWS:
                x_pos += 1
                y_pos = 0
        self.setLayout(layout)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.connect(self,SIGNAL("customContextMenuRequested(QPoint)"),self.contextMenuRequested)
    def _on_change(self,state):
        if not self.suppress_update:
            self.SI_stateChanged.emit()
            #self.emit(QtCore.SIGNAL('stateChanged()'))
    def save(self,ds_parent):
        tags_store = data_store('tags',None,ds_parent)
        selected_tags = self.get_selected_tags()
        for tag in selected_tags:
            #only store checked tags
            tag = str(tag)
            data_store(tag,None,tags_store)
    def load(self,ds_parent):
        try:
            tag_ds = ds_parent.get_child('tags')
            for tag in tag_ds:
                tag_name = tag.get_name()
                if tag_name == "None":
                    tag_name = None
                if tag_name in list(self._check_boxes.keys()):
                    self._check_boxes[tag_name].setCheckState(QtCore.Qt.Checked)
        except:
            print("Warning: Loading a older saved configuration. Category/tag settings not loaded.")
    @QtCore.Slot(QtCore.QPoint)
    def contextMenuRequested(self, point):
        menu = QtWidgets.QMenu()
        # Select all menu item
        action_select = QtWidgets.QAction("Select All",menu)
        self.connect(action_select,SIGNAL("triggered()"), lambda: self.select_all(True))
        menu.addAction(action_select)
        # Select all menu item
        action_deselect = QtWidgets.QAction("De-select All",menu)
        self.connect(action_deselect,SIGNAL("triggered()"), lambda: self.select_all(False))
        menu.addAction(action_deselect)
        menu.exec_(self.mapToGlobal(point))
    def select_all(self, select):
        self.suppress_update = True
        for tag in list(self._check_boxes.values()):
            tag.setCheckState(QtCore.Qt.Checked if select else QtCore.Qt.Unchecked)
        self.suppress_update = False
        self.SI_stateChanged.emit()
        #self.emit(QtCore.SIGNAL('stateChanged()'))

class tab_view(QtWidgets.QWidget):
    '''describes the view of the registers and the tag selection and interaction beteen'''
    SI_resize_main_window = QtCore.Signal()
    SI_channel_data_ready = QtCore.Signal(object)
    SI_passive_observer_data = QtCore.Signal(object)
    SI_nameChanged = QtCore.Signal(QtCore.QObject)
    SI_request_read_channel_list = QtCore.Signal(object)
    SI_request_write_channel_list = QtCore.Signal(object)
    SI_tab_use_write_presets = QtCore.Signal(object)
    SI_tab_use_read_presets = QtCore.Signal(object)
    def __init__(self,channel_group_object,parent):
        QtWidgets.QWidget.__init__(self, parent)
        self._name = "Empty"
        self._name_locked = False
        self.channel_group_object = channel_group_object
        self.dig = display_item_group(self.channel_group_object)
        self.dig.SI_request_read_channel_list.connect(self.read_channel_list)
        self.dig.SI_request_write_channel_list.connect(self.write_channel_list)
        #self.connect(self.dig,SIGNAL('request_write_channel_list(PyQt_PyObject)'), self.write_channel_list)
        self.SI_resize_main_window.connect(self.dig.resize_main_window)
        #self.connect(self, SIGNAL('resize_main_window()'), self.dig, SLOT('resize_main_window()'))
        self.SI_channel_data_ready.connect(self.dig.receive_channel_data)
        #self.connect(self,SIGNAL('channel_data_ready(PyQt_PyObject)'), self.dig.receive_channel_data)
        self.SI_passive_observer_data.connect(self.dig.receive_passive_channel_data)
        #self.connect(self,SIGNAL('passive_observer_data(PyQt_PyObject)'), self.dig.receive_passive_channel_data)
        self.dcg = display_tag_group(channel_group_object)
        #self.connect(self.dcg, QtCore.SIGNAL("stateChanged()"), self._tags_changed)
        self.dcg.SI_stateChanged.connect(self._tags_changed)
        self.init_interface()
    @QtCore.Slot()
    def resize_main_window(self):
        self.SI_resize_main_window.emit()
        #self.emit(SIGNAL('resize_main_window()'))
    def init_interface(self):
        layout = QtWidgets.QVBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignLeft)
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidget(self.dig)
        self.scroll_area.setWidgetResizable(True)
        layout.addWidget(self.scroll_area,100) #add the display_item_group at the top
        layout.addWidget(self.dcg,0) #add the display_tag_group at the bottom
        self.setLayout(layout)
        self.show()
    def wheelEvent(self, QWheelEvent):
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        if modifiers == QtCore.Qt.NoModifier:
            #remap mouse wheel vertical scroll to horizontal scroll, since the only scroll bar is horizontal.
            scroll_bar = self.scroll_area.horizontalScrollBar()
            scroll_bar.triggerAction(scroll_bar.SliderSingleStepAdd if QWheelEvent.delta() < 0 else scroll_bar.SliderSingleStepSub)
        else:
            QWheelEvent.ignore()
    def update_from_dict(self,data_dict):
        self.dig.update_from_dict(data_dict)
    def get_name(self):
        return self._name
    def set_name(self,name,write_locked=False):
        if self._name_locked:
            if write_locked:
                self._name = name
                self._name_locked = True
                self.SI_nameChanged.emit(self)
                #self.emit(QtCore.SIGNAL('nameChanged(QWidget)'),self)
        else:
            self._name = name
            self.SI_nameChanged.emit(self)
            #self.emit(QtCore.SIGNAL('nameChanged(QWidget)'),self)
    def _tags_changed(self):
        selected_tags = self.dcg.get_selected_tags()
        selected_tags.sort(key=lambda s: str(s).upper())
        name = str(selected_tags)
        name = name.lstrip('[').rstrip(']').replace("'","")
        if not len(name):
            name = "Empty"
        self.set_name(name,write_locked=False)
        self.dig.inclusive_filter(selected_tags)
    def read_channel_list(self,channel_list):
        self.SI_request_read_channel_list.emit(channel_list)
        #self.emit(SIGNAL('request_read_channel_list(PyQt_PyObject)'),channel_list)
    def write_channel_list(self,channel_list):
        self.SI_request_write_channel_list.emit(channel_list)
        #self.emit(SIGNAL('request_write_channel_list(PyQt_PyObject)'),channel_list)
    def receive_channel_data(self,data_dict):
        self.SI_channel_data_ready.emit(data_dict)
        #self.emit(SIGNAL('channel_data_ready(PyQt_PyObject)'),data_dict)
    def receive_passive_channel_data(self,data_dict):
        self.SI_passive_observer_data.emit(data_dict)
        #self.emit(SIGNAL('passive_observer_data(PyQt_PyObject)'),data_dict)
    def wake(self):
        self.dig.wake()
    def save(self,ds_parent):
        tv = data_store('tab_view',None,ds_parent)
        tag_ds = data_store('tag',None,tv)
        self.dcg.save(tag_ds)
        dig_ds = data_store('dig',None,tv)
        self.dig.save(dig_ds)
    def load(self,ds_parent):
        tv = ds_parent.get_child('tab_view')
        tag_ds = tv.get_child('tag')
        self.dcg.load(tag_ds)
        dig_ds = tv.get_child('dig')
        self.dig.load(dig_ds)
    def tab_use_write_presets(self,bool):
        self.dig.use_write_presets(bool)
    def tab_use_read_presets(self,bool):
        self.dig.use_read_presets(bool)
    def tab_flash_on_change(self,bool):
        self.dig.flash_on_change(bool)
    def tab_change_font_size(self,increment):
        self.dig.change_font_size(increment)
    def cleanup_upon_disconnect(self):
        self.dig.cleanup_upon_disconnect()

class tab_group(QtWidgets.QTabWidget):
    '''a group of tab_views'''
    SI_passive_observer_data = QtCore.Signal(object)
    SI_channel_data_ready = QtCore.Signal(object)
    SI_tab_use_write_presets = QtCore.Signal(object)
    SI_tab_use_read_presets = QtCore.Signal(object)
    SI_request_read_channel_list = QtCore.Signal(object)
    SI_request_write_channel_list = QtCore.Signal(object)
    SI_tab_flash_on_change = QtCore.Signal(object)
    SI_tab_change_font_size = QtCore.Signal(object)
    SI_resize_main_window = QtCore.Signal()
    def __init__(self, channel_group, background_call=None):
        '''Create a group of tabs in the Qt5 GUI given a PyICe channel_group.
        background_call is an optional argument. If offered, it must be a function that takes
        a function of no arguments to be enqueued to run on another thread, such as
        the background_worker thread.'''
        assert isinstance(channel_group, lab_core.channel_group)
        assert callable(background_call) or (background_call is None)
        QtWidgets.QTabWidget.__init__(self)
        self.channel_group_object = channel_group
        self._active_tab = None
        self._previous_tab = None
        self.background_call = background_call
        self.init_interface()
    def init_interface(self):
        #add the 'add_tab' button on right
        btnAdd = QtWidgets.QToolButton()
        btnAdd.setMinimumWidth(3)
        btnAdd.setText("  +  ")
        btnAdd.setToolTip("New Tab")
        btnAdd.setEnabled(True)
        self.setCornerWidget(btnAdd, QtCore.Qt.TopRightCorner)
        #self.setTabShape(QTabWidge.)
        self.setUsesScrollButtons(True)
        self.connect(btnAdd, QtCore.SIGNAL('clicked()'), self.add_tab_view)
        self.connect(self, QtCore.SIGNAL('tabCloseRequested(int)'), self.remove_tab)
        self.connect(self, QtCore.SIGNAL('currentChanged(int)'), self.active_changed)
        self.connect(self, QtCore.SIGNAL('currentChanged(int)'), self.resize_main_window)
        self.add_tab_view()
    @QtCore.Slot()
    def resize_main_window(self):
        self.SI_resize_main_window.emit()
    def mouseDoubleClickEvent(self, event):
        self.add_tab_view()
    def add_tab_view(self):
        debug_logging.debug("add_tab_view")
        tv = tab_view(self.channel_group_object,self)
        self.connect_tv(tv)
        self.addTab(tv,'Empty')
        self.update_tab_rules()
        self.tab_view_name_change(tv)
        new_tab_index = self.count()-1
        self.setCurrentIndex( new_tab_index )
        self._previous_tab = self._active_tab
        self._active_tab = self.widget(self.currentIndex())
        debug_logging.debug("  new tab index {}".format(new_tab_index))
        return tv
    def connect_tv(self,tv_widget):
        tv_widget.SI_nameChanged.connect(self.tab_view_name_change)
        tv_widget.SI_request_read_channel_list.connect(self.read_channel_list)
        tv_widget.SI_request_write_channel_list.connect(self.write_channel_list)
        self.SI_passive_observer_data.connect(tv_widget.receive_passive_channel_data)
    def tab_view_name_change(self,tab_view_object):
        index = self.find_widget_in_tabs(tab_view_object)
        name = self.widget(index).get_name()
        self.setTabText(index,name)
    def find_widget_in_tabs(self,widget):
        #returns index
        for i in range(self.count()):
            if self.widget(i) == widget:
                return i
        else:
            return None
    def remove_tab(self,index):
        debug_logging.debug("tab_group.remove_tab")
        self.removeTab(index)
        self.update_tab_rules()
    def update_tab_rules(self):
        self.setTabsClosable(self.count() > 1)
        self.setMovable(self.count() > 1)
    def disconnect_tab(self,tab_view_widget):
        if tab_view_widget != None:
            new_tab_index = self.find_widget_in_tabs(tab_view_widget)
            if new_tab_index is None:
                dbgmsg = "tab_group.disconnect_tab id={}".format(id(tab_view_widget))
            else:
                dbgmsg = "tab_group.disconnect_tab #{}".format(new_tab_index)
            debug_logging.debug(dbgmsg)
            self.SI_channel_data_ready.disconnect(tab_view_widget.receive_channel_data )
            self.SI_tab_use_write_presets.disconnect(tab_view_widget.tab_use_write_presets )
            self.SI_tab_use_read_presets.disconnect(tab_view_widget.tab_use_read_presets )
            self.SI_tab_flash_on_change.disconnect( tab_view_widget.tab_flash_on_change )
            self.SI_tab_change_font_size.disconnect(tab_view_widget.tab_change_font_size)
            self.SI_resize_main_window.disconnect(tab_view_widget.resize_main_window)
    def connect_tab(self,tab_view_widget):
        if tab_view_widget != None:
            new_tab_index = self.find_widget_in_tabs(tab_view_widget)
            if new_tab_index is None:
                dbgmsg = "tab_group.connect_tab id={}".format(id(tab_view_widget))
            else:
                dbgmsg = "tab_group.connect_tab #{}".format(new_tab_index)
            debug_logging.debug(dbgmsg)
            self.SI_channel_data_ready.connect(tab_view_widget.receive_channel_data)
            self.SI_tab_use_write_presets.connect(tab_view_widget.tab_use_write_presets )
            self.SI_tab_use_read_presets.connect(tab_view_widget.tab_use_read_presets )
            self.SI_tab_flash_on_change.connect( tab_view_widget.tab_flash_on_change )
            self.SI_tab_change_font_size.connect( tab_view_widget.tab_change_font_size)
            self.SI_resize_main_window.connect(tab_view_widget.resize_main_window)
            tab_view_widget.wake()
    def active_changed(self,index):
        debug_logging.debug("tab_group.active_changed({}) started".format(index))
        old_tab = self._active_tab if self.count() > 0 else None
        new_tab = self.widget(index) if index >= 0 else None
        if old_tab is not None:
            old_tab.cleanup_upon_disconnect()

            class TabSwitchingAgent(object):
                def __init__(self, the_tab_group, old_tab, new_tab, retries=3):
                    self.tries_so_far = 0
                    self.the_tab_group = the_tab_group
                    self.old_tab = old_tab
                    self.new_tab = new_tab
                    self.retries = retries
                def try_to_disconnect_old_tab(self):
                    debug_logging.debug("TabSwitchingAgent: try_to_disconnect_old_tab()")
                    self.tries_so_far += 1
                    try:
                        self.the_tab_group.disconnect_tab(self.old_tab)
                    except RuntimeError as e:
                        debug_logging.info("  Temporarily unable to disconnect Qt signals"
                                           " from old tab, will retry...\n  {}".format(e))
                        if callable(self.the_tab_group.background_call) and self.tries_so_far < self.retries:
                            # Retry in the background worker thread. This gives a chance for any "in-flight"
                            # channel_data_ready Qt signals to reach their slots and retire, increasing the
                            # chance that our next attempt to disconnect will succeed.
                            self.the_tab_group.background_call(self.try_to_disconnect_old_tab)
                    else:
                        if self.tries_so_far > 1:
                            debug_logging.info("  ...retrying successfully disconnected old tab.")
                        else:
                            debug_logging.debug("  Disconnected old tab successfully")
                        self.the_tab_group.background_call(self.connect_new_tab)
                def connect_new_tab(self):
                    debug_logging.debug("TabSwitchingAgent: Connecting new tab")
                    self.the_tab_group.connect_tab(self.new_tab)

            tda = TabSwitchingAgent(self, old_tab, new_tab)
            tda.try_to_disconnect_old_tab()
        else:
            # Case of no previous tab to disconnect.
            debug_logging.debug("  tab_group.active_changed({}), no previous tab to disconnect".format(index, self.find_widget_in_tabs(self._previous_tab)))
            self.connect_tab(new_tab)
        self._active_tab = new_tab
        self._previous_tab = old_tab
    def read_channel_list(self,channel_list):
        self.SI_request_read_channel_list.emit(channel_list)
    def write_channel_list(self,channel_list):
        self.SI_request_write_channel_list.emit(channel_list)
    def receive_channel_data(self,data_dict):
        self.SI_channel_data_ready.emit(data_dict)
    def receive_passive_channel_data(self,queue):
        #better to try and crash than test and not crash
        data_dict = queue.get_nowait()
        self.SI_passive_observer_data.emit(data_dict)
    def save(self,ds_parent):
        tg = data_store('tab_group',None,ds_parent)
        for i in  range(self.count()):
            tab = self.widget(i)
            tab_ds = data_store('tab',None,tg)
            tab.save(tab_ds)
    def load(self,parent_ds):
        self.disconnect_tab(self._active_tab)
        self.clear()
        #are the tabs really gone??
        for i in range(self.count()):
            self.widget(i).close()  # let's close 'em all --FL 5/2/2019
        for tg_ds in parent_ds:
            if tg_ds.get_name() == 'tab_group':
                for tab in tg_ds:
                    #create a tab view from the store
                    tv = self.add_tab_view()
                    tv.load(tab)
    def tab_use_write_presets(self,bool):
        self.SI_tab_use_write_presets.emit(bool)
    def tab_use_read_presets(self,bool):
        self.SI_tab_use_read_presets.emit(bool)
    def tab_flash_on_change(self,bool):
        self.SI_tab_flash_on_change.emit(bool)
    def tab_change_font_size(self,increment):
        self.SI_tab_change_font_size.emit(increment)

class gui_logger(QtCore.QObject):
    SI_request_background_call = QtCore.Signal(object)
    SI_channel_data_ready = QtCore.Signal(object)
    def __init__(self,channel_group):
        QtCore.QObject.__init__(self)
        self._logger = None
        self.connect_dialog = None
        self._channel_group = channel_group
        self.logger_view = logger_view(channel_group,None)
        self.logger_view.hide()
        self.create_connect_dialog()
    def display_select_channels(self):
        self.logger_view.show()
    def log(self):
        if self._logger:
            self._logger.remove_all_channels_and_sub_groups()
            channel_names = self.logger_view.get_selected_channel_name_list()
            for channel_name in channel_names:
                self._logger.add( self._channel_group[channel_name] )
            #cannot directly use the logger here, send it to the back ground worker to actually read
            self.SI_request_background_call.emit(self._logger.log)
            #self.emit(SIGNAL('request_background_call(PyQt_PyObject)'),self._logger.log)
            debug_logging.info(("Logging selected channel data to SQLite database at "
                                "{}").format(datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')))
        else:
            raise Exception('Logger is not connected')
    def log_data(self, data_dict):
        print("logging....")
        if self._logger:
            self._logger.log_data(data_dict)
        else:
            raise Exception('Logger is not connected')
    def log_data_if_changed(self, data_dict):
        if self._logger:
            self._logger.log_data(data_dict, only_if_changed=True)
        else:
            raise Exception('Logger is not connected')
    def save(self,ds_parent):
        lv_ds = data_store('logger_view',None,ds_parent)
        self.logger_view.save(lv_ds)
        data_store('logger_dbase',self._get_dbase_filename(),ds_parent)
        data_store('logger_table',self._get_table_name(),ds_parent)
    def load(self,ds_parent):
        lv_ds = ds_parent.get_child('logger_view')
        if lv_ds:
            self.logger_view.load(lv_ds)
        self._set_dbase_filename( str(ds_parent['logger_dbase']))
        self._set_table_name( str(ds_parent['logger_table']))
    def display_connect(self):
        self.connect_dialog.show()
    def logger_disconnect(self):
        if self._logger:
            self._logger.stop()
            self._logger = None
            debug_logging.info("Database disconnected!")
        else:
            return
            #raise Exception('Logger is not connected')
    def _disp_save_dialog(self):
        fname, _ = QtWidgets.QFileDialog.getSaveFileName(None, 'Connect Database', '.',"SQLite Files (*.sqlite);;All files (*.*)", options = QtWidgets.QFileDialog.DontConfirmOverwrite)
        if fname:
            self.filename_box.setText(fname)
    def create_connect_dialog(self):
        self.connect_dialog = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        # database file name box
        dbase_file_group = QtWidgets.QWidget()
        dbase_file_group_layout = QtWidgets.QHBoxLayout()
        dbase_file_group.setLayout(dbase_file_group_layout)
        layout.addWidget( QtWidgets.QLabel("Database File:"))
        self.filename_box = QtWidgets.QLineEdit(  )
        self.filename_box.setFocus()
        dbase_file_group_layout.addWidget(self.filename_box)
        file_dialog_button = QtWidgets.QPushButton("...")
        self.connect(file_dialog_button,SIGNAL('clicked()'), self._disp_save_dialog )
        dbase_file_group_layout.addWidget(file_dialog_button)
        layout.addWidget(dbase_file_group)
        #table name
        layout.addWidget( QtWidgets.QLabel("Table Name:"))
        self.tablename_box = QtWidgets.QLineEdit(  )
        layout.addWidget(self.tablename_box)
        # write close
        buttons_widget = QtWidgets.QWidget()
        buttons_layout = QtWidgets.QHBoxLayout()
        replace_button = QtWidgets.QPushButton("Replace Table")
        self.connect(replace_button,SIGNAL("clicked()"),self._replace_table)
        buttons_layout.addWidget( replace_button )
        append_button = QtWidgets.QPushButton("Append Table")
        self.connect(append_button,SIGNAL("clicked()"),self._append_table)
        buttons_layout.addWidget(append_button)
        cancel_button = QtWidgets.QPushButton("Cancel")
        self.connect(cancel_button,SIGNAL("clicked()"), self.connect_dialog.close )
        buttons_layout.addWidget(cancel_button)
        buttons_widget.setLayout(buttons_layout)
        layout.addWidget(buttons_widget)
        self.connect_dialog.setLayout(layout)
        self.connect_dialog.hide()
    def _get_dbase_filename(self):
        return str(self.filename_box.text())
    def _get_table_name(self):
        return str(self.tablename_box.text())
    def _set_dbase_filename(self,name):
        self.filename_box.setText(name)
    def _set_table_name(self,name):
        self.tablename_box.setText(name)
    def _append_table(self):
        self._logger = lab_core.logger(self._channel_group,database=self._get_dbase_filename())
        self._logger.append_table(self._get_table_name())
        self._logger.set_journal_mode(journal_mode='WAL', synchronous='NORMAL', timeout_ms=10000)
        self.connect_dialog.close()
    def _replace_table(self):
        self._logger = lab_core.logger(self._channel_group,database=self._get_dbase_filename())
        self._logger.new_table(self._get_table_name(),replace_table=True)
        self._logger.set_journal_mode(journal_mode='WAL', synchronous='NORMAL', timeout_ms=10000)
        self.connect_dialog.close()

class logger_item(QtWidgets.QCheckBox,channel_wrapper):
    def __init__(self,channel_object):
        QtWidgets.QCheckBox.__init__(self)
        channel_wrapper.__init__(self,channel_object)
        self._displayed = False
        if self.get_description():
            self.setToolTip(self.get_description())
        self.update_display()
        self.setCheckState(QtCore.Qt.Checked)
    def update_display(self):
        self.setText( self.get_name() )
    def display(self,state):
        self._displayed = state
    def displayed(self):
        return self._displayed
    def selected(self):
        return self.checkState() == QtCore.Qt.Checked
    def save(self,ds_parent):
        li_ds = data_store('logger_item',self.get_name(),ds_parent)
        li_ds['selected'] = str( self.selected() )
    def load(self,ds_parent):
        li_ds = ds_parent.get_child('logger_item')
        if li_ds:
            assert li_ds.get_value() == self.get_name()
            if li_ds['selected'] == 'True':
                self.setCheckState(QtCore.Qt.Checked)
            elif li_ds['selected'] == 'False':
                self.setCheckState(QtCore.Qt.Unchecked)

class logger_item_group(QtWidgets.QWidget):
    def __init__(self,channel_group_object):
        QtWidgets.QWidget.__init__(self)
        self.logger_items = []
        self.init_interface()
        self.build_interface()
        self._channel_group = channel_group_object
        self.populate_from_channel_group(channel_group_object)
        self._expecting_data = False
    def populate_from_channel_group(self,channel_group_object):
        for channel in channel_group_object:
            li = logger_item(channel)
            self.add_logger_item(li)
    def add_logger_item(self,item):
        self.logger_items.append(item)
    def sort(self):
        self.logger_items.sort(key = lambda item: item.get_name().upper())
    def inclusive_filter(self,filter_list):
        #filter_list is a list of tag names to filter on
        for di in self.logger_items:
            if di.get_tag() in filter_list:
                di.display(True)
            else:
                di.display(False)
        self.build_interface()
    def init_interface(self):
        layout = QtWidgets.QVBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignTop)
        self.grid_container = QtWidgets.QWidget()
        self.grid_container_container = QtWidgets.QWidget()
        container_container_layout = QtWidgets.QHBoxLayout()
        container_container_layout.setAlignment(QtCore.Qt.AlignLeft)
        self.grid_container_container.setLayout(container_container_layout)
        container_container_layout.addWidget(self.grid_container)
        #container_container_layout.addStretch(80)
        layout.addWidget(self.grid_container_container)
        #layout.addStretch(80)
        self.setLayout(layout)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.connect(self,SIGNAL("customContextMenuRequested(QPoint)"),self.contextMenuRequested)
    def build_interface(self):
        self._grid = QtWidgets.QGridLayout()
        self._grid.setHorizontalSpacing(10)
        self._grid.setVerticalSpacing(5)
        self._grid.setAlignment(QtCore.Qt.AlignLeft)
        self.grid_container_container.layout().removeWidget(self.grid_container)
        self.grid_container = QtWidgets.QWidget()
        self.grid_container_container.layout().addWidget(self.grid_container)
        self.grid_container.setLayout(self._grid)
        for di in self.logger_items:
            di.setParent(None)
        y_pos = 0
        x_pos = 0
        column_height = 0
        self.columnWidths = []
        self.columnWidths.append(0)
        for di in self.logger_items:
            if di.displayed():
                if column_height > 0 and column_height + di.sizeHint().height() + self._grid.verticalSpacing() > self.parentWidget().size().height() - 60:
                    y_pos = 0
                    x_pos += 1
                    self.columnWidths.append(0)
                    column_height = 0
                self._grid.addWidget(di, y_pos, x_pos)
                di.column_placement = x_pos
                column_height += di.sizeHint().height() + self._grid.verticalSpacing()
                y_pos += 1
    def get_selected_channel_name_list(self):
        channel_name_list = []
        for li in self.logger_items:
            if li.selected():
                channel_name_list.append( li.get_name() )
        return channel_name_list
    def save(self,ds_parent):
        lig_ds = data_store('logger_group',None,ds_parent)
        for li in self.logger_items:
            li_ds = data_store('logger_item_container',li.get_name(),lig_ds)
            li.save(li_ds)
    def load(self,ds_parent):
        lig_ds = ds_parent.get_child('logger_group')
        for li_ds in lig_ds:
            li_name = li_ds.get_value()
            for li in  self.logger_items:
                if li.get_name() == li_name:
                    li.load(li_ds)
    @QtCore.Slot(QtCore.QPoint)
    def contextMenuRequested(self, point):
        menu = QtWidgets.QMenu()
        # Select all menu item
        action_select = QtWidgets.QAction("Select All",menu)
        self.connect(action_select,SIGNAL("triggered()"), lambda: self.select_all(True))
        menu.addAction(action_select)
        # Select all menu item
        action_deselect = QtWidgets.QAction("De-select All",menu)
        self.connect(action_deselect,SIGNAL("triggered()"), lambda: self.select_all(False))
        menu.addAction(action_deselect)
        menu.exec_(self.mapToGlobal(point))
    def select_all(self, select):
        for li in self.logger_items:
            if li.displayed():
                li.setCheckState(QtCore.Qt.Checked if select else QtCore.Qt.Unchecked)

class logger_view(QtWidgets.QWidget):
    '''describes the view of the registers and the tag selection and interaction beteen'''
    def __init__(self,channel_group_object,parent):
        QtWidgets.QWidget.__init__(self, parent)
        self.channel_group_object = channel_group_object
        self.lig = logger_item_group(self.channel_group_object)
        self.dcg = display_tag_group(channel_group_object)
        self.dcg.SI_stateChanged.connect(self._tags_changed)
        #self.connect(self.dcg, QtCore.SIGNAL("stateChanged()"), self._tags_changed)
        self.setWindowTitle('Select Logger Channels')
        self.init_interface()
    def init_interface(self):
        layout = QtWidgets.QVBoxLayout()
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidget(self.lig)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area,100)  #add the display_item_group at the top
        layout.addWidget(self.dcg,0)  #add the display_tag_group at the bottom
        self.setLayout(layout)
        self.resize(800,600)
        self.show()
    def _tags_changed(self):
        selected_tags = self.dcg.get_selected_tags()
        selected_tags.sort(key=lambda s: str(s).upper())
        self.lig.inclusive_filter(selected_tags)
    def get_selected_channel_name_list(self):
        return self.lig.get_selected_channel_name_list()
    def resizeEvent(self, event):
        self.lig.build_interface()
    def save(self,ds_parent):
        tv = data_store('logger_view',None,ds_parent)
        tag_ds = data_store('tag',None,tv)
        self.dcg.save(tag_ds)
        lig_ds = data_store('lig',None,tv)
        self.lig.save(lig_ds)
    def load(self,ds_parent):
        tv = ds_parent.get_child('logger_view')
        tag_ds = tv.get_child('tag')
        self.dcg.load(tag_ds)
        lig_ds = tv.get_child('lig')
        self.lig.load(lig_ds)

class background_worker(QtCore.QThread):
    SI_channel_data_ready = QtCore.Signal(object)
    SI_dump_data_ready = QtCore.Signal(object)
    #background worker thread, it is the only thing that read and writes registers
    def __init__(self,channel_group):
        QtCore.QThread.__init__(self)
        self._channel_group = channel_group
        self._calls = []
        self.queue = queue.Queue(5)
        self.log = open('gui_cmd_history.log', 'a', buffering=1)
        self.log.write("\n\n###############################\n")
        self.log.write("# {} #\n".format(datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')))
        self.log.write("###############################\n\n")
        self.running = True
        self.run_loop_has_quit = False
    def read_channel_list(self,read_list):
        # FIXME FL: Removed the re-enqueue preventer during GUI slowdown and memory-leak debug 5/6/2019
        # do not re-enqueue multiple requests to read the same channels
        # for item in list(self.queue.queue):  # FL note: Woah! This isn't part of the Queue.Queue API.
        #     if item[0] == 'read' and set(item[1]) == set(read_list):
        #         return
        # FIXME FL: self.log.write("master.read_channel_list({})\n".format(read_list))
        self.log.write("master.read_channels({})\n".format(read_list))
        self.queue.put ( ('read',read_list) )
    def write_channel_list(self,write_list):
        for e in write_list:
            self.log.write("master.write('{}', {})\n".format(*e))
        self.queue.put ( ('write',write_list) )
    def dump_channel_list(self,dump_list):
        self.queue.put ( ('dump',dump_list) )
    def background_call(self,call):
        self.queue.put ( ('call',call) )
    def stop(self):
        self.queue.put ( ('stop',None) )
        self.log.close()
        self.running = False
    def run(self):
        try:
            while self.running:
                try:
                    #write is first so if a read follows a write the new value will be set
                    (data_type,data) = self.queue.get()
                    if data_type == 'write' :
                        self._write_channel_list(data)
                    elif data_type == 'dump':
                        self._read_dump_list(data)
                    elif data_type == 'read':
                        self._read_channel_list(data)
                    elif data_type == 'call':
                        data()
                    elif data_type == "stop":
                        break
                    else:
                        debug_logging.warning('background worker received command it does not recognize: ({}, {})'.format(repr(data_type), repr(data)))
                except Exception as e:
                    debug_logging.warning("**** lab_gui.background_worker.run() caught exception {} but keeps running".format(e))
                    debug_logging.warning(traceback.format_exc())
        except Exception as e:
            debug_logging.warning("**** lab_gui.background_worker.run() caught exception {} and exits".format(e))
            debug_logging.warning(traceback.format_exc())
        finally:
            self.run_loop_has_quit = True

    def _read_channel_list_core(self,read_list):
        #list is a list of channel_names to read
        # build a list of actual channels from names
        channels = []
        for name in read_list:
            if self._channel_group[name].is_readable():
                channels.append(self._channel_group[name])
        output = {}
        try:
            results = self._channel_group.read_channel_list(channels)
        except Exception as e:
            print("background error")
            print(e)
            print(traceback.format_exc())
            # print "attempting to read individually"
            results = {}
            for channel in channels:
                results[channel.get_name()] = lab_core.ChannelReadException('READ_ERROR')
        return results
    def _read_channel_list(self,read_list):
        "Called in background_worker thread to do the actual instrument/HW/DUT reading"
        results = self._read_channel_list_core(read_list)
        self.SI_channel_data_ready.emit(results)
        #self.emit(SIGNAL('channel_data_ready(PyQt_PyObject)'),results)
    def _read_dump_list(self, dump_list):
        results = self._read_channel_list_core(dump_list)
        self.SI_dump_data_ready.emit(results)
        #self.emit(SIGNAL('dump_data_ready(PyQt_PyObject)'),results)
    def _write_channel_list(self,write_list):
        e = None
        #list is a list of tuples of channel_name and value to write
        for (channel_name,value) in write_list:
            debug_logging.info("Write {} to {}".format(channel_name,value))
            try:
                self._channel_group[channel_name].write_unformatted(value)
            except Exception as e:
                debug_logging.warning("lab_gui.background_worker._write_channel_list() caught exception {}".format(e))
                debug_logging.warning("while writing channel '{}' to {} from write_list {}".format(channel_name, repr(value), repr(write_list)))
                debug_logging.warning(traceback.format_exc())
                raise e
    def close(self, timeout=0.8):
        self.queue.put( ('call',self.stop))
        tzero = time.time()
        while self.running and time.time() - tzero < timeout:
            time.sleep(0.1)
            if self.run_loop_has_quit:
                return
        debug_logging.info("\nlab_gui.background_worker.close() timed out waiting for \n"
                           "PyICe GUI's background worker thread to quit.\n")

class ltc_lab_gui_main_window(QtWidgets.QMainWindow):
    SI_request_background_call = QtCore.Signal(object)
    SI_request_read_channel_list = QtCore.Signal(object)
    SI_request_dump_channel_list = QtCore.Signal(object)
    SI_request_write_channel_list = QtCore.Signal(object)
    SI_channel_data_ready = QtCore.Signal(object)
    SI_passive_observer_data = QtCore.Signal(object)
    SI_close_main = QtCore.Signal()
    SI_resize_main_window = QtCore.Signal()
    SI_tab_use_write_presets = QtCore.Signal(bool)
    SI_tab_user_read_presets = QtCore.Signal(bool)
    SI_tab_flash_on_change = QtCore.Signal(bool)
    SI_change_font_size = QtCore.Signal(int)
    def __init__(self,channel_group, background_call=None):
        '''Create the GUI's main window given a PyICe channel_group.
        background_call is an optional argument. If offered, it must be a function that takes
        a function of no arguments to be enqueued to run on another thread, such as
        the background_worker thread.'''
        assert isinstance(channel_group, lab_core.channel_group)
        assert callable(background_call) or (background_call is None)
        QtWidgets.QMainWindow.__init__(self)
        self._tg = tab_group(channel_group, background_call=background_call)
        self._channel_group = channel_group
        self.logger = None
        self._gui_logger = gui_logger(channel_group)
        self.SI_tab_use_write_presets.connect(self._tg.tab_use_write_presets )
        self.SI_tab_user_read_presets.connect(self._tg.tab_use_read_presets )
        self.SI_tab_flash_on_change.connect(self._tg.tab_flash_on_change )
        self.SI_change_font_size.connect(self._tg.tab_change_font_size )

        self._overflow_alpha = 0
        # self._busy_alpha = 0
        self.palette = QtGui.QPalette()
        self.setAutoFillBackground(True)
        self.setPalette(self.palette)

        self.overflow_highlight = QtCore.QPropertyAnimation(self,QtCore.QByteArray("overflow_alpha".encode("utf-8")))
        self.overflow_highlight.setDuration(3500) #msecs
        self.overflow_highlight.setStartValue(255)
        self.overflow_highlight.setEasingCurve(QtCore.QEasingCurve.OutCirc)
        self.overflow_highlight.setEndValue(0)

        # self.busy_highlight = QtCore.QPropertyAnimation(self,"busy_alpha")
        # self.busy_highlight.setDuration(3500) #msecs
        # self.busy_highlight.setStartValue(0)
        # self.busy_highlight.setEasingCurve(QtCore.QEasingCurve.InCirc)
        # self.busy_highlight.setEndValue(255)

        self.init_interface()
        self._data = {} #dictionary of most recent data for dump
    def init_interface(self):
        self.setCentralWidget(self._tg)
        self.menu_bar = self.create_menu_bar()
        self.move(300, 150)
        self.resize(800,600)
        self.activateWindow()
        self.raise_()
    def _get_overflow_alpha(self):
        return self._overflow_alpha
    def _set_overflow_alpha(self, value):
        self._overflow_alpha = value
        color = QtGui.QColor(255,230,230,a=self._overflow_alpha)
        self.palette.setColor(self.backgroundRole(), color)
        self.setPalette(self.palette)
    overflow_alpha = QtCore.Property(int, _get_overflow_alpha, _set_overflow_alpha)
    # def _get_busy_alpha(self):
    #     return self._busy_alpha
    # def _set_busy_alpha(self, value):
    #     self._busy_alpha = value
    #     color = QtGui.QColor(230,230,255,a=self._busy_alpha)
    #     self.palette.setColor(self.backgroundRole(), color)
    #     self.setPalette(self.palette)
    # busy_alpha = QtCore.Property(int, _get_busy_alpha, _set_busy_alpha)
    def _queue_overflow_highlight(self):
        self.overflow_highlight.stop()
        self.overflow_highlight.start(QtCore.QPropertyAnimation.KeepWhenStopped)
    def showEvent(self, event):
        self.SI_resize_main_window.emit()
    def resizeEvent(self, event):
        self.SI_resize_main_window.emit()
    def mouseReleaseEvent(self, event):
        pass
    def create_menu_bar(self):
        menu_bar = self.menuBar()
        # file
        file_menu = QtWidgets.QMenu("File",menu_bar)
        menu_bar.addMenu(file_menu)
        file_open = QtWidgets.QAction("Open...",file_menu)
        file_open.setShortcut(QtGui.QKeySequence(QtCore.Qt.CTRL + QtCore.Qt.Key_O))
        file_menu.addAction(file_open)
        file_open.triggered.connect(self._disp_open_dialog)
        file_save_as = QtWidgets.QAction("Save As...",file_menu)
        file_save_as.setShortcut(QtGui.QKeySequence(QtCore.Qt.CTRL + QtCore.Qt.SHIFT + QtCore.Qt.Key_S))
        file_menu.addAction(file_save_as)
        file_save_as.triggered.connect(self._disp_save_dialog)
        file_save_default = QtWidgets.QAction("Save Default",file_menu)
        file_save_default.setShortcut(QtGui.QKeySequence(QtCore.Qt.CTRL + QtCore.Qt.Key_S))
        file_save_default.triggered.connect(lambda: self.save_file('default.guicfg'))
        file_menu.addAction(file_save_default)
        file_menu.addSeparator()
        file_old_dump = QtWidgets.QAction("Dump Cached Data...",file_menu)
        file_old_dump.triggered.connect(self._disp_dump_old_dialog)
        file_menu.addAction(file_old_dump)
        file_new_dump = QtWidgets.QAction("Dump New Data...",file_menu)
        file_new_dump.triggered.connect(self._disp_dump_new_dialog)
        file_menu.addAction(file_new_dump)
        file_menu.addSeparator()
        self.file_passive = QtWidgets.QAction("Passive Observer",file_menu,checkable=True)
        file_menu.addAction(self.file_passive)
        self.file_passive.toggled.connect(self.set_passive_observer_mode) #Bool
        self.file_close = QtWidgets.QAction("Close",file_menu)
        self.file_close.setShortcut(QtGui.QKeySequence(QtCore.Qt.CTRL + QtCore.Qt.Key_Q))
        self.file_close.triggered.connect(self.close)
        file_menu.addAction(self.file_close)

        #tab menu
        tab_menu = QtWidgets.QMenu("Tab",menu_bar)
        menu_bar.addMenu(tab_menu)
        tab_use_write_presets = QtWidgets.QAction("Use Write Presets",tab_menu)
        tab_use_write_presets.triggered.connect(lambda: self.SI_tab_use_write_presets.emit(True))
        tab_menu.addAction(tab_use_write_presets)
        tab_no_write_presets = QtWidgets.QAction("Don't Use Write Presets",tab_menu)
        tab_no_write_presets.triggered.connect(lambda: self.SI_tab_use_write_presets.emit(False))
        tab_menu.addAction(tab_no_write_presets)
        tab_menu.addSeparator()
        tab_use_read_presets = QtWidgets.QAction("Use Read Presets",tab_menu)
        tab_use_read_presets.triggered.connect(lambda: self.SI_tab_user_read_presets.emit(True))
        tab_menu.addAction(tab_use_read_presets)
        tab_no_read_presets = QtWidgets.QAction("Don't Use Read Presets",tab_menu)
        tab_no_read_presets.triggered.connect(lambda: self.SI_tab_user_read_presets.emit(False))
        tab_menu.addAction(tab_no_read_presets)
        tab_menu.addSeparator()
        tab_flash_on_change = QtWidgets.QAction("Flash on Change",tab_menu)
        tab_flash_on_change.triggered.connect(lambda: self.SI_tab_flash_on_change.emit(True))
        tab_menu.addAction(tab_flash_on_change)
        tab_no_flash_on_change = QtWidgets.QAction("Don't Flash on Change",tab_menu)
        tab_no_flash_on_change.triggered.connect(lambda: self.SI_tab_flash_on_change.emit(False))
        tab_menu.addAction(tab_no_flash_on_change)
        tab_menu.addSeparator()
        increase_font_size = QtWidgets.QAction("Increase Font Size",tab_menu)
        increase_font_size.setShortcut(QtGui.QKeySequence(QtCore.Qt.CTRL + QtCore.Qt.Key_Plus))
        increase_font_size.triggered.connect(lambda: self.SI_change_font_size.emit(1))
        tab_menu.addAction(increase_font_size)
        decrease_font_size = QtWidgets.QAction("Decrease Font Size",tab_menu)
        decrease_font_size.setShortcut(QtGui.QKeySequence(QtCore.Qt.CTRL + QtCore.Qt.Key_Minus))
        decrease_font_size.triggered.connect(lambda: self.SI_change_font_size.emit(-1))
        tab_menu.addAction(decrease_font_size)
        tab_menu.addSeparator()
        read_all = QtWidgets.QAction("Read All",tab_menu)
        read_all.setShortcut(QtGui.QKeySequence(QtCore.Qt.CTRL + QtCore.Qt.Key_R))
        read_all.triggered.connect(self._tg._active_tab.dig.request_read_all)
        tab_menu.addAction(read_all)

        #logger menu
        logger_menu = QtWidgets.QMenu("Logger",menu_bar)
        menu_bar.addMenu(logger_menu)
        logger_connect = QtWidgets.QAction("Connect Database ...",logger_menu)
        logger_connect.triggered.connect(self._gui_logger.display_connect)
        logger_menu.addAction(logger_connect)
        logger_disconnect = QtWidgets.QAction("Disconnect Database",logger_menu)
        logger_disconnect.triggered.connect(self.logger_disconnect)
        logger_menu.addAction(logger_disconnect)
        logger_menu.addSeparator()
        logger_select_channels = QtWidgets.QAction("Select Channels...",logger_menu)
        logger_select_channels.triggered.connect(self._gui_logger.display_select_channels)
        logger_menu.addAction(logger_select_channels)
        logger_log = QtWidgets.QAction("Log Once",logger_menu)
        logger_log.setShortcut(QtGui.QKeySequence(QtCore.Qt.CTRL + QtCore.Qt.Key_L))
        logger_log.triggered.connect(self._gui_logger.log)
        logger_menu.addAction(logger_log)
        logger_menu.addSeparator()
        self.logger_background_log = QtWidgets.QAction("Enable Background Logging",logger_menu,checkable=True)
        self.logger_background_log.toggled.connect(self.enable_background_logging)
        logger_menu.addAction(self.logger_background_log)
        self.logger_change = QtWidgets.QAction("Enable Logging on Change",logger_menu,checkable=True)
        self.logger_change.toggled.connect(self.enable_change_logging)
        logger_menu.addAction(self.logger_change)
        return menu_bar
    def enable_background_logging(self, enable_log):
        if not self._gui_logger._logger:
            self.logger_background_log.setChecked(False)
            raise Exception('Logger is not connected')
        elif enable_log:
            debug_logging.info("Background Logging Enabled!")
            self.enable_change_logging(False) # mutually exclusive crappy radio button
            self.SI_channel_data_ready.connect(self._gui_logger.log_data)
        else:
            try:
                self.SI_channel_data_ready.disconnect(self._gui_logger.log_data)
                debug_logging.info("Background Logging Disabled!")
            except RuntimeError:
                pass # I thought it wasn't connected.
        self.logger_background_log.setChecked(enable_log)
    def enable_change_logging(self, enable_log):
        if not self._gui_logger._logger:
            self.logger_change.setChecked(False)
            raise Exception('Logger is not connected')
        elif enable_log:
            debug_logging.info("Change Logging Enabled!")
            self.enable_background_logging(False) # mutually exclusive crappy radio button
            self.SI_channel_data_ready.connect(self._gui_logger.log_data_if_changed)
        else:
            try:
                self.SI_channel_data_ready.disconnect(self._gui_logger.log_data_if_changed)
                debug_logging.info("Change Logging Disabled!")
            except RuntimeError:
                pass # I thought it wasn't connected.
        self.logger_change.setChecked(enable_log)
    def logger_disconnect(self):
        try:
            self.enable_background_logging(False)
            self.enable_change_logging(False)
        except Exception as e:
            pass # on exit, logger may not be connected
        self._gui_logger.logger_disconnect()
    def read_channel_list(self,channel_list):
        self.SI_request_read_channel_list.emit(channel_list)
        # self.busy_highlight.start(QtCore.QPropertyAnimation.KeepWhenStopped)
    def write_channel_list(self,channel_list):
        self.SI_request_write_channel_list.emit(channel_list)
    def receive_dump_data(self,data_dict):
        self._data = data_dict
        self.dump(self._dump_file_name)
    def receive_channel_data(self,data_dict):
        # debug_logging.debug("main_window got channel_data_ready:\n  {}".format(", ".join(data_dict.keys())))
        self._data.update(data_dict)
        self.SI_channel_data_ready.emit(data_dict)
        # self.busy_highlight.stop()
        # self.busy_alpha = 0
    def receive_background_call_request(self,call):
        self.SI_request_background_call.emit(call)
    def receive_passive_channel_data(self,queue):
        self.SI_passive_observer_data.emit(queue)
    def _disp_save_dialog(self):
        fname, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Save file', '.',"Gui Configuration files (*.guicfg);;All files (*.*);;XML files (*.xml)")
        if fname:
            self.save_file(fname)
    def _disp_open_dialog(self):
        fname, ftype = QtWidgets.QFileDialog.getOpenFileName(self, 'Open file', '.',"Gui Configuration files (*.guicfg);;All files (*.*);;XML files (*.xml)")
        if len(fname) > 0:
            debug_logging.info("Loading GUI configuration from {}".format(fname))
            self.load_file(fname)
        else:
            debug_logging.info("No GUI configuration file specified for loading.")
    def _disp_dump_old_dialog(self):
        fname, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Save Dump file', '.',"Text Files (*.txt);;All files (*.*)")
        if fname:
            self.dump(fname)
    def _disp_dump_new_dialog(self):
        fname, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Save Dump file', '.',"Text Files (*.txt);;All files (*.*)")
        if fname:
            self._dump_file_name = fname
            channel_name_list = [channel.get_name() for channel in self._channel_group]
            self.SI_request_dump_channel_list.emit(channel_name_list)
            #self.emit(SIGNAL('request_dump_channel_list(PyQt_PyObject)'),channel_name_list)
    def dump(self,file_name):
        with open(file_name,'w') as f:
            for name,value in sorted(list(self._data.items()), key=lambda item: item[0]):
                f.write('{}: {}\n'.format(name,value))
            f.close()
    def load_file(self,file_name):
        ds = data_store()
        ds.load(file_name)
        self.load(ds)
    def save_file(self,file_name):
        ds = data_store('lab_gui')
        self.save(ds)
        ds.save(file_name)
    def load(self,parent_ds):
        for ds in parent_ds:
            if ds.get_name() == 'tab_group':
                self._tg.load(ds)
            if ds.get_name() == 'logger_container':
                self._gui_logger.load(ds)
            if ds.get_name() == 'main_window':
                ds_size = ds.get_child('size')
                if ds_size:
                    self.resize( int(ds_size['x']), int(ds_size['y']) )
    def show_passive_error(self,channel_list):
        #print 'Error: In passive mode, reading and writing not allowed'
        raise Exception('In passive mode, reading and writing not allowed')
    def save(self,parent_ds):
        tgc_ds = data_store('tab_group',None,parent_ds)
        self._tg.save(tgc_ds)
        lc = data_store('logger_container',None,parent_ds)
        self._gui_logger.save(lc)
        mw = data_store('main_window',None,parent_ds)
        size = data_store('size',None,mw)
        size['x'] = str(self.size().width())
        size['y'] = str(self.size().height())
    def set_passive_observer_mode(self, passive):
        if not passive:
            self.file_passive.setChecked(False)
            try:
                self._tg.SI_request_read_channel_list.disconnect(self.show_passive_error)
                self._tg.SI_request_write_channel_list.disconnect(self.show_passive_error)
                self._gui_logger.SI_request_background_call.disconnect(self.show_passive_error)
                self.SI_passive_observer_data.disconnect(self._tg.receive_passive_channel_data)
            except:
                pass

            self._tg.SI_request_read_channel_list.connect(self.read_channel_list)
            self._tg.SI_request_write_channel_list.connect(self.write_channel_list)
            self.SI_channel_data_ready.connect(self._tg.receive_channel_data)
            self._gui_logger.SI_request_background_call.connect(self.receive_background_call_request)
            self.setWindowTitle(self._channel_group.get_name())
        elif passive:
            self.disconnect(self.file_passive,SIGNAL("toggled(bool)"),self.set_passive_observer_mode)
            self.file_passive.setChecked(True)
            try:
                self._tg.SI_request_read_channel_list.disconnect(self.read_channel_list )
                self._tg.SI_request_write_channel_list.disconnect(self.write_channel_list )
                self.SI_channel_data_ready.disconnect(self._tg.receive_channel_data )
                self.SI_request_background_call.disconnect(self.receive_background_call_request)
            except:
                pass
            self.connect(self.file_passive,SIGNAL("toggled(bool)"),self.set_passive_observer_mode)
            self._tg.SI_request_read_channel_list.connect( self.show_passive_error )
            self._tg.SI_request_write_channel_list.connect(self.show_passive_error )
            self._gui_logger.SI_request_background_call.connect(self.show_passive_error )
            self.SI_passive_observer_data.connect(self._tg.receive_passive_channel_data)
            self.setWindowTitle('{} - PASSIVE OBSERVER MODE'.format(self._channel_group.get_name()))
        self.SI_resize_main_window.connect(self._tg.resize_main_window)
    def close(self):
        QtWidgets.QMainWindow.close(self)
    def closeEvent(self, event):
        self.logger_disconnect()
        self.SI_close_main.emit()

QApp = QtWidgets.QApplication(sys.argv)   # QApplication is a singleton per Qt docs

# class ltc_lab_gui_app(QtWidgets.QApplication):
class ltc_lab_gui_app(QObject):
    SI_queue_overflow = Signal()
    SI_passive_observer_data = Signal(object)
    def __init__(self,channel_group,passive=False,cfg_file='default.guicfg'):
        super().__init__()
        # Setup background_worker thread that does all channel I/O.
        self.worker = background_worker(channel_group)
        self.worker.start()
        #need to clone in case there are remote objects; they wont play nice with qt threads
        self._channel_group = channel_group.clone(name="GUI flat channel group")
        self.main_window = ltc_lab_gui_main_window(channel_group, background_call=self.worker.background_call)
        # icon path is relative to calling script, so we need to find an absolute path back to PyICe
        icon_path = os.path.join(os.path.dirname(__file__), "tssop.ico")
        self.main_window.setWindowIcon(QtGui.QIcon(icon_path))

        # open the default configuration if it exists
        try:
            self.main_window.load_file(cfg_file)
        except IOError:
            pass
        self.main_window.cb = QApp.clipboard()
        self.worker.SI_channel_data_ready.connect(self.main_window.receive_channel_data)
        self.worker.SI_dump_data_ready.connect(self.main_window.receive_dump_data)
        self.SI_queue_overflow.connect(self.main_window._queue_overflow_highlight)
        self.main_window.SI_request_background_call.connect(self.worker.background_call)
        self.main_window.SI_request_read_channel_list.connect( self.worker.read_channel_list)
        self.main_window.SI_request_dump_channel_list.connect(self.worker.dump_channel_list)
        self.main_window.SI_request_write_channel_list.connect(self.worker.write_channel_list)
        self.main_window.SI_close_main.connect(QApp.exit)
        if passive:
            self.SI_passive_observer_data.connect(self.main_window.receive_passive_channel_data)
            self.main_window.set_passive_observer_mode(True)
        else:
            self.main_window.set_passive_observer_mode(False)
            self.main_window.SI_close_main.connect(self.worker.close)
        self.passive_queue = queue.Queue(5)
        self.main_window.show()
    # def __del__(self):
    #     self.worker.close()
    #     self.worker.wait()
    def passive_data(self,data_dict):
        try:
            self.passive_queue.put_nowait(data_dict)
            self.SI_passive_observer_data.emit(self.passive_queue)
            self.q_is_full = False
        except queue.Full:
            if not self.q_is_full:
                self.q_is_full = True
                #print "Warning: Background GUI unable to keep up with main thread's data rate @ {}".format(datetime.datetime.now())
            self.SI_queue_overflow().emit()
            #self.emit(SIGNAL('queue_overflow()'))
    def exec_(self):
        return QApp.exec_()


if __name__ == '__main__':
    from . import lab_instruments
    from . import lab_core
    from . import twi_instrument
    master = lab_core.master("Demonstration GUI")
    master.add_channel_delta_timer('time_d')
    timer = lab_instruments.timer()
    timer.add_channel_total_seconds('seconds')
    timer.add_channel_total_minutes('minutes')
    master.add(timer)
    import cProfile
    PROFILING = True
    if PROFILING:
        profiler = cProfile.Profile()
        profiler.enable()
    master.gui()
    if PROFILING:
        profiler.disable()
        profiler.dump_stats("lab_gui.profile")
        print("GUI performance logged in lab_gui.profile.")
