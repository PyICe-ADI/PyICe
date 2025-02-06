from ..lab_core import *
import atexit
from functools import wraps
import pyvisa.errors

class scpi_smu(scpi_instrument):
    ''''''
    #todo abstract methods?
class keithley_2400(scpi_smu):
    ''''''
    # todo NPLC config?
    # todo trigger source, pulse, sweep? Other instrument driver?
    # todo atexit cleanup?
    # todo V/I init to zero?, source off?
    
    def __init__(self,interface_visa):
        '''interface_visa'''
        self._base_name = 'Keithley 2400'
        super(scpi_smu, self).__init__(f"Keithley 2400 @ {interface_visa}")
        self.add_interface_visa(interface_visa)
        self._configured_channels = {}
        self._output_off(channel_number=1)
        self.get_interface().write(':SOURce1:VOLTage:PROTection:LEVel 20') ##todo Dave fix
        atexit.register(self._output_off, channel_number=1) #TODO debug
    def _output_off(self, channel_number):
        self.get_interface().write(f':SOURce{channel_number}:CLEar:IMMediate')
    def _init_channel(self, channel_number):
        if channel_number in self._configured_channels:
            assert 'v_force' in self._configured_channels[channel_number]
            assert 'i_force' in self._configured_channels[channel_number]
            assert 'v_sense' in self._configured_channels[channel_number]
            assert 'i_sense' in self._configured_channels[channel_number]
            assert 'v_compl' in self._configured_channels[channel_number]
            assert 'i_compl' in self._configured_channels[channel_number]
        else:
            self._configured_channels[channel_number] = {'v_force': None,
                                                         'i_force': None,
                                                         'v_sense': None,
                                                         'i_sense': None,
                                                         'v_compl': None,
                                                         'i_compl': None,
                                                        }
    def _fix_exclusive(self, ch, value):
        '''fix write cache of exclusive channel pair sibling'''
        if ch.get_attribute('channel_type') == 'vforce':
            pair_ch = self._configured_channels[ch.get_attribute('channel_number')]['i_force']
            if  pair_ch is not None:
                pair_ch._set_value(None)
        elif ch.get_attribute('channel_type') == 'iforce':
            pair_ch = self._configured_channels[ch.get_attribute('channel_number')]['v_force']
            if  pair_ch is not None:
                pair_ch._set_value(None)
        else:
            raise Exception('How did I get here?')
    def _parse_float(self, val):
        f = float(val)
        if f == 9.91E37: #Keithley NaN
            f = float('nan')
        return f
    def _vforce(self, channel_number, value):
        if value is not None:
            self.get_interface().write(f':SOURce{channel_number}:VOLTage:LEVel:IMMediate:AMPLitude {value}')
            self.get_interface().write(f':SOURce{channel_number}:FUNCtion:MODE VOLTage')
            self.get_interface().write(f':OUTPut{channel_number}:STATe ON')
        else:
            pair_ch = self._configured_channels[channel_number]['i_force']
            if pair_ch is not None and pair_ch.read() is None:
                self._output_off(channel_number=channel_number)
    def _iforce(self, channel_number, value):
        if value is not None:
            self.get_interface().write(f':SOURce{channel_number}:CURRent:LEVel:IMMediate:AMPLitude {value}')
            self.get_interface().write(f':SOURce{channel_number}:FUNCtion:MODE CURRent')
            self.get_interface().write(f':OUTPut{channel_number}:STATe ON')
        else:
            pair_ch = self._configured_channels[channel_number]['v_force']
            if pair_ch is not None and pair_ch.read() is None:
                self._output_off(channel_number=channel_number)
    def _vsense(self, channel_number):
        # what about channel number parsing?!?!?!?
        # :FORMat:ELEMents [SENSe[1]] <item list> Specify data elements for data string
        # Parameters <item list> = VOLTageIncludes voltage reading
        # CURRentIncludes current reading
        # RESistance Includes resistance reading
        # TIMEIncludes timestamp
        # STATusIncludes status information
        #todo better message parsing
        #todo explicitly set format of response included elements
        (voltage, current, resistance, timestamp, status) = self.get_interface().ask(f':MEASure:VOLTage:DC?').split(',')
        return self._parse_float(voltage)
    def _isense(self, channel_number):
        # what about channel number parsing?!?!?!?
        (voltage, current, resistance, timestamp, status) = self.get_interface().ask(f':MEASure:CURRent:DC?').split(',')
        return self._parse_float(current)
    def _vcompl(self, channel_number, value):
        self.get_interface().write(f':SENSe{channel_number}:VOLTage:DC:PROTection:LEVel {value}')
    def _icompl(self, channel_number, value):
        self.get_interface().write(f':SENSe{channel_number}:CURRent:DC:PROTection:LEVel {value}')
    def add_channel_voltage_force(self, channel_name, channel_number=1):
        '''voltage force. Mutually exclusive at any moment with current force.'''
        self._init_channel(channel_number)
        new_channel = channel(channel_name,write_function=lambda v, channel_number=channel_number: self._vforce(channel_number, v))
        self._configured_channels[channel_number]['v_force'] = new_channel
        self.get_interface().write(f':SOURce{channel_number}:VOLTage:RANGe:AUTO ON')
        self.get_interface().write(f':SOURce{channel_number}:VOLTage:MODE FIXed')
        self.get_interface().write(f':SOURce{channel_number}:CLEar:AUTO OFF')
        # self.get_interface().write(f':SOURce{channel_number}:FUNCtion:SHAPe DC') #2430 only
        new_channel.set_attribute('channel_number', channel_number)
        new_channel.set_attribute('channel_type', 'vforce')
        new_channel.add_write_callback(self._fix_exclusive)
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_voltage_force.__doc__)
        # new_channel.set_display_format_function(function = lambda float_data: lab_utils.eng_string(float_data, fmt=fmt,si=True) + 'V')
        return self._add_channel(new_channel)
    def add_channel_current_force(self, channel_name, channel_number=1):
        '''current force. Mutually exclusive at any moment with voltage force.'''
        self._init_channel(channel_number)
        new_channel = channel(channel_name,write_function=lambda i, channel_number=channel_number: self._iforce(channel_number, i))
        self._configured_channels[channel_number]['i_force'] = new_channel
        self.get_interface().write(f':SOURce{channel_number}:CURRent:RANGe:AUTO ON')
        self.get_interface().write(f':SOURce{channel_number}:CURRent:MODE FIXed')
        self.get_interface().write(f':SOURce{channel_number}:CLEar:AUTO OFF')
        # self.get_interface().write(f':SOURce{channel_number}:FUNCtion:SHAPe DC') #2430 only
        new_channel.set_attribute('channel_number', channel_number)
        new_channel.set_attribute('channel_type', 'iforce')
        new_channel.add_write_callback(self._fix_exclusive)
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_current_force.__doc__)
        # new_channel.set_display_format_function(function = lambda float_data: lab_utils.eng_string(float_data, fmt=fmt,si=True) + 'A')
        return self._add_channel(new_channel)
    def add_channel_voltage_sense(self, channel_name, channel_number=1):
        '''voltage readback'''
        #range, nplc?
        # [:SENSe[1]]:VOLTage[:DC]:NPLCycles <n> Set speed (PLC)
        self._init_channel(channel_number)
        new_channel = channel(channel_name,read_function=lambda channel_number=channel_number: self._vsense(channel_number))
        self._configured_channels[channel_number]['v_sense'] = new_channel
        new_channel.set_attribute('channel_number', channel_number)
        new_channel.set_attribute('channel_type', 'vsense')
        # new_channel.set_delegator(self)
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_voltage_sense.__doc__)
        # new_channel.set_display_format_function(function = lambda float_data: lab_utils.eng_string(float_data, fmt=fmt,si=True) + 'A')
        return self._add_channel(new_channel)
    def add_channel_current_sense(self, channel_name, channel_number=1):
        '''current readback'''
        #range, nplc?
        # [:SENSe[1]]:CURRent[:DC]:NPLCycles <n> Set speed (PLC)
        self._init_channel(channel_number)
        new_channel = channel(channel_name,read_function=lambda channel_number=channel_number: self._isense(channel_number))
        self._configured_channels[channel_number]['i_sense'] = new_channel
        new_channel.set_attribute('channel_number', channel_number)
        new_channel.set_attribute('channel_type', 'isense')
        # new_channel.set_delegator(self)
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_current_sense.__doc__)
        # new_channel.set_display_format_function(function = lambda float_data: lab_utils.eng_string(float_data, fmt=fmt,si=True) + 'A')
        return self._add_channel(new_channel)
    def add_channel_voltage_compliance(self, channel_name, channel_number=1):
        '''max voltage in current forcing modes'''
        
        #there are two thresholds. Source compliance (OVP) and Sense compliance (true compliance). Ignoring the former for now....
        # these are very coarse. ie
        # <n> = -210 to 210 Specify V-Source limit
        # 20 Set limit to 20V
        # 40 Set limit to 40V 
        # 60 Set limit to 60V
        # 18-80 SCPI Command Reference 2400 Series SourceMeter® User’s Manual 
        # 80 Set limit to 80V
        # 100 Set limit to 100V 
        # 120 Set limit to 120V 
        # 160 Set limit to 160V 
        # 161 to 210 Set limit to 210V (NONE)
        # DEFault Set limit to 210V (NONE)
        # MINimum Set limit to 20V
        # MAXimum Set limit to 210V (NONE)'''
        # :SOURce[1]:VOLTage:PROTection[:LEVel] 
        # TODO if this is useful
        self._init_channel(channel_number)
        new_channel = channel(channel_name,write_function=lambda v, channel_number=channel_number: self._vcompl(channel_number, v))
        self._configured_channels[channel_number]['v_compl'] = new_channel
        new_channel.set_attribute('channel_number', channel_number)
        new_channel.set_attribute('channel_type', 'vcompl')
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_voltage_compliance.__doc__)
        # new_channel.set_display_format_function(function = lambda float_data: lab_utils.eng_string(float_data, fmt=fmt,si=True) + 'V')
        return self._add_channel(new_channel)
    def add_channel_current_compliance(self, channel_name, channel_number=1):
        '''max current in voltage forcing modes'''
        self._init_channel(channel_number)
        new_channel = channel(channel_name,write_function=lambda i, channel_number=channel_number: self._icompl(channel_number, i))
        self._configured_channels[channel_number]['i_compl'] = new_channel
        new_channel.set_attribute('channel_number', channel_number)
        new_channel.set_attribute('channel_type', 'icompl')
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_current_compliance.__doc__)
        # new_channel.set_display_format_function(function = lambda float_data: lab_utils.eng_string(float_data, fmt=fmt,si=True) + 'V')
        return self._add_channel(new_channel)
    def add_channels(self, channel_name, channel_number=1):
        '''shortcut'''
        return (self.add_channel_voltage_force(f'{channel_name}_vforce', channel_number),
                self.add_channel_current_force(f'{channel_name}_iforce', channel_number),
                self.add_channel_voltage_sense(f'{channel_name}_vsense', channel_number),
                self.add_channel_current_sense(f'{channel_name}_isense', channel_number),
                self.add_channel_voltage_compliance(f'{channel_name}_vcompl', channel_number),
                self.add_channel_current_compliance(f'{channel_name}_icompl', channel_number),
                )
    #TODO read_delegated??

import time
class keithley_2600(keithley_2400):
    '''use 2400 personality emulator compatibility script '''
    def __init__(self, interface_visa):
        #try:
        #    interface_visa.write("DIAG:EXIT")
        #except pyvisa.errors.VisaIOError as e:
        #    print(e)
        interface_visa.write("*RST")
        #interface_visa.write("loadandrunscript Persona2400")
        # print('hello')
        # for i, line in enumerate(type(self)._Persona2400.splitlines()):
            # msg = f'{i}: {line.strip()}'
            # input(msg)
            # print(msg); time.sleep(0.01)
            # interface_visa.write(line.strip())
            # time.sleep(0.005)
        #tmo = interface_visa.timeout
        #interface_visa.timeout = 30
        #interface_visa.write(type(self)._Persona2400)
        #interface_visa.write("endscript")
        #interface_visa.timeout = tmo
        #self.get_interface().write("DIAG:EXIT")
        interface_visa.write("Initialize2400")
        interface_visa.write("Engine2400")
        super().__init__(interface_visa)
        #self._raw_write = self.get_interface().write
        #self._raw_read = self.get_interface().read
        #self._raw_ask = self.get_interface().ask
    #def _persona_decorator(func):
    #    @wraps(func)
    #    def persona_wrapper(self, *args, **kwargs):
    #        self._raw_write('Execute2400("')
    #        resp = func(*args, **kwargs)
    #        self._raw_write('")')


        
    _Persona2400 = '''
        loadandrunscript Persona2400
        --$Change: 76212 $
        
        local gModelSupport =
        {
            ["2601B"] = {mFeatureDigio = true},
            ["2602B"] = {mFeatureDigio = true},
            ["2604B"] = {mFeatureDigio = false},
            ["2611B"] = {mFeatureDigio = true},
            ["2612B"] = {mFeatureDigio = true},
            ["2614B"] = {mFeatureDigio = false},
            ["2634B"] = {mFeatureDigio = false},
            ["2635B"] = {mFeatureDigio = true},
            ["2636B"] = {mFeatureDigio = true},
        }
        
        local gDisplayVariables = {}
        gDisplayVariables.mDisplayScreen = display.screen
        display.screen = display.USER
        
        gDisplayVariables.mDisplayText1 = display.gettext(false, 1)
        gDisplayVariables.mDisplayText2 = display.gettext(false, 2)
        -- Loading Message
        display.clear()
        display.setcursor(1, 1)
        if gModelSupport[localnode.model] then
            display.settext("Please Wait...")
            display.setcursor(2, 1)
            display.settext("Initializing 2400 mode")    
            delay(50e-3)
        else    
            display.settext("Model not supported")
            display.setcursor(2, 1)
            display.settext("Script requires Series 2600B")
            delay(2)
            display.setcursor(1, 1)
            display.settext(gDisplayVariables.mDisplayText1)
            display.setcursor(2, 1)
            display.settext(gDisplayVariables.mDisplayText2)
            display.screen = gDisplayVariables.mDisplayScreen
            exit()
        end
        
        
        local g2400FwRev = "C32   Oct  4 2010 14:20:11/A02  /K/H"
        local gAutoRunEnable = false
        local gInitialized = false
        local gDisplayErrors = false
        local gCommandTree
        local gErrorQueue = {}
        local gCurrentBuffer
        local gVoltageBuffer
        local gSMCurrentBuffer
        local gSMVoltageBuffer
        -- Setter and getter functions 
        local gAccessors = {}
        local gRemoteComm = ki.remotecomm
        
        local NullFunction = function () end
        
        local gCharCodes =
        {
            mB              = string.byte([[B]]),
            mBracketLeft    = string.byte("["),
            mBracketRight   = string.byte("]"),
            mC              = string.byte([[C]]),
            mCaret          = string.byte([[^]]),
            mColon          = string.byte([[:]]),
            mComma          = string.byte([[,]]),
            mDoubleQuote    = string.byte([["]]),
            mDot            = string.byte([[.]]),
            mH              = string.byte([[H]]),
            mHash           = string.byte([[#]]),
            mMinus          = string.byte([[-]]),
            mNewLine        = string.byte("\n"),
            mNine           = string.byte([[9]]),
            mOne            = string.byte([[1]]),
            mParenLeft      = string.byte([[(]]),
            mParenRight     = string.byte([[)]]),
            mPlus           = string.byte([[+]]),
            mQ              = string.byte([[Q]]),
            mQuestion       = string.byte([[?]]),
            mR              = string.byte([[R]]),
            mSemicolon      = string.byte([[;]]),
            mSingleQuote    = string.byte([[']]),
            mSlash          = string.byte([[/]]),
            mStar           = string.byte([[*]]),
            mT              = string.byte([[T]]),
            mV              = string.byte([[V]]),
            mZero           = string.byte([[0]]),
        }
        
        local gResponseValues =
        {
            [true]  = "1",
            [false] = "0",
            [1]     = "1",
            [0]     = "0",
        }
        
        local gNonProgMnemonic  = "[^%a%d_]"
        local gNonWhitespace    = "[^%s]"
        
        local gNan = 9.91e37
        local gInf = 9.90e37
        local gEpsilon = 5e-7
        
        local gSpecialCommands =
        {
            ["$Empty"] =
            {
                mCommand = {mPriority = true},
            },
            ["ABORT"] =
            {
                mCommand = {mPriority = true},
            },
            ["*TRG"] =
            {
                mCommand = {mPriority = true},
            },
            [gRemoteComm.types.DCL] =
            {
                mCommand = {mPriority = true},
            },
            [gRemoteComm.types.TRIGGER] =
            {
            },
            [gRemoteComm.types.SETLOCKOUT] =
            {
                mCommand = {},
            },
            [gRemoteComm.types.RESETLOCKOUT] =
            {
                mCommand = {},
            },
            -- gRemoteComm.types.GOTOLOCAL
            -- gRemoteComm.types.GOTOREMOTE
        }
        gSpecialCommands["$Empty"].mCommand.mExecute = NullFunction
        
        --============================================================================
        --
        -- Local variables used for better performance
        --
        --============================================================================
        
        local gAscii = format.ASCII
        local gMathAbs = math.abs
        local gTypeDcl = gRemoteComm.types.DCL
        
        local Print = gRemoteComm.partialprint
        local PrintNumber = function (lNumber)
            if gAccessors.mGetFormatData() == gAscii and lNumber >= 0 then
                gRemoteComm.partialprint("+")
            end
            gRemoteComm.partialprintnumber(lNumber)
        end
        
        local gSource = smua.source
        local gMeasure = smua.measure
        local gFilter = gMeasure.filter
        local gArm = smua.trigger.arm
        local gTrigger = smua.trigger
        local gSourceCap = ki.smua.trigger.source
        local gTriggerGenerator = trigger.generator[1]
        local gDCAMPS = smua.OUTPUT_DCAMPS
        local gDCVOLTS = smua.OUTPUT_DCVOLTS
        
        local gRemoteCommStatus = gRemoteComm.status
        local gStatusOvertemp = status.questionable.over_temperature
        local gStatusMeasurement = status.measurement
        local gDigioSupport = true
        local gTriggerLines
        
        gDigioSupport = gModelSupport[localnode.model].mFeatureDigio
        if gDigioSupport then
            gTriggerLines = digio.trigger
        end
        
        -- Trigger Timer usage
        --[[
            trigger.timer[1] -> Measurement Event Detector
            trigger.timer[3] -> Trigger Delay timer
            trigger.timer[4] -> Arm Timer
            trigger.timer[5] -> Source Delay timer
        --]]
        local gMeasureCompleteTimer = trigger.timer[1]
        local gTrigDelayTimer = trigger.timer[3]
        local gArmTimer = trigger.timer[4]
        local gSourceDelayTimer = trigger.timer[5]
        -- Trigger Blender usage
        --[[
            trigger.blender[1] -> 
            trigger.blender[2] -> 
            trigger.blender[3] -> 
            trigger.blender[4] -> Arm layer output triggers
            trigger.blender[5] -> Trigger layer output triggers
            trigger.blender[6] -> Used when arm and trigger layer use the same output
        --]]
        local gBlender1 = trigger.blender[1]
        local gBlender2 = trigger.blender[2]
        local gBlender3 = trigger.blender[3]
        local gTrigOutArm = trigger.blender[4]
        local gTrigOutTrig = trigger.blender[5]
        local gTrigOutBoth = trigger.blender[6]
        
        -- SMU A Source getter functions
        local smua_GetSrcFunc = makegetter(gSource, "func")
        local smua_GetSrcRngV = makegetter(gSource, "rangev")
        local smua_GetSrcRngI = makegetter(gSource, "rangei")
        local smua_GetSrcLevV = makegetter(gSource, "levelv")
        local smua_GetSrcLevI = makegetter(gSource, "leveli")
        local smua_GetSrcLimV = makegetter(gSource, "limitv")
        local smua_GetSrcLimI = makegetter(gSource, "limiti")
        
        -- SMU A Source setter functions
        local smua_SetSrcRngV = makesetter(gSource, "rangev")
        local smua_SetSrcRngI = makesetter(gSource, "rangei")
        local smua_SetSrcLevV = makesetter(gSource, "levelv")
        local smua_SetSrcLevI = makesetter(gSource, "leveli")
        local smua_SetSrcLimV = makesetter(gSource, "limitv")
        local smua_SetSrcLimI = makesetter(gSource, "limiti")
        
        -- SMU A Measure setter functions
        local smua_SetMeasRngV = makesetter(gMeasure, "rangev")
        local smua_SetMeasRngI = makesetter(gMeasure, "rangei")
        
        -- Setter and getter functions 
        gAccessors.mStatusOvertempCondition = makegetter(gStatusOvertemp, "condition")
        gAccessors.mStatusMeasurementCondition = makegetter(gStatusMeasurement, "condition")   
        gAccessors.mSourceOutputEnableAction = makegetter(gSource, "outputenableaction")
        gAccessors.mSetSourceCapMaxi = makesetter(gSourceCap,"maxi")
        gAccessors.mSetSourceCapMaxv = makesetter(gSourceCap,"maxv")
        gAccessors.mTriggerSourceStimulus = makesetter(gTrigger.source, "stimulus")
        gAccessors.mTriggerSourceLinearv = gTrigger.source.linearv
        gAccessors.mTriggerSourceLineari = gTrigger.source.lineari
        gAccessors.mTriggerSourceListv = gTrigger.source.listv
        gAccessors.mTriggerSourceListi = gTrigger.source.listi
        gAccessors.mTriggerSourceLogv = gTrigger.source.logv
        gAccessors.mTriggerSourceLogi = gTrigger.source.logi
        gAccessors.mTriggerSourceAction = makesetter(gTrigger.source, "action")
        gAccessors.mTriggerMeasureiv = gTrigger.measure.iv
        gAccessors.mTriggerMeasurei = gTrigger.measure.i
        gAccessors.mTriggerMeasureStimulus = makesetter(gTrigger.measure, "stimulus")
        
        gAccessors.mSetSourceLimiti = makesetter(gSource, "limiti")
        gAccessors.mSetSourceLimitv = makesetter(gSource, "limitv")
        gAccessors.mSetSourceLeveli = makesetter(gSource, "leveli")
        gAccessors.mSetSourceLevelv = makesetter(gSource, "levelv")
        gAccessors.mSetSourceRangei = makesetter(gSource, "rangei")
        gAccessors.mSetSourceRangev = makesetter(gSource, "rangev")
        gAccessors.mSetSourceAutoRangei = makesetter(gSource, "autorangei")
        gAccessors.mSetSourceAutoRangev = makesetter(gSource, "autorangev")
        gAccessors.mSetSourceDelay = makesetter(gSource, "delay")
        gAccessors.mSetMeasureAutoRangev = makesetter(gMeasure,"autorangev")
        gAccessors.mSetMeasureAutoRangei = makesetter(gMeasure,"autorangei")
        gAccessors.mSetMeasureRangev = makesetter(gMeasure,"rangev")
        gAccessors.mSetMeasureRangei = makesetter(gMeasure,"rangei")
        gAccessors.mSetMeasureAutoZero = makesetter(gMeasure, "autozero")
        gAccessors.mSetMeasureNplc = makesetter(gMeasure, "nplc")
        gAccessors.mMeasureiv = gMeasure.iv
        gAccessors.mMeasurei = gMeasure.i
        gAccessors.mSetSourceFunc = makesetter(gSource, "func")
        gAccessors.mSetSourceOutput = makesetter(gSource, "output")
        gAccessors.mSetSense = makesetter(smua,"sense")
        gAccessors.mSetFilterCount = makesetter(gFilter, "count")
        gAccessors.mSetFilterType = makesetter(gFilter, "type")
        gAccessors.mSetFilterEnable = makesetter(gFilter, "enable")
        
        gAccessors.mGetSourceCapMaxi = makegetter(gSourceCap,"maxi")
        gAccessors.mGetSourceCapMaxv = makegetter(gSourceCap,"maxv")
        gAccessors.mGetSourceLimiti = makegetter(gSource, "limiti")
        gAccessors.mGetSourceLimitv = makegetter(gSource, "limitv")
        gAccessors.mGetSourceLeveli = makegetter(gSource, "leveli")
        gAccessors.mGetSourceLevelv = makegetter(gSource, "levelv")
        gAccessors.mGetSourceRangei = makegetter(gSource, "rangei")
        gAccessors.mGetSourceRangev = makegetter(gSource, "rangev")
        gAccessors.mGetSourceAutoRangei = makegetter(gSource, "autorangei")
        gAccessors.mGetSourceAutoRangev = makegetter(gSource, "autorangev")
        gAccessors.mGetSourceDelay = makegetter(gSource, "delay")
        gAccessors.mGetMeasureAutoRangev = makegetter(gMeasure,"autorangev")
        gAccessors.mGetMeasureAutoRangei = makegetter(gMeasure,"autorangei")
        gAccessors.mGetMeasureRangev = makegetter(gMeasure,"rangev")
        gAccessors.mGetMeasureRangei = makegetter(gMeasure,"rangei")
        gAccessors.mGetMeasureAutoZero = makegetter(gMeasure, "autozero")
        gAccessors.mGetMeasureNplc = makegetter(gMeasure, "nplc")
        gAccessors.mGetSourceFunc = makegetter(gSource, "func")
        gAccessors.mGetSourceOutput = makegetter(gSource, "output")
        gAccessors.mGetStatusStandardEvent = makegetter(status.standard, "event")
        gAccessors.mGetSense = makegetter(smua,"sense")
        gAccessors.mGetFormatData = makegetter(format, "data")
        local SmuOn = function ()
            gAccessors.mSetSourceOutput(1)
        end
        
        --============================================================================
        --
        -- Model specific tables
        --
        -- These tables store model specific range related information.
        --
        --============================================================================
        
        local gOperatingBoundaries
        local gSafeOperatingArea
        local gRangeTable
        local gPrintEnable = false
        
        if localnode.model == "2612B" or localnode.model == "2611B"
        or localnode.model == "2614B" then
        
            gOperatingBoundaries =
            {
                -- Source voltage amplitudes
                mDefaultVoltageLevel    = 0,
                mMinimumVoltageLevel    = -202,
                mMaximumVoltageLevel    = 202,
        
                -- Source current amplitudes
                mDefaultCurrentLevel    = 0,
                mMinimumCurrentLevel    = -1.515,
                mMaximumCurrentLevel    = 1.515,
        
                -- Source/sense voltage ranges
                mDefaultVoltageRange    = 20,
                --mMinimumVoltageRange    = 200e-3,
                mMinimumVoltageRange    = 0,
                mMaximumVoltageRange    = 200,
        
                -- Source/sense current ranges
                mDefaultCurrentRange    = 100e-6,
                --mMinimumCurrentRange    = 100e-9,
                mMinimumCurrentRange    = 0,
                mMaximumCurrentRange    = 1.5,
        
                -- Source current limits
                mDefaultCurrentLimit    = 1.05e-4,
                mMinimumCurrentLimit    = 10e-9,
                mMaximumCurrentLimit    = 1.515,
        
                -- Source voltage limits
                mDefaultVoltageLimit    = 21,
                mMimimumVoltageLimit    = 20e-3,
                mMaximumVoltageLimit    = 202,
        
                -- Current lowrange (current auto ranging lower limit)
                mDefaultCurrentLowRange = 1e-6,
                mMinimumCurrentLowRange = 100e-9,
                mMaximumCurrentLowRange = 1.5,
        
                -- Voltage lowrange
                mDefaultVoltageLowRange = 200e-3,
                mMimimumVoltageLowRange = 200e-3,
                mMaximumVoltageLowRange = 200,
        
                -- Resistance ranges
                mDefaultResistanceRange = 2.1e5,
                mMinimumResistanceRange = 2.1e1,
                mMaximumResistanceRange = 2.1e8,
            }
        
            gRangeTable =
            {
                mVoltage        = {200e-3, 2, 20, 200},
                mVoltageLimit   = {200e-3, 2, 20, 200},
        
                mCurrent        = {1e-7, 1e-6, 1e-5, 1e-4, 1e-3, 1e-2, 1e-1, 1, 1.5},
                mCurrentLimit   = {1e-7, 1e-6, 1e-5, 1e-4, 1e-3, 1e-2, 1e-1, 1.5},
        
                mResistance     = {2.1e1, 2.1e2, 2.1e3, 2.1e4, 2.1e5, 2.1e6, 2.1e7, 2.1e8},
            }
        
            gSafeOperatingArea = {mVoltage = 20, mCurrent = .1}
        elseif localnode.model == "2602B" or localnode.model == "2601B" or localnode.model == "2604B" then
        
            gOperatingBoundaries =
            {
                -- Source voltage amplitudes
                mDefaultVoltageLevel    = 0,
                mMinimumVoltageLevel    = -40.4,
                mMaximumVoltageLevel    = 40.4,
        
                -- Source current amplitudes
                mDefaultCurrentLevel    = 0,
                mMinimumCurrentLevel    = -3.03,
                mMaximumCurrentLevel    = 3.03,
        
                -- Source/sense voltage ranges
                mDefaultVoltageRange    = 20,
                --mMinimumVoltageRange    = 100e-3,
                mMinimumVoltageRange    = 0,
                mMaximumVoltageRange    = 40,
        
                -- Source/sense current ranges
                mDefaultCurrentRange    = 100e-6,
                --mMinimumCurrentRange    = 100e-9,
                mMinimumCurrentRange    = 0,
                mMaximumCurrentRange    = 3,
        
                -- Source current limits
                mDefaultCurrentLimit    = 1.05e-4,
                mMinimumCurrentLimit    = 10e-9,
                mMaximumCurrentLimit    = 3.03,
        
                -- Source voltage limits
                mDefaultVoltageLimit    = 21,
                mMimimumVoltageLimit    = 10e-3,
                mMaximumVoltageLimit    = 40.4,
        
                -- Current lowrange (current auto ranging lower limit)
                mDefaultCurrentLowRange = 1e-6,
                mMinimumCurrentLowRange = 100e-9,
                mMaximumCurrentLowRange = 3,
        
                -- Voltage lowrange
                mDefaultVoltageLowRange = 100e-3,
                mMimimumVoltageLowRange = 100e-3,
                mMaximumVoltageLowRange = 40,
        
                -- Resistance ranges
                mDefaultResistanceRange = 2.1e5,
                mMinimumResistanceRange = 2.1e1,
                mMaximumResistanceRange = 2.1e8,
            }
        
            gRangeTable =
            {
                mVoltage        = {100e-3, 1, 6, 40},
                mVoltageLimit   = {100e-3, 1, 40},
        
                mCurrent        = {1e-7, 1e-6, 1e-5, 1e-4, 1e-3, 1e-2, 1e-1, 1, 3},
                mCurrentLimit   = {1e-7, 1e-6, 1e-5, 1e-4, 1e-3, 1e-2, 1e-1, 3},
        
                mResistance     = {2.1e1, 2.1e2, 2.1e3, 2.1e4, 2.1e5, 2.1e6, 2.1e7, 2.1e8},
            }
        
            gSafeOperatingArea = {mVoltage = 6, mCurrent = 1}
        elseif localnode.model == "2636B" or localnode.model == "2635B" or localnode.model == "2634B" then
        
            gOperatingBoundaries =
            {
                -- Source voltage amplitudes
                mDefaultVoltageLevel    = 0,
                mMinimumVoltageLevel    = -202,
                mMaximumVoltageLevel    = 202,
        
                -- Source current amplitudes
                mDefaultCurrentLevel    = 0,
                mMinimumCurrentLevel    = -1.515,
                mMaximumCurrentLevel    = 1.515,
        
                -- Source/sense voltage ranges
                mDefaultVoltageRange    = 20,
                --mMinimumVoltageRange    = 200e-3,
                mMinimumVoltageRange    = 0,
                mMaximumVoltageRange    = 200,
        
                -- Source/sense current ranges
                mDefaultCurrentRange    = 100e-6,
                --mMinimumCurrentRange    = 1e-10,
                mMinimumCurrentRange    = 0,
                mMaximumCurrentRange    = 1.5,
        
                -- Source current limits
                mDefaultCurrentLimit    = 1.05e-4,
                mMinimumCurrentLimit    = 1e-10,
                mMaximumCurrentLimit    = 1.515,
        
                -- Source voltage limits
                mDefaultVoltageLimit    = 21,
                mMimimumVoltageLimit    = 20e-3,
                mMaximumVoltageLimit    = 202,
        
                -- Current lowrange (current auto ranging lower limit)
                mDefaultCurrentLowRange = 1e-6,
                mMinimumCurrentLowRange = 1e-10,
                mMaximumCurrentLowRange = 1.5,
        
                -- Voltage lowrange
                mDefaultVoltageLowRange = 200e-3,
                mMimimumVoltageLowRange = 200e-3,
                mMaximumVoltageLowRange = 200,
        
                -- Resistance ranges
                mDefaultResistanceRange = 2.1e5,
                mMinimumResistanceRange = 2.1e1,
                mMaximumResistanceRange = 2.1e8,
            }
        
            gRangeTable =
            {
                mVoltage        = {200e-3, 2, 20, 200},
                mVoltageLimit   = {200e-3, 2, 20, 200},
        
                mCurrent        = {1e-10, 1e-9, 1e-8, 1e-7, 1e-6, 1e-5, 1e-4, 1e-3, 1e-2, 1e-1, 1, 1.5},
                mCurrentLimit   = {1e-10, 1e-9, 1e-8, 1e-7, 1e-6, 1e-5, 1e-4, 1e-3, 1e-2, 1e-1, 1.5},
        
                mResistance     = {2.1e1, 2.1e2, 2.1e3, 2.1e4, 2.1e5, 2.1e6, 2.1e7, 2.1e8},
            }
        
            gSafeOperatingArea = {mVoltage = 20, mCurrent = .1}
        end
        
        --============================================================================
        --
        --  Parsers and input managment
        --
        --============================================================================
        
        local gOrigin
        local gEngineMode = false
        local gParserState = {}
        local gCurrentRoot
        
        --[[
        
            Data Structures.
        
            Command Table
        
            The main parser data structure, the command table, is a hierarchical tree
            based structure that directly reflects the command structure of the
            simulated SCPI instrument.  At each level, an element could be a
            non-terminal (path) element or a terminal command.  For terminal commands,
            there can be a command form and/or a query form.  The command might also
            take parameters.  The following generic structures are used to hold the
            command tables:
        
            Header Element:
                (mPath)     Header Element sub-tree (for path, when next char is a :)
                            (This member is implied. For efficiency, its members are
                            stored directly at this level. See comment below.)
                mCommand    Execution structure for command (if not a path)
                mQuery      Execution structure for query (if not a path)
        
            Command Element:
                mExecute    Execution function.
                mParameters Array of parameter elements for parameters.
        
            Parameter Element:
                mOptional   True if parameter is optional. False or nil if not.
                mDefault    Default value.
                mParse      Parser function.
        
            For SCPI based instruments, command path strings are not case sensitive.
            We can utilize this to simplify building the command table structures.
            Instead of creating an explicit mPath member, we can simply encode all
            the sub-tree elements with upper case keys and put them directly in the
            table of the parent command element. Observe that all member names start
            with a lower case "m" and will not conflict with any child element keys.
        
        
            ParseInfo
        
                This structure holds a partially parsed command. The parameters have
                been extracted as raw strings but have note been checked or decoded.
        
                mCommandNode The command element from the command tree.
                mCommand    The mQuery or mCommand element from the command node.
                mParameters Array of parameter strings (partially parsed).
                mError      (When there is an error) The error code detected while
                            parsing the command, or a table of error codes.
        
            Parser State
        
                This structure maintains the input and parser state.
        
                mCurrentText        The text of the current unparsed (or partially parsed) data.
                mCurrentTextUpper   An upper case copy of mCurrentText.
                mCurrentPosition    The byte position of where the parser will resume.
                mNextMessage        The next unparsed record in the record chain.
                mLastMessage        The last record in the record chain.
                mNextCommand        A ParseInfo table for the next command to process.
                mPartialMessage     An accumulator for a sequence of partial messages.
        
            Each message record has the following fields:
        
                mType           The message type
                mMessage        The text of the message
                mNext           Reference to next record if there is one
                mCount          The count of messages received from firmware
        --]]
        
        ------------------------------------------------------------------------------
        --
        --  AddMessage
        --
        --  Add a message to the Parser input queue.
        --
        ------------------------------------------------------------------------------
        
        local AddMessage = function (lMessage, lType, lCount)
            local lNewRecord = {mType = lType, mMessage = lMessage, mCount = lCount}
            if gParserState.mLastMessage then
                gParserState.mLastMessage.mNext = lNewRecord
            else
                gParserState.mNextMessage = lNewRecord
            end
            gParserState.mLastMessage = lNewRecord
        end
        
        ------------------------------------------------------------------------------
        --
        --  GetNewMessage
        --
        --  Get a new command interface message and add it to the parser input queue.
        --  The first message will decide the command interface origin to use. Once
        --  a command interface is chosen, only messages from that command interface
        --  will be used. All other interfaces will be ignored.
        --
        ------------------------------------------------------------------------------
        
        local GetNewMessage
        
        local GetCommandMessage = function ()
            local lMessage
            local lType
            local lOrigin
        
            lMessage, lType, lOrigin = gRemoteComm.getmessage()
            if lOrigin == gOrigin then
                if lType == gTypeDcl then
                    -- Clear all messages and commands ahead of the DCL.
                    gParserState.mLastMessage = nil
                    gParserState.mPartialMessage = nil
                    gParserState.mCurrentText = nil
                    gParserState.mNextCommand = nil
                    gPrintEnable = false
                end
                AddMessage(lMessage, lType, 1)
            end
        end
        
        local GetFirstCommandMessage = function ()
            local lMessage
            local lType
            local lOrigin
        
            lMessage, lType, lOrigin = gRemoteComm.getmessage()
            if lMessage then
                gRemoteComm.output = lOrigin
                gOrigin = lOrigin
                AddMessage(lMessage, lType, 1)
                GetNewMessage = GetCommandMessage
            end
        end
        
        GetNewMessage = GetFirstCommandMessage
        
        ------------------------------------------------------------------------------
        --
        --  ParseBlockLength
        --
        --  This function determines the end of a block data parameter. It will
        --  return the position of the last character in the block data element. If
        --  there is an error, it will return the starting position.
        --
        ------------------------------------------------------------------------------
        
        local ParseBlockLength = function (lText, lStart)
            local lCharCode = string.byte(lText, lStart)
            local lCount
        
            if lCharCode == gCharCodes.mZero then
                return string.len(lText) - lStart
            else
                local lLength = 0
        
                -- Get length of count field
                lCount = lCharCode - gCharCodes.mZero
                if lStart + 1 + lCount > string.len(lText) then
                    -- Not enough data for length field
                    return lStart
                end
                for lIndex = lStart + 1, lStart + lCount do
                    lCharCode = string.byte(lText, lIndex)
                    if lCharCode >= gCharCodes.mZero and lCharCode <= gCharCodes.mNine then
                        lLength = lLength * 10 + lCharCode - gCharCodes.mZero
                    else
                        -- Bad length field
                        return lStart
                    end
                end
                if lStart + lCount + lLength > string.len(lText) then
                    -- Not enough data
                    return lStart
                end
                return lStart + lCount + lLength
            end
        end
        
        ------------------------------------------------------------------------------
        --
        --  ParseExpression
        --
        --  Parse a 488.2 expression. This function will extract an expression
        --  parameter including the parenthesis. The character at lStart should be the
        --  left parenthesis.
        --
        ------------------------------------------------------------------------------
        
        local ParseExpression = function (lText, lStart)
            local lLength = string.len(lText)
            local lIndex = lStart + 1
            local lIndex2
            local lNesting = 1
        
            while lNesting > 0 and lIndex <= lLength do
                lIndex2 = string.find(lText, "[()]", lIndex) or lLength + 1
                if lIndex2 > lLength then
                    return "", lIndex2
                end
                if string.byte(lText, lIndex2) == gCharCodes.mParenLeft then
                    lNesting = lNesting + 1
                else
                    lNesting = lNesting - 1
                end
                lIndex = lIndex2 + 1
            end
            return string.sub(lText, lStart, lIndex2), lIndex2 + 1
        end
        
        ------------------------------------------------------------------------------
        --
        --  ParseString
        --
        --  Parse a 488.2 string.  This function will extract a string parameter
        --  including all nested quotes.  The character at lStart must be the
        --  delimiter to use.
        --
        ------------------------------------------------------------------------------
        
        local ParseString = function (lText, lStart)
            local lLength = string.len(lText)
            local lQuote = string.sub(lText, lStart, lStart)
            local lPattern = "[%"..lQuote.."]"
            local lIndex = lStart + 1
            local lIndex2
            local lQuoteCode = string.byte(lQuote)
        
            while lIndex <= lLength do
                lIndex2 = string.find(lText, lPattern, lIndex) or lLength + 1
                if string.byte(lText, lIndex2 + 1) ~= lQuoteCode then
                    break
                end
                lIndex = lIndex2 + 2
            end
            if string.byte(lText, lIndex2) ~= lQuoteCode then
                return "", lStart
            end
            return string.sub(lText, lStart, lIndex2), lIndex2 + 1
        end
        
        ------------------------------------------------------------------------------
        --
        -- ParseNRf
        --
        -- Parse an NRf number. If a valid NRf number is found, this function returns
        -- the index of the first character after the number. If a valid NRf number
        -- not found, it returns the start index.
        --
        -- After parsing, the text parsed can be passed to tonumber() for conversion
        -- after removing any intermediate whitespace.
        --
        ------------------------------------------------------------------------------
        
        local ParseNRf = function (lText, lStart)
            local lCharCode
            local lIndex = lStart
            local lIndex2
            local lIndex3
        
            -- Skip leading sign
            lCharCode = string.byte(lText, lIndex)
            if lCharCode == gCharCodes.mPlus or lCharCode == gCharCodes.mMinus then
                lIndex = lIndex + 1
            end
        
            -- Parse mantissa
            lIndex2, lIndex3 = string.find(lText, "^%d*", lIndex)
            if lIndex2 then
                -- There were leading digits. Look for optional dot and optional
                -- digits that follow.
                lIndex = lIndex3 + 1
                lCharCode = string.byte(lText, lIndex)
                if lCharCode == gCharCodes.mDot then
                    lIndex = lIndex + 1
                    lIndex2, lIndex3 = string.find(lText, "^%d*", lIndex)
                    if lIndex2 then
                        lIndex = lIndex3 + 1
                    end
                end
            else
                -- There were no leading digits. We must now see a dot and one or
                -- more digits.
                lIndex2, lIndex3 = string.find(lText, "^[.]%d+", lIndex)
                if lIndex2 then
                    lIndex = lIndex3 + 1
                else
                    -- Not a valid number
                    return lStart
                end
            end
        
            -- Parse exponent
            lIndex2, lIndex3 = string.find(lText, "^%s*[Ee]", lIndex)
            if lIndex2 then
                -- There is an exponent
                lIndex = lIndex3 + 1
                lIndex2, lIndex3 = string.find(lText, "^%s*[+-]?%d+", lIndex)
                if lIndex2 then
                    lIndex = lIndex3 + 1
                else
                    -- Invalid exponent
                    return lStart
                end
            end
        
            -- A valid number was found
            return lIndex
        end
        
        --============================================================================
        --
        -- Parser Tables
        --
        --============================================================================
        
        local gParserTable = {}
        
        ------------------------------------------------------------------------------
        --
        -- ParseParameterAny
        --
        -- Accept an exact copy of the parameter. This parser function is intended
        -- to be used as a place holder until a real parser function can be
        -- implemented for the parameter.
        --
        ------------------------------------------------------------------------------
        
        gParserTable.ParseParameterAny = function (lParameter)
            return lParameter
        end
        
        ------------------------------------------------------------------------------
        --
        --  ParseParameterBlockData
        --
        --  Parse a 488.2 block data string.
        --
        ------------------------------------------------------------------------------
        
        gParserTable.ParseParameterBlockData = function (lParameter)
            local lCharCode = string.byte(lParameter)
        
            if lCharCode == gCharCodes.mHash then
                lCharCode = string.byte(lParameter, 2)
                return string.sub(lParameter, 3 + lCharCode - gCharCodes.mZero)
            else
                return nil, -104
            end
        end
        
        ------------------------------------------------------------------------------
        --
        -- ParseParameterBoolean
        --
        ------------------------------------------------------------------------------
        
        gParserTable.ParseParameterBoolean = function (lParameter)
            local lIndex
            local lLength
        
            lLength = string.len(lParameter)
            lIndex = ParseNRf(lParameter, 1)
        
            if lIndex > 1 then
                -- This is a numeric value
                local lValue, lIndex2
        
                lValue, lIndex2 = string.find(lParameter, "^%s*$", lIndex)
                if lIndex2 ~= lLength then
                    return nil, -120
                end
                lParameter = string.gsub(lParameter, " ", "")
                lValue = tonumber(lParameter)
                if lValue >= 0.5 or lValue < -0.5 then
                    return true
                end
                return false
            end
            if lParameter == "ON" then
                return true
            elseif lParameter == "OFF" then
                return false
            end
            return nil, -104
        end
        
        ------------------------------------------------------------------------------
        --
        -- ParseParameterChoice
        --
        ------------------------------------------------------------------------------
        
        gParserTable.ParseParameterChoice = function (lParameter, lParseData)
            local lValue, lError
            local lIndex
        
            lParseData = lParseData.mData
            lIndex = 1
            while lParseData[lIndex] do
                lValue, lError = lParseData[lIndex].mParse(lParameter, lParseData[lIndex])
                if lValue ~= nil then
                    return lValue
                end
                lIndex = lIndex + 1
            end
            return nil, -102
        end
        
        ------------------------------------------------------------------------------
        --
        -- ParseParameterExpression
        --
        ------------------------------------------------------------------------------
        
        gParserTable.ParseParameterExpression = function (lParameter)
            if string.byte(lParameter, 1) ~= gCharCodes.mParenLeft then
                return nil, -104
            end
            return lParameter
        end
        
        ------------------------------------------------------------------------------
        --
        -- ParseParameterName
        --
        ------------------------------------------------------------------------------
        
        gParserTable.ParseParameterName = function (lParameter, lParseData)
            lParameter = lParseData.mNames[lParameter]
        
            if lParameter then
                return lParameter
            else
                return nil, -102
            end
        end
        
        ------------------------------------------------------------------------------
        --
        -- ParseParameterNameString
        --
        ------------------------------------------------------------------------------
        
        gParserTable.ParseParameterNameString = function (lParameter, lParseData)
            local lError
        
            lParameter, lError = gParserTable.ParseParameterString(lParameter)
            if lParameter then
                lParameter = lParseData.mNames[string.upper(lParameter)]
        
                if lParameter then
                    return lParameter
                else
                    return nil, -150
                end
            else
                return nil, lError
            end
        end
        
        ------------------------------------------------------------------------------
        --
        -- ParseParameterNDN
        --
        -- This parser will accept an NDN or an NRf. If the number is NRf, it will
        -- be converted to an integer.
        --
        ------------------------------------------------------------------------------
        
        gParserTable.ParseParameterNDN = function (lParameter)
            local lCharCode
        
            lCharCode = string.byte(lParameter, 1)
            if lCharCode == gCharCodes.mHash then
                lCharCode = string.byte(lParameter, 2)
                lParameter = string.sub(lParameter, 3)
                if lCharCode == gCharCodes.mH then
                    return tonumber(lParameter, 16) or 0
                elseif lCharCode == gCharCodes.mQ then
                    return tonumber(lParameter, 8) or 0
                elseif lCharCode == gCharCodes.mB then
                    return tonumber(lParameter, 2) or 0
                else
                    return nil, -104
                end
            end
            return gParserTable.ParseParameterIntegerNRf(lParameter)
        end
        
        ------------------------------------------------------------------------------
        --
        -- ParseParameterNRf
        --
        -- This parser will accept an NRf number. This does not include INF. If the
        -- parameter is accepted, it is converted to a number.
        --
        ------------------------------------------------------------------------------
        
        gParserTable.ParseParameterNRf = function (lParameter)
            local lIndex = ParseNRf(lParameter, 1)
            if lIndex > string.len(lParameter) then
                lParameter = string.gsub(lParameter, " ", "")
                return tonumber(lParameter)
            end
            if lIndex > 1 then
                return nil, -102
            else
                return nil, -104
            end
        end
        
        ------------------------------------------------------------------------------
        --
        -- ParseParameterIntegerNRf
        --
        -- This parser will accept an NRf number and convert it to an integer.
        --
        ------------------------------------------------------------------------------
        
        gParserTable.ParseParameterIntegerNRf = function (lParameter)
            local lValue, lError
        
            lValue, lError = gParserTable.ParseParameterNRf(lParameter)
            if lValue then
                if lValue < 0 then
                    lValue = math.ceil(lValue - 0.5)
                else
                    lValue = math.floor(lValue + 0.5)
                end
            end
            return lValue, lError
        end
        
        ------------------------------------------------------------------------------
        --
        -- ParseParameterNumList
        --
        ------------------------------------------------------------------------------
        
        gParserTable.ParseParameterNumList = function (lParameter)
            local lList = {}
            local lCount
            local lCharCode
            local lLength = string.len(lParameter) - 1
            local lIndex
            local lIndex2
            local lIndex3
            local lText
            local lError
        
            lCharCode = string.byte(lParameter, 1)
            if lCharCode ~= gCharCodes.mParenLeft then
                return nil, -104
            end
            -- We don't need to verify the last parenthesis because the expression
            -- parser will guarantee they are matched and there is nothing after the
            -- last one.
        
            -- Break the list into raw text pairs
            lCount = 0
            lIndex2, lIndex3 = string.find(lParameter, "^ *", 2)
            lIndex = lIndex3 + 1
            while lIndex < lLength do
                lIndex2, lIndex3 = string.find(lParameter, " *, *", lIndex)
                if not lIndex2 then
                    lIndex2 = string.find(lParameter, " *[)]$", lIndex)
                    lIndex3 = lLength
                end
                if lIndex2 == lIndex then
                    -- Empty entry
                    return nil, -121
                end
                lText = string.sub(lParameter, lIndex, lIndex2 - 1)
                lIndex = lIndex3 + 1
        
                lIndex2 = string.find(lText, ":", 1)
                lCount = lCount + 2
                if lIndex2 then
                    lList[lCount - 1] = string.sub(lText, 1, lIndex2 - 1)
                    lList[lCount] = string.sub(lText, lIndex2 + 1)
                else
                    lList[lCount - 1] = lText
                    lList[lCount] = lText
                end
            end
        
            lIndex = 1
            while lIndex <= lCount do
                lList[lIndex], lError = gParserTable.ParseParameterIntegerNRf(lList[lIndex])
                if lError then
                    return nil, -260
                end
                lIndex = lIndex + 1
            end
        
            return lList
        end
        
        ------------------------------------------------------------------------------
        --
        -- ParseParameterString
        --
        ------------------------------------------------------------------------------
        
        gParserTable.ParseParameterString = function (lParameter)
            local lCharCode
        
            lCharCode = string.byte(lParameter, 1)
            if lCharCode == gCharCodes.mSingleQuote then
                lParameter = string.gsub(string.sub(lParameter, 2, -2), [['']], [[']])
            elseif lCharCode == gCharCodes.mDoubleQuote then
                lParameter = string.gsub(string.sub(lParameter, 2, -2), [[""]], [["]])
            else
                return nil, -104
            end
            return lParameter
        end
        
        ------------------------------------------------------------------------------
        --
        -- Reusable parameter tables
        --
        ------------------------------------------------------------------------------
        
        gParserTable.mParseAny          = {mParse = gParserTable.ParseParameterAny}
        gParserTable.mParseArmEvent =
        {
            mParse = gParserTable.ParseParameterName,
            mNames =
            {
                ["NONE"]        = "NONE",
                ["TENTER"]      = "TENT",
                ["TENT"]        = "TENT",
                ["TEXIT"]       = "TEX",
                ["TEX"]         = "TEX",
            }
        }
        gParserTable.mParseArmEventOptional =
        {
            mParse = gParserTable.ParseParameterName,
            mOptional = true,
            mNames =gParserTable.mParseArmEvent.mNames,
        }
        gParserTable.mParseArmTimer =
        {
            mParse = gParserTable.ParseParameterName,
            mOptional = true,
            mNames =
            {
                ["DEFAULT"]     = 0.1,
                ["DEF"]         = 0.1,
                ["MAXIMUM"]     = 99999.992,
                ["MAX"]         = 99999.992,
                ["MINIMUM"]     = 0.001,
                ["MIN"]         = 0.001,
            }
        }
        gParserTable.mParseAutoDelay =
        {
            mParse = gParserTable.ParseParameterName,
            mOptional = true,
            mNames =
            {
                ["DEFAULT"]     = 100e-6,
                ["DEF"]         = 100e-6,
                ["MAXIMUM"]     = 60,
                ["MAX"]         = 60,
                ["MINIMUM"]     = 0,
                ["MIN"]         = 0,
            }
        }
        gParserTable.mParseBlockData    = {mParse = gParserTable.ParseParameterBlockData}
        gParserTable.mParseBoolean      = {mParse = gParserTable.ParseParameterBoolean}
        gParserTable.mParseCalcElement =
        {
            mParse = gParserTable.ParseParameterName,
            mNames =
            {
                ["CALCULATE"]   = "CALC",
                ["CALC"]        = "CALC",
                ["TIME"]        = "TIME",
                ["STATUS"]      = "STAT",
                ["STAT"]        = "STAT",
            }
        }
        gParserTable.mParseCalcElementOptional =
        {
            mParse = gParserTable.ParseParameterName,
            mOptional = true,
            mNames = gParserTable.mParseCalcElement.mNames,
        }
        gParserTable.mParseCurrentLevel =
        {
            mParse = gParserTable.ParseParameterName,
            mOptional = true,
            mNames =
            {
                ["DEFAULT"]     = gOperatingBoundaries.mDefaultCurrentLevel,
                ["DEF"]         = gOperatingBoundaries.mDefaultCurrentLevel,
                ["MAXIMUM"]     = gOperatingBoundaries.mMaximumCurrentLevel,
                ["MAX"]         = gOperatingBoundaries.mMaximumCurrentLevel,
                ["MINIMUM"]     = gOperatingBoundaries.mMinimumCurrentLevel,
                ["MIN"]         = gOperatingBoundaries.mMinimumCurrentLevel,
            }
        }
        gParserTable.mParseCurrentLimit =
        {
            mParse = gParserTable.ParseParameterName,
            mOptional = true,
            mNames =
            {
                ["DEFAULT"]     = gOperatingBoundaries.mDefaultCurrentLimit,
                ["DEF"]         = gOperatingBoundaries.mDefaultCurrentLimit,
                ["MAXIMUM"]     = gOperatingBoundaries.mMaximumCurrentLimit,
                ["MAX"]         = gOperatingBoundaries.mMaximumCurrentLimit,
                ["MINIMUM"]     = -gOperatingBoundaries.mMaximumCurrentLimit,
                ["MIN"]         = -gOperatingBoundaries.mMaximumCurrentLimit,
            }
        }
        gParserTable.mParseCurrentLowRange =
        {
            mParse = gParserTable.ParseParameterName,
            mOptional = true,
            mNames =
            {
                ["DEFAULT"]     = gOperatingBoundaries.mDefaultCurrentLowRange,
                ["DEF"]         = gOperatingBoundaries.mDefaultCurrentLowRange,
                ["MAXIMUM"]     = gOperatingBoundaries.mMaximumCurrentLowRange,
                ["MAX"]         = gOperatingBoundaries.mMaximumCurrentLowRange,
                ["MINIMUM"]     = gOperatingBoundaries.mMinimumCurrentLowRange,
                ["MIN"]         = gOperatingBoundaries.mMinimumCurrentLowRange,
            }
        }
        gParserTable.mParseCurrentRange =
        {
            mParse = gParserTable.ParseParameterName,
            mOptional = true,
            mNames =
            {
                ["DEFAULT"]     = gOperatingBoundaries.mDefaultCurrentRange,
                ["DEF"]         = gOperatingBoundaries.mDefaultCurrentRange,
                ["MAXIMUM"]     = gOperatingBoundaries.mMaximumCurrentRange,
                ["MAX"]         = gOperatingBoundaries.mMaximumCurrentRange,
                ["MINIMUM"]     = gOperatingBoundaries.mMinimumCurrentRange,
                ["MIN"]         = gOperatingBoundaries.mMinimumCurrentRange,
            }
        }
        gParserTable.mParseCurrentSpan =
        {
            mParse = gParserTable.ParseParameterName,
            mOptional = true,
            mNames =
            {
                ["DEFAULT"]     = gOperatingBoundaries.mDefaultCurrentLevel,
                ["DEF"]         = gOperatingBoundaries.mDefaultCurrentLevel,
                ["MAXIMUM"]     = gOperatingBoundaries.mMaximumCurrentLevel * 2,
                ["MAX"]         = gOperatingBoundaries.mMaximumCurrentLevel * 2,
                ["MINIMUM"]     = gOperatingBoundaries.mMinimumCurrentLevel * 2,
                ["MIN"]         = gOperatingBoundaries.mMinimumCurrentLevel * 2,
            }
        }
        gParserTable.mParseDataFormat =
        {
            mParse = gParserTable.ParseParameterName,
            mNames =
            {
                ["ASCII"]       = "ASC",
                ["ASC"]         = "ASC",
                ["HEXADECIMAL"] = "HEX",
                ["HEX"]         = "HEX",
                ["OCTAL"]       = "OCT",
                ["OCT"]         = "OCT",
                ["BINARY"]      = "BIN",
                ["BIN"]         = "BIN",
            }
        }
        gParserTable.mParseDefaultZero =
        {
            mParse = gParserTable.ParseParameterName,
            mOptional = true,
            mNames =
            {
                ["DEFAULT"]     = 0,
                ["DEF"]         = 0,
            }
        }
        gParserTable.mParseDelay =
        {
            mParse = gParserTable.ParseParameterName,
            mOptional = true,
            mNames =
            {
                ["DEFAULT"]     = 0,
                ["DEF"]         = 0,
                ["MAXIMUM"]     = 9999.999,
                ["MAX"]         = 9999.999,
                ["MINIMUM"]     = 0,
                ["MIN"]         = 0,
            }
        }
        gParserTable.mParseDigits =
        {
            mParse = gParserTable.ParseParameterName,
            mOptional = true,
            mNames =
            {
                ["DEFAULT"]     = 7,
                ["DEF"]         = 7,
                ["MAXIMUM"]     = 7,
                ["MAX"]         = 7,
                ["MINIMUM"]     = 5,
                ["MIN"]         = 5,
            }
        }
        gParserTable.mParseDirection =
        {
            mParse = gParserTable.ParseParameterName,
            mNames =
            {
                ["ACCEPTOR"]    = "ACC",
                ["ACC"]         = "ACC",
                ["SOURCE"]      = "SOUR",
                ["SOUR"]        = "SOUR",
            }
        }
        gParserTable.mParseElement =
        {
            mParse = gParserTable.ParseParameterName,
            mNames =
            {
                ["VOLTAGE"]     = "VOLT",
                ["VOLT"]        = "VOLT",
                ["CURRENT"]     = "CURR",
                ["CURR"]        = "CURR",
                ["RESISTANCE"]  = "RES",
                ["RES"]         = "RES",
                ["TIME"]        = "TIME",
                ["STATUS"]      = "STAT",
                ["STAT"]        = "STAT",
            }
        }
        gParserTable.mParseElementOptional =
        {
            mParse = gParserTable.ParseParameterName,
            mOptional = true,
            mNames = gParserTable.mParseElement.mNames,
        }
        gParserTable.mParseExpression = {mParse = gParserTable.ParseParameterExpression}
        gParserTable.mParseFilterCount =
        {
            mParse = gParserTable.ParseParameterName,
            mOptional = true,
            mNames =
            {
                ["DEFAULT"]     = 10,
                ["DEF"]         = 10,
                ["MAXIMUM"]     = 100,
                ["MAX"]         = 100,
                ["MINIMUM"]     = 1,
                ["MIN"]         = 1,
            }
        }
        gParserTable.mParseFormat =
        {
            mParse = gParserTable.ParseParameterName,
            mNames =
            {
                ["ASCII"]       = "ASC",
                ["ASC"]         = "ASC",
                ["SREAL"]       = "SRE",
                ["SRE"]         = "SRE",
                ["REAL"]        = "REAL",
            }
        }
        gParserTable.mParseFunctionName =
        {
            mParse = gParserTable.ParseParameterNameString,
            mNames =
            {
                ["CURRENT"]     = "CURR",
                ["CURRENT:DC"]  = "CURR",
                ["CURR"]        = "CURR",
                ["CURR:DC"]     = "CURR",
                ["VOLTAGE"]     = "VOLT",
                ["VOLTAGE:DC"]  = "VOLT",
                ["VOLT"]        = "VOLT",
                ["VOLT:DC"]     = "VOLT",
                ["RESISTANCE"]  = "RES",
                ["RES"]         = "RES",
            }
        }
        gParserTable.mParseFunctionNameOptional =
        {
            mParse = gParserTable.ParseParameterNameString,
            mOptional = true,
            mNames = gParserTable.mParseFunctionName.mNames,
        }
        gParserTable.mParseFunctionMode =
        {
            mParse = gParserTable.ParseParameterName,
            mNames =
            {
                ["FIXED"]       = "FIX",
                ["FIX"]         = "FIX",
                ["LIST"]        = "LIST",
                ["SWEEP"]       = "SWE",
                ["SWE"]         = "SWE",
            }
        }
        gParserTable.mParseInteger      = {mParse = gParserTable.ParseParameterIntegerNRf}
        gParserTable.mParseInfinity     =
        {
            mParse = gParserTable.ParseParameterName,
            mNames =
            {
                ["INFINITE"]    = gInf,
                ["INF"]         = gInf,
                ["NNFINITE"]    = -gInf,
                ["NINF"]        = -gInf,
            }
        }
        gParserTable.mParseMinMaxDef =
        {
            mParse = gParserTable.ParseParameterName,
            mOptional = true,
            mNames =
            {
                ["DEFAULT"]     = "DEF",
                ["DEF"]         = "DEF",
                ["MAXIMUM"]     = "MAX",
                ["MAX"]         = "MAX",
                ["MINIMUM"]     = "MIN",
                ["MIN"]         = "MIN",
            }
        }
        gParserTable.mParseNDN          = {mParse = gParserTable.ParseParameterNDN}
        gParserTable.mParseNext         =
        {
            mParse = gParserTable.ParseParameterName,
            mNames =
            {
                ["NEXT"] = "NEXT",
            }
        }
        gParserTable.mParseNplc =
        {
            mParse = gParserTable.ParseParameterName,
            mOptional = true,
            mNames =
            {
                ["DEFAULT"]     = 1,
                ["DEF"]         = 1,
                ["MAXIMUM"]     = 25,
                ["MAX"]         = 25,
                ["MINIMUM"]     = .001,
                ["MIN"]         = .001,
            }
        }
        gParserTable.mParseNRf          = {mParse = gParserTable.ParseParameterNRf}
        gParserTable.mParseNRfOptional  = {mParse = gParserTable.ParseParameterNRf, mOptional = true}
        gParserTable.mParseNumList      = {mParse = gParserTable.ParseParameterNumList}
        gParserTable.mParseGeneralNegative =
        {
            mParse = gParserTable.ParseParameterName,
            mOptional = true,
            mNames =
            {
                ["DEFAULT"]     = -1,
                ["DEF"]         = -1,
                ["MAXIMUM"]     = 999.9999e18,
                ["MAX"]         = 999.9999e18,
                ["MINIMUM"]     = -999.9999e18,
                ["MIN"]         = -999.9999e18,
            }
        }
        gParserTable.mParseGeneralPositive =
        {
            mParse = gParserTable.ParseParameterName,
            mOptional = true,
            mNames =
            {
                ["DEFAULT"]     = 1,
                ["DEF"]         = 1,
                ["MAXIMUM"]     = 999.9999e18,
                ["MAX"]         = 999.9999e18,
                ["MINIMUM"]     = -999.9999e18,
                ["MIN"]         = -999.9999e18,
            }
        }
        gParserTable.mParseGeneralZero =
        {
            mParse = gParserTable.ParseParameterName,
            mOptional = true,
            mNames =
            {
                ["DEFAULT"]     = 0,
                ["DEF"]         = 0,
                ["MAXIMUM"]     = 999.9999e18,
                ["MAX"]         = 999.9999e18,
                ["MINIMUM"]     = -999.9999e18,
                ["MIN"]         = -999.9999e18,
            }
        }
        gParserTable.mParsePoints =
        {
            mParse = gParserTable.ParseParameterName,
            mOptional = true,
            mNames =
            {
                ["DEFAULT"]     = 2500,
                ["DEF"]         = 2500,
                ["MAXIMUM"]     = 2500,
                ["MAX"]         = 2500,
                ["MINIMUM"]     = 2,
                ["MIN"]         = 2,
            }
        }
        gParserTable.mParsePulseDelay =
        {
            mParse = gParserTable.ParseParameterName,
            mOptional = true,
            mNames =
            {
                ["DEFAULT"]     = 0,
                ["DEF"]         = 0,
                ["MAXIMUM"]     = 4294,
                ["MAX"]         = 4294,
                ["MINIMUM"]     = 0,
                ["MIN"]         = 0,
            }
        }
        gParserTable.mParsePulseWidth =
        {
            mParse = gParserTable.ParseParameterName,
            mOptional = true,
            mNames =
            {
                ["DEFAULT"]     = 0.00015,
                ["DEF"]         = 0.00015,
                ["MAXIMUM"]     = 0.005,
                ["MAX"]         = 0.005,
                ["MINIMUM"]     = 0.00015,
                ["MIN"]         = 0.00015,
            }
        }
        gParserTable.mParseResistanceRange =
        {
            mParse = gParserTable.ParseParameterName,
            mOptional = true,
            mNames =
            {
                ["DEFAULT"]     = gOperatingBoundaries.mDefaultResistanceRange,
                ["DEF"]         = gOperatingBoundaries.mDefaultResistanceRange,
                ["MAXIMUM"]     = gOperatingBoundaries.mMaximumResistanceRange,
                ["MAX"]         = gOperatingBoundaries.mMaximumResistanceRange,
                --["MINIMUM"]     = gOperatingBoundaries.mMinimumResistanceRange,
                --["MIN"]         = gOperatingBoundaries.mMinimumResistanceRange,
                ["MINIMUM"]     = 0,
                ["MIN"]         = 0,
            }
        }
        gParserTable.mParseSMNames =
        {
            mParse = gParserTable.ParseParameterName,
            mOptional = true,
            mNames =
            {
                ["DEFAULT"]     = 1,
                ["DEF"]         = 1,
                ["MAXIMUM"]     = 100,
                ["MAX"]         = 100,
                ["MINIMUM"]     = 1,
                ["MIN"]         = 1,
            }
        }
        gParserTable.mParseString       = {mParse = gParserTable.ParseParameterString}
        gParserTable.mParseTracePoints =
        {
            mParse = gParserTable.ParseParameterName,
            mOptional = true,
            mNames =
            {
                ["DEFAULT"]     = 100,
                ["DEF"]         = 100,
                ["MAXIMUM"]     = 2500,
                ["MAX"]         = 2500,
                ["MINIMUM"]     = 1,
                ["MIN"]         = 1,
            }
        }
        gParserTable.mParseTriggerCount =
        {
            mParse = gParserTable.ParseParameterName,
            mOptional = true,
            mNames =
            {
                ["DEFAULT"]     = 1,
                ["DEF"]         = 1,
                ["MAXIMUM"]     = 2500,
                ["MAX"]         = 2500,
                ["MINIMUM"]     = 1,
                ["MIN"]         = 1,
            }
        }
        gParserTable.mParseTriggerDelay =
        {
            mParse = gParserTable.ParseParameterName,
            mOptional = true,
            mNames =
            {
                ["DEFAULT"]     = 0,
                ["DEF"]         = 0,
                ["MAXIMUM"]     = 999.99988,
                ["MAX"]         = 999.99988,
                ["MINIMUM"]     = 0,
                ["MIN"]         = 0,
            }
        }
        gParserTable.mParseTriggerEvent =
        {
            mParse = gParserTable.ParseParameterName,
            mNames =
            {
                ["NONE"]        = "NONE",
                ["SOURCE"]      = "SOUR",
                ["SOUR"]        = "SOUR",
                ["TENT"]        = "TENT",
                ["SENSE"]       = "SENS",
                ["SENS"]        = "SENS",
                ["DELAY"]       = "DEL",
                ["DEL"]         = "DEL",
            }
        }
        gParserTable.mParseTriggerEventOptional =
        {
            mParse = gParserTable.ParseParameterName,
            mOptional = true,
            mNames =gParserTable.mParseTriggerEvent.mNames,
        }
        gParserTable.mParseUpDown =
        {
            mParse = gParserTable.ParseParameterName,
            mNames =
            {
                ["DOWN"]        = "DOWN",
                ["UP"]          = "UP",
            }
        }
        gParserTable.mParseVoltageLevel =
        {
            mParse = gParserTable.ParseParameterName,
            mOptional = true,
            mNames =
            {
                ["DEFAULT"]     = gOperatingBoundaries.mDefaultVoltageLevel,
                ["DEF"]         = gOperatingBoundaries.mDefaultVoltageLevel,
                ["MAXIMUM"]     = gOperatingBoundaries.mMaximumVoltageLevel,
                ["MAX"]         = gOperatingBoundaries.mMaximumVoltageLevel,
                ["MINIMUM"]     = gOperatingBoundaries.mMinimumVoltageLevel,
                ["MIN"]         = gOperatingBoundaries.mMinimumVoltageLevel,
            }
        }
        gParserTable.mParseVoltageLimit =
        {
            mParse = gParserTable.ParseParameterName,
            mOptional = true,
            mNames =
            {
                ["DEFAULT"]     = gOperatingBoundaries.mDefaultVoltageLimit,
                ["DEF"]         = gOperatingBoundaries.mDefaultVoltageLimit,
                ["MAXIMUM"]     = gOperatingBoundaries.mMaximumVoltageLimit,
                ["MAX"]         = gOperatingBoundaries.mMaximumVoltageLimit,
                ["MINIMUM"]     = -gOperatingBoundaries.mMaximumVoltageLimit,
                ["MIN"]         = -gOperatingBoundaries.mMaximumVoltageLimit,
            }
        }
        gParserTable.mParseVoltageLowRange =
        {
            mParse = gParserTable.ParseParameterName,
            mOptional = true,
            mNames =
            {
                ["DEFAULT"]     = gOperatingBoundaries.mDefaultVoltageLowRange,
                ["DEF"]         = gOperatingBoundaries.mDefaultVoltageLowRange,
                ["MAXIMUM"]     = gOperatingBoundaries.mMaximumVoltageLowRange,
                ["MAX"]         = gOperatingBoundaries.mMaximumVoltageLowRange,
                ["MINIMUM"]     = gOperatingBoundaries.mMinimumVoltageLowRange,
                ["MIN"]         = gOperatingBoundaries.mMinimumVoltageLowRange,
            }
        }
        gParserTable.mParseVoltageRange =
        {
            mParse = gParserTable.ParseParameterName,
            mOptional = true,
            mNames =
            {
                ["DEFAULT"]     = gOperatingBoundaries.mDefaultVoltageRange,
                ["DEF"]         = gOperatingBoundaries.mDefaultVoltageRange,
                ["MAXIMUM"]     = gOperatingBoundaries.mMaximumVoltageRange,
                ["MAX"]         = gOperatingBoundaries.mMaximumVoltageRange,
                ["MINIMUM"]     = gOperatingBoundaries.mMinimumVoltageRange,
                ["MIN"]         = gOperatingBoundaries.mMinimumVoltageRange,
            }
        }
        gParserTable.mParseVoltageSpan =
        {
            mParse = gParserTable.ParseParameterName,
            mOptional = true,
            mNames =
            {
                ["DEFAULT"]     = gOperatingBoundaries.mDefaultVoltageLevel,
                ["DEF"]         = gOperatingBoundaries.mDefaultVoltageLevel,
                ["MAXIMUM"]     = gOperatingBoundaries.mMaximumVoltageLevel * 2,
                ["MAX"]         = gOperatingBoundaries.mMaximumVoltageLevel * 2,
                ["MINIMUM"]     = gOperatingBoundaries.mMinimumVoltageLevel * 2,
                ["MIN"]         = gOperatingBoundaries.mMinimumVoltageLevel * 2,
            }
        }
        
        gParserTable.mAny           = {gParserTable.mParseAny}
        gParserTable.mBoolean       = {gParserTable.mParseBoolean}
        gParserTable.mCurrentLevel =
        {
            {
                mParse = gParserTable.ParseParameterChoice,
                mData =
                {
                    gParserTable.mParseNRf,
                    gParserTable.mParseCurrentLevel,
                    gParserTable.mParseInfinity,
                }
            }
        }
        gParserTable.mCurrentLevelQuery = {gParserTable.mParseCurrentLevel}
        gParserTable.mCurrentRange =
        {
            {
                mParse = gParserTable.ParseParameterChoice,
                mData =
                {
                    gParserTable.mParseNRf,
                    gParserTable.mParseCurrentRange,
                    gParserTable.mParseUpDown,
                    gParserTable.mParseInfinity,
                }
            }
        }
        gParserTable.mCurrentRangeQuery = {gParserTable.mParseCurrentRange}
        gParserTable.mDataFormat    = {gParserTable.mParseDataFormat}
        gParserTable.mDelay         =
        {
            {
                mParse = gParserTable.ParseParameterChoice,
                mData =
                {
                    gParserTable.mParseNRf,
                    gParserTable.mParseDelay,
                    gParserTable.mParseInfinity,
                }
            }
        }
        gParserTable.mDisplayData =
        {
            {
                mParse = gParserTable.ParseParameterChoice,
                mData =
                {
                    gParserTable.mParseString,
                    gParserTable.mParseBlockData,
                }
            }
        }
        gParserTable.mExpression    = {gParserTable.mParseExpression}
        gParserTable.mFunctionList =
        {
            gParserTable.mParseFunctionName,
            gParserTable.mParseFunctionNameOptional,
            gParserTable.mParseFunctionNameOptional,
            gParserTable.mParseFunctionNameOptional,
        }
        gParserTable.mFunctionMode  = {gParserTable.mParseFunctionMode}
        gParserTable.mInteger       = {gParserTable.mParseInteger}
        gParserTable.mIntegerMinMaxDef =
        {
            {
                mParse = gParserTable.ParseParameterChoice,
                mData =
                {
                    gParserTable.mParseInteger,
                    gParserTable.mParseMinMaxDef,
                    gParserTable.mParseInfinity,
                }
            }
        }
        gParserTable.mIntegerOrInf  =
        {
            {
                mParse = gParserTable.ParseParameterChoice,
                mData =
                {
                    gParserTable.mParseInteger,
                    gParserTable.mParseInfinity,
                }
            }
        }
        gParserTable.mMinMaxDef     = {gParserTable.mParseMinMaxDef}
        gParserTable.mNDN           = {gParserTable.mParseNDN}
        gParserTable.mNRf           = {gParserTable.mParseNRf}
        gParserTable.mNRfMinMaxDef =
        {
            {
                mParse = gParserTable.ParseParameterChoice,
                mData =
                {
                    gParserTable.mParseNRf,
                    gParserTable.mParseMinMaxDef,
                    gParserTable.mParseInfinity,
                }
            }
        }
        gParserTable.mNumList         = {gParserTable.mParseNumList}
        gParserTable.mGeneralNegative =
        {
            {
                mParse = gParserTable.ParseParameterChoice,
                mData =
                {
                    gParserTable.mParseNRf,
                    gParserTable.mParseGeneralNegative,
                    gParserTable.mParseInfinity,
                }
            }
        }
        gParserTable.mGeneralNegativeQuery = {gParserTable.mParseGeneralNegative}
        gParserTable.mGeneralPositive =
        {
            {
                mParse = gParserTable.ParseParameterChoice,
                mData =
                {
                    gParserTable.mParseNRf,
                    gParserTable.mParseGeneralPositive,
                    gParserTable.mParseInfinity,
                }
            }
        }
        gParserTable.mGeneralPositiveQuery = {gParserTable.mParseGeneralPositive}
        gParserTable.mGeneralZero =
        {
            {
                mParse = gParserTable.ParseParameterChoice,
                mData =
                {
                    gParserTable.mParseNRf,
                    gParserTable.mParseGeneralZero,
                    gParserTable.mParseInfinity,
                }
            }
        }
        gParserTable.mGeneralZeroQuery = {gParserTable.mParseGeneralZero}
        gParserTable.mSMIndex       =
        {
            {
                mParse = gParserTable.ParseParameterChoice,
                mData =
                {
                    gParserTable.mParseInteger,
                    gParserTable.mParseSMNames,
                    gParserTable.mParseInfinity,
                }
            }
        }
        gParserTable.mSMIndexQuery  = {gParserTable.mParseSMNames}
        gParserTable.mSMLocation    =
        {
            {
                mParse = gParserTable.ParseParameterChoice,
                mData =
                {
                    gParserTable.mParseInteger,
                    gParserTable.mParseNext,
                }
            }
        }
        gParserTable.mSourceList = {gParserTable.mParseNRf}
        for lIndex = 2, 100 do
            gParserTable.mSourceList[lIndex] = gParserTable.mParseNRfOptional
        end
        gParserTable.mString        = {gParserTable.mParseString}
        gParserTable.mTriggerCount =
        {
            {
                mParse = gParserTable.ParseParameterChoice,
                mData =
                {
                    gParserTable.mParseInteger,
                    gParserTable.mParseTriggerCount,
                    gParserTable.mParseInfinity,
                }
            }
        }
        gParserTable.mTriggerCountQuery = {gParserTable.mParseTriggerCount}
        gParserTable.mTriggerDirection = {gParserTable.mParseDirection}
        gParserTable.mVoltageLevel =
        {
            {
                mParse = gParserTable.ParseParameterChoice,
                mData =
                {
                    gParserTable.mParseNRf,
                    gParserTable.mParseVoltageLevel,
                    gParserTable.mParseInfinity,
                }
            }
        }
        gParserTable.mVoltageLevelQuery = {gParserTable.mParseVoltageLevel}
        gParserTable.mVoltageRange =
        {
            {
                mParse = gParserTable.ParseParameterChoice,
                mData =
                {
                    gParserTable.mParseNRf,
                    gParserTable.mParseVoltageRange,
                    gParserTable.mParseUpDown,
                    gParserTable.mParseInfinity,
                }
            }
        }
        gParserTable.mVoltageRangeQuery = {gParserTable.mParseVoltageRange}
        
        ------------------------------------------------------------------------------
        --
        --  Parse4882
        --
        --  Parse a 488.2 command.  This function will break a command down into
        --  component parts.  It will return a structure with the component parts
        --  and the number of characters from the input string that were used.
        --
        --  The parsed command is stored in a ParseInfo structure:
        --
        ------------------------------------------------------------------------------
        
        Parse4882 = function (lTextMixedCase, lText, lStart)
            local lCommand = {}
            local lCommandNode
            local lLength = string.len(lText)
            local lCharCode
            local lIndex
            local lIndex2
            local lIndex3
            local lCount
            local lHeader
        
            -- This routine requires that there is no leading whitespace ahead of the
            -- command to parse. Replace the initialization of lIndex with the
            -- commented out initialization to have this routine skip the leading
            -- whitespace. It is not done now for better efficiency.
            lIndex = lStart
            -- Skip leading whitespace.
            -- lIndex = string.find(lText, lNonWhitespace, lStart) or (lLength + 1)
        
            -- Parse headers
            -- Determine root of command
            lCharCode = string.byte(lText, lIndex)
            if lCharCode == gCharCodes.mColon then
                -- Command rooted at top of hierarchy.
                gCurrentRoot = gCommandTree
                lIndex = lIndex + 1
                lCharCode = string.byte(lText, lIndex)
            end
            if lCharCode == gCharCodes.mStar then
                -- Command is a common command.
                lIndex2 = string.find(lText, gNonProgMnemonic, lIndex + 1) or lLength + 1
                lHeader = string.sub(lText, lIndex, lIndex2 - 1)
                gCurrentRoot = gCommandTree
                lCommandNode = gCommandTree[lHeader]
                if lCommandNode then
                    lIndex = lIndex2
                else
                    -- Unrecognized header (could not find a match)
                    lCommand.mError = -113
                    lIndex = lLength + 1
                end
            else
                lCommandNode = gCurrentRoot
                while lIndex <= lLength do
                    lIndex2 = string.find(lText, gNonProgMnemonic, lIndex) or lLength + 1
                    lHeader = string.sub(lText, lIndex, lIndex2 - 1)
                    if lCommandNode[lHeader] then
                        gCurrentRoot = lCommandNode
                        lCommandNode = lCommandNode[lHeader]
        
                        lCharCode = string.byte(lText, lIndex2)
                        if lCharCode ~= gCharCodes.mColon then
                            lIndex = lIndex2
                            break
                        else
                            lIndex = lIndex2 + 1
                        end
                    else
                        if lCommandNode == gCurrentRoot and string.len(lHeader) == 0 then
                            -- Empty command. Ignore it.
                            lCommandNode = gSpecialCommands["$Empty"]
                        else
                            -- Unrecognized header (could not find a match)
                            lCommand.mError = -113
                            lIndex = lLength + 1
                        end
                        break
                    end
                end
            end
            if lCommandNode then
                lCommand.mCommandNode = lCommandNode
                lCharCode = string.byte(lText, lIndex)
                if lCharCode == gCharCodes.mQuestion then
                    -- This is a query
                    lCommand.mCommand = lCommandNode.mQuery
                    lIndex = lIndex + 1
                    lCharCode = string.byte(lText, lIndex)
                else
                    lCommand.mCommand = lCommandNode.mCommand
                end
                -- Here we expect a whitespace character, a semicolon, or the end of string
                -- to be at the parse index.
                if lIndex <= lLength and lCharCode ~= gCharCodes.mSemicolon then
                    if string.find(lText, "^%s", lIndex) ~= lIndex then
                        -- ERROR! invalid <PROGRAM HEADER SEPARATOR>
                        lCommand.mError = -111
                        lIndex = lLength + 1
                    end
                end
        
                -- Parse parameters
                lCount = 0
                lCommand.mParameters = {}
                while lIndex <= lLength do
                    -- Skip leading whitespace
                    lIndex = string.find(lText, gNonWhitespace, lIndex) or lLength + 1
                    if lIndex <= lLength then
                        lCharCode = string.byte(lText, lIndex)
                        if lCharCode == gCharCodes.mSemicolon then
                            -- End of command found
                            lIndex2, lIndex3 = string.find(lText, ";%s*", lIndex)
                            lIndex = lIndex3 + 1
                            break
                        end
        
                        -- This must be a parameter
                        lCount = lCount + 1
                        if lCharCode == gCharCodes.mSingleQuote or lCharCode == gCharCodes.mDoubleQuote then
                            lCommand.mParameters[lCount], lIndex = ParseString(lTextMixedCase, lIndex)
                            if lIndex <= lLength then
                                lIndex2, lIndex3 = string.find(lText, "^%s*[,;]", lIndex)
                                if lIndex2 then
                                    -- Skip whitespace and point to comma or semicolon
                                    lIndex = lIndex3
                                else
                                    lIndex2, lIndex3 = string.find(lText, "^%s*$", lIndex)
                                    if not lIndex2 then
                                        -- Text after string (or parse error in string)
                                        lCommand.mError = -150
                                        break
                                    end
                                    lIndex = lLength + 1
                                end
                            end
                        elseif lCharCode == gCharCodes.mHash then
                            lCharCode = string.byte(lText, lIndex + 1)
                            if lCharCode == gCharCodes.mH then
                                -- Hexadecimal encoding
                                lIndex2, lIndex3 = string.find(lText, "^%x*", lIndex + 2)
                                if lIndex2 then
                                    lCommand.mParameters[lCount] = string.sub(lText, lIndex, lIndex3)
                                    lIndex = lIndex3 + 1
                                else
                                    lCommand.mError = -102
                                    break
                                end
                            elseif lCharCode == gCharCodes.mB then
                                -- Binary encoding
                                lIndex2, lIndex3 = string.find(lText, "^[01]*", lIndex + 2)
                                if lIndex2 then
                                    lCommand.mParameters[lCount] = string.sub(lText, lIndex, lIndex3)
                                    lIndex = lIndex3 + 1
                                else
                                    lCommand.mError = -102
                                    break
                                end
                            elseif lCharCode == gCharCodes.mQ then
                                -- Octal encoding
                                lIndex2, lIndex3 = string.find(lText, "^[01234567]*", lIndex + 2)
                                if lIndex2 then
                                    lCommand.mParameters[lCount] = string.sub(lText, lIndex, lIndex3)
                                    lIndex = lIndex3 + 1
                                else
                                    lCommand.mError = -102
                                    break
                                end
                            elseif lCharCode == gCharCodes.mZero then
                                -- Indefinite length arbitrary block data
                                if gParserState.mLastChar == gCharCodes.mNewLine then
                                    -- Don't include the terminating linefeed
                                    lCommand.mParameters[lCount] = string.sub(lTextMixedCase, lIndex, -2)
                                else
                                    lCommand.mParameters[lCount] = string.sub(lTextMixedCase, lIndex)
                                end
                                lIndex = lLength + 1
                                break
                            elseif lCharCode >= gCharCodes.mOne and lCharCode <= gCharCodes.mNine then
                                -- Definite length arbitrary block data
                                lIndex2 = ParseBlockLength(lText, lIndex + 1)
                                if lIndex2 > lIndex + 1 then
                                    lCommand.mParameters[lCount] = string.sub(lTextMixedCase, lIndex, lIndex2)
                                    lIndex = lIndex2 + 1
                                else
                                    lCommand.mError = -102
                                    break
                                end
                                if lIndex <= lLength then
                                    lIndex2, lIndex3 = string.find(lText, "^%s*[,;]", lIndex)
                                    if lIndex2 then
                                        -- Skip whitespace and point to comma or semicolon
                                        lIndex = lIndex3
                                    else
                                        lIndex2, lIndex3 = string.find(lText, "^%s*$", lIndex)
                                        if not lIndex2 then
                                            -- more data after block data
                                            lCommand.mError = -160
                                        end
                                        lIndex = lLength + 1
                                    end
                                end
                            else
                                -- Invalid (either bad code or end of string after #)
                                lCommand.mError = -102
                                break
                            end
                        elseif lCharCode == gCharCodes.mParenLeft then
                            -- Expression data
                            lCommand.mParameters[lCount], lIndex = ParseExpression(lText, lIndex)
                            if lIndex <= lLength then
                                lIndex2, lIndex3 = string.find(lText, "^%s*[,;]", lIndex)
                                if lIndex2 then
                                    -- Skip whitespace and point to comma or semicolon
                                    lIndex = lIndex3
                                else
                                    lIndex2, lIndex3 = string.find(lText, "^%s*$", lIndex)
                                    if not lIndex2 then
                                       gErrorQueue.Add(-170)
                                    end
                                    lIndex = lLength + 1
                                end
                            end
                        else
                            lIndex2, lIndex3, lCommand.mParameters[lCount] = string.find(lText, "([^,;]-)%s*[,;]", lIndex)
                            if lIndex2 then
                                lIndex = lIndex3
                            else
                                lIndex2, lIndex3, lCommand.mParameters[lCount] = string.find(lText, "(.-)%s*$", lIndex)
                                lIndex = lLength + 1
                            end
                        end
                        if lIndex <= lLength then
                            lCharCode = string.byte(lText, lIndex)
                            if lCharCode == gCharCodes.mComma then
                                lIndex = lIndex + 1
                            end
                        end
                    end
                end
            end
        
            return lCommand, lIndex - lStart
        end
        
        ------------------------------------------------------------------------------
        --
        --  ParseNextMessage
        --
        --  Fully parse the next command in the current command message. It will
        --  return the next command. It will return nil if there are no more commands
        --  in the current message. If there are parse errors, the mParseInfo.mError
        --  member will be set to the error code of the error.
        --
        --  This function will update the current position based on the number of
        --  characters used. If all the characters are used, the position will be one
        --  past the end of the string.
        --
        ------------------------------------------------------------------------------
        
        local ParseNextCommand = function ()
            local lParseInfo
            local lCount
            local lCommand
            local lExpectedParameters
        
            lParseInfo, lCount = Parse4882(gParserState.mCurrentText, gParserState.mCurrentTextUpper, gParserState.mCurrentPosition)
            gParserState.mCurrentPosition = gParserState.mCurrentPosition + lCount
            if gParserState.mCurrentPosition > string.len(gParserState.mCurrentText) then
                gParserState.mCurrentText = nil
            end
            if lParseInfo then
                if lParseInfo.mError then
                    gParserState.mCurrentText = nil
                else
                    lCommand = lParseInfo.mCommand
                    if lCommand then
                        -- Iterate over the parameters array and match parameters
                        -- to parser functions.
                        lExpectedParameters = lCommand.mParameters
                        if lExpectedParameters then
                            local lActualParameters = lParseInfo.mParameters
                            local lIndex = 1
                            local lError
                            local lExpected
                            local lActual
        
                            lExpected = lExpectedParameters[lIndex]
                            while lExpected do
                                lActual = lActualParameters[lIndex]
                                if lActual then
                                    -- Check parameter
                                    lActualParameters[lIndex], lError = lExpected.mParse(lActual, lExpected)
                                    if lError then
                                        lParseInfo.mError = lError
                                        break
                                    end
                                else
                                    if lExpected.mOptional then
                                        if lExpected.mDefault then
                                            -- Use default
                                            lActualParameters[lIndex] = lExpected.mDefault
                                        else
                                            -- Stop scanning when remaining parameters
                                            -- are missing and have no default.
                                            break
                                        end
                                    else
                                        -- Missing parameter
                                        lParseInfo.mError = -109
                                        break
                                    end
                                end
                                lIndex = lIndex + 1
                                lExpected = lExpectedParameters[lIndex]
                            end
                            if lActualParameters[lIndex] and not lError then
                                -- Too many parameters
                                lParseInfo.mError = -108
                            end
                        else
                            -- No parameters were expected
                            if lParseInfo.mParameters[1] then
                                lParseInfo.mError = -108
                            end
                        end
                    else
                        -- Query/Command mismatch
                        lParseInfo.mError = -113
                    end
                end
            end
        
            return lParseInfo
        end
        
        ------------------------------------------------------------------------------
        --
        --  GetNextCommand
        --
        --  Load the next command from the message queue. This could be a decoded
        --  message or the next command from a parsable message.
        --
        ------------------------------------------------------------------------------
        
        local GetNextCommand = function ()
            local lMessage
            local lText
        
            if gParserState.mCurrentText then
                gParserState.mNextCommand = ParseNextCommand()
                return
            end
        
            -- Make sure previous message was properly terminated.
            gRemoteComm.terminatemessage()
        
            if gParserState.mNextMessage then
                lMessage = gParserState.mNextMessage
        
                -- Remove current message from queue
                gParserState.mNextMessage = lMessage.mNext
                if not gParserState.mNextMessage then
                    gParserState.mLastMessage = nil
                end
        
                -- Decode the message
                if lMessage.mType == gRemoteComm.types.MESSAGE then
                    lText = lMessage.mMessage
                    if gParserState.mPartialMessage then
                        lText = gParserState.mPartialMessage .. lText
                        gParserState.mPartialMessage = nil
                    end
                    -- Replace all control characters with spaces (Note: this may not work
                    -- for products that accept/expect control characters in quoted strings.)
                    gParserState.mLastChar = string.byte(lText, -1)
                    lText = string.gsub(lText, "%c", " ")
                    gParserState.mCurrentText = lText
                    lText = string.upper(lText)
                    gParserState.mCurrentTextUpper = lText
                    -- For efficiency, leading/trailing whitespace is removed here rather than
                    -- in the parse routine.
                    gParserState.mCurrentPosition = string.find(lText, gNonWhitespace, 1) or (string.len(lText) + 1)
        
                    gCurrentRoot = gCommandTree
                    gParserState.mNextCommand = ParseNextCommand()
                elseif gSpecialCommands[lMessage.mType] then
                    local lCommand = {}            
                    lCommand.mCommandNode = gSpecialCommands[lMessage.mType]
                    lCommand.mCommand = gSpecialCommands[lMessage.mType].mCommand
        
                    gParserState.mNextCommand = lCommand
                elseif lMessage.mType == gRemoteComm.types.PARTIAL_MESSAGE then
                    if gParserState.mPartialMessage then
                        gParserState.mPartialMessage = gParserState.mPartialMessage .. lMessage.mMessage
                    else
                        gParserState.mPartialMessage = lMessage.mMessage
                    end
                end
                -- Handle TRUNCATED_MESSAGE
            end
        end
        
        --============================================================================
        --
        --  Execution functions
        --
        --============================================================================
        ------------------------------------------------------------------------------
        -- script initialization functions
        --[[
            These functions are used to initialize and setup the script
        --]]
        -----------------------------------------------------------------------------
        
        local Init = {}
        local ResetDefaults
        local ResetScriptVariables
        local ResetSmuSettings
        
        ------------------------------------------------------------------------------
        --
        --  Initialize2400
        --
        --  Prepare the instrument hardware for 2400 emulation. This function must
        --  be called before using Execute2400 or after changing the hardware state
        --  between invokations of Engine2400.
        --
        ------------------------------------------------------------------------------
        
        Initialize2400 = function ()
            gInitialized = true
            reset()
            ResetSmuSettings()
            format.byteorder = format.NORMAL
        end
        
        ------------------------------------------------------------------------------
        --
        --  ExecuteCommand
        --
        --  Execute a command or log the parser error for the command if there was
        --  one.
        --
        ------------------------------------------------------------------------------
        
        local ExecuteCommand  = function (lParseInfo)
            if lParseInfo.mError then
                if type(lParseInfo.mError) == "table" then
                    for lIndex, lError in ipairs(lParseInfo.mError) do
                        gErrorQueue.Add(lError)
                    end
                else
                    gErrorQueue.Add(lParseInfo.mError)
                end
            elseif lParseInfo.mCommand then
                lParseInfo.mCommand.mExecute(lParseInfo.mParameters)
            end
            
            gRemoteComm.terminateunit()
        end
        
        ------------------------------------------------------------------------------
        --
        --  PriorityExecute
        --
        --  Peek ahead for the next command and execute it if it has priority (one
        --  designed to run while a sweep is in progress).
        --
        ------------------------------------------------------------------------------
        
        local PriorityExecute = function ()
        
            if gEngineMode then
                GetNewMessage()
            end
        
            if gPrintEnable or gParserState.mNextCommand then
                -- The only time this will be true is if a previous call to this
                -- function found a non-priority command that it did not execute.
                return
            end
                
            GetNextCommand()
            if gParserState.mNextCommand then
                local lCommand = gParserState.mNextCommand
        
                if lCommand.mError or lCommand.mCommand.mPriority then
                    gParserState.mNextCommand = nil
                    ExecuteCommand(lCommand)
                end
            end
        end
        
        ------------------------------------------------------------------------------
        --
        --  ExecuteMessage
        --
        --  Execute the next SCPI command string in the parser queue.
        --
        ------------------------------------------------------------------------------
        
        local ExecuteMessage = function ()
            local lCommand
        
            while gParserState.mNextCommand or gParserState.mCurrentText do
                if gParserState.mNextCommand then
                    lCommand = gParserState.mNextCommand
                    gParserState.mNextCommand = nil
                else
                    lCommand = ParseNextCommand()
                end
        
                if lCommand then
                    ExecuteCommand(lCommand)
                end
            end
            gRemoteComm.terminatemessage()
        end
        
        ------------------------------------------------------------------------------
        --
        --  Execute2400
        --
        --  Execute a 2400 SCPI command string.
        --
        ------------------------------------------------------------------------------
        
        Execute2400 = function (lCommandMessage)
            if type(lCommandMessage) == "string" then
                AddMessage(lCommandMessage, gRemoteComm.types.MESSAGE, 0)
                GetNextCommand()
                ExecuteMessage()
            else
                print("$DIAG$ Can only execute a string message")
            end
        end
        
        ------------------------------------------------------------------------------
        --
        --  Engine2400
        --
        --  Intercept command interface communication and process commands as 2400
        --  SCPI command messages.
        --
        ------------------------------------------------------------------------------
        local UpdateStatusModel
        
        Engine2400 = function ()
            if not gInitialized then
                Initialize2400()
            end
            -- override status register
            gRemoteCommStatus.override = 175
            gEngineMode = true
            display.screen = display.SMUA
            gRemoteComm.intercept = gRemoteComm.ALL
            gOrigin = nil
            GetNewMessage = GetFirstCommandMessage
            while true do
                GetNewMessage()
                if gParserState.mNextMessage then
                    GetNextCommand()
                    ExecuteMessage()
                else
                    -- Update status model here.
                    UpdateStatusModel()
                    delay(0.0003)
                end
                --collectgarbage()
            end
            gRemoteComm.intercept = gRemoteComm.DISABLE
            gEngineMode = false
        end
        
        --============================================================================
        --
        --  Utility functions
        --
        --============================================================================
        
        -- Status model registers
        local measStatus      = {mCondition = 0, mEvent = 0, mEventEnable = 0, mSummary = 1}
        local quesStatus      = {mCondition = 0, mEvent = 0, mEventEnable = 0, mSummary = 4}
        local operStatus      = {mCondition = 0, mEvent = 0, mEventEnable = 0, mSummary = 8}
        local standardStatus  = {                mEvent = 0, mEventEnable = 0, mSummary = 6}
        
        local StatusModel = {mStatus = 0}
        
        StatusModel.SetCondition = function (lRegister, lBit)
            local lCondition = bit.set(lRegister.mCondition, lBit)
            if lCondition ~= lRegister.mCondition then
                lRegister.mCondition = lCondition
                StatusModel.SetEvent(lRegister, lBit)
            end
        end
        
        StatusModel.ClearCondition = function (lRegister, lBit)
            lRegister.mCondition = bit.clear(lRegister.mCondition, lBit)
        end
        
        StatusModel.SetEvent = function (lRegister, lBit)
            local lEvent = bit.set(lRegister.mEvent, lBit)
            if lEvent ~= lRegister.mEvent then
                lRegister.mEvent = lEvent
                if bit.bitand(lEvent, lRegister.mEventEnable) > 0 then
                    StatusModel.SetSummary(lRegister.mSummary)
                end
            end
        end
        
        StatusModel.SetEvents = function (lRegister, lMask)
            local lEvent = bit.bitor(lRegister.mEvent, lMask)
            if lEvent ~= lRegister.mEvent then
                lRegister.mEvent = lEvent
                if bit.bitand(lEvent, lRegister.mEventEnable) > 0 then
                    StatusModel.SetSummary(lRegister.mSummary)
                end
            end
        end
        
        StatusModel.ClearEvent = function (lRegister)
            lRegister.mEvent = 0
            StatusModel.ClearSummary(lRegister.mSummary)
        end
        
        StatusModel.SetEnable = function (lRegister, lValue)
            lRegister.mEventEnable = lValue
            if bit.bitand(lRegister.mEvent, lRegister.mEventEnable) > 0 then
                StatusModel.SetSummary(lRegister.mSummary)
            else
                StatusModel.ClearSummary(lRegister.mSummary)
            end
        end
        
        StatusModel.SetSummary = function (lBit)
            local lStatus = bit.set(StatusModel.mStatus, lBit)
            if lStatus ~= StatusModel.mStatus then
                StatusModel.mStatus = lStatus
                gRemoteCommStatus.condition = lStatus
            end
        end
        
        StatusModel.ClearSummary = function (lBit)
            local lStatus = bit.clear(StatusModel.mStatus, lBit)
            if lStatus ~= StatusModel.mStatus then
                StatusModel.mStatus = lStatus
                gRemoteCommStatus.condition = lStatus
            end
        end
        
        ------------------------------------------------------------------------------
        --
        --  UpdateStatusModel
        --
        ------------------------------------------------------------------------------
        
        UpdateStatusModel = function ()
            local lEvents
        
            -- Monitor for overtemperature condition
            if bit.test(gAccessors.mStatusOvertempCondition(), 2) then
                -- Measurement Event Register Bit 13(12 on 2400), Over Temperature
                StatusModel.SetCondition(measStatus, 13)
                gErrorQueue.Add(809)
            else
                StatusModel.ClearCondition(measStatus, 13)
            end
        
            -- Monitor for Output Enable (OE), Interlock (INT) condition
            if gAccessors.mSourceOutputEnableAction() == smua.OE_OUTPUT_OFF then
                if bit.test(gAccessors.mStatusMeasurementCondition(), 12) then
                    -- Measurement Event Register Bit 12(11 on 2400), Output Enable (OE), Interlock (INT) condition
                    StatusModel.SetCondition(measStatus, 12)
                else
                    StatusModel.ClearCondition(measStatus, 12)
                    local lError = errorqueue.next()
                    if lError == 5041 or lError == 802 then
                        gErrorQueue.Add(802)
                    end
                end
            end
        
            -- Update Standard Event Register
            -- (OPC (Bit 1), URQ (Bit 6), PON (Bit 7) bits are directly read from 2600 status model)
            lEvents = gAccessors.mGetStatusStandardEvent()
            if lEvents > 0 then
                StatusModel.SetEvents(standardStatus, bit.bitand(lEvents, 193))
            end
            
        end
        
        ------------------------------------------------------------------------------
        --
        --  WaitForEvent
        --
        --  Process command input (so we can look for triggers and aborts) while
        --  waiting for an event. This function takes a function argument that must
        --  return true when the event is detected. This function will loop until the
        --  given function returns true.
        --
        ------------------------------------------------------------------------------
        
        local WaitForEvent = function (lCheck)
            while true do
                PriorityExecute()
                if lCheck() then
                    return
                end
                UpdateStatusModel()
            end
        end
        
        ------------------------------------------------------------------------------
        --
        --  Configure2400
        --
        --  Configure the emulation to run at power on (or not). This function also
        --  provides a method to retrieve the build number for identification
        --  purposes.
        --
        ------------------------------------------------------------------------------
        
        Configure2400 = function ()
            local lSubMenu = display.menu("Configure 2400 Mode", "RunAtPowerON DisplayErrors DeleteScript Version")
            
            if lSubMenu == "RunAtPowerON" then
                local lAutoRun = display.menu("AutoRun At Power ON", "ENABLE DISABLE")
                if lAutoRun == "ENABLE" then
                    userstring.add("AutoRun2400", "true")
                elseif lAutoRun == "DISABLE" then
                    if gAutoRunEnable then
                        userstring.delete("AutoRun2400")
                    end
                end
            elseif lSubMenu == "DisplayErrors" then
                local lDisplay = display.menu("Display Errors?", "YES NO")
                if lDisplay == "YES" then
                    gDisplayErrors = true
                elseif lDisplay == "NO" then
                    gDisplayErrors = false
                end        
            elseif lSubMenu == "DeleteScript" then
                local lDelete = display.menu("Delete Persona2400?", "YES NO")
                if lDelete == "YES" then
                    if gAutoRunEnable then
                        userstring.delete("AutoRun2400")
                    end
                    script.delete("Persona2400")
                    Persona2400 = nil
                    display.loadmenu.delete("Run2400")
                    display.loadmenu.delete("Configure2400")
                    display.clear()
                    display.setcursor(1, 1)
                    display.settext("$BRestart The Unit")
                    display.setcursor(2, 1)
                    display.settext("to finish Persona2400 Deletion")
                end        
            elseif lSubMenu == "Version" then
                local lVersion = "$Change: 76212 $"
                local lIndex1, lIndex2 = string.find(lVersion, "%d+")
                lVersion = string.sub(lVersion, lIndex1, lIndex2)
                display.clear()
                display.setcursor(1, 1)
                display.settext("Build#: " .. lVersion)
            end
        end
        
        --============================================================================
        --
        -- Calc subsystem expression parsers
        --
        -- These functions implement a recursive descent parser to parse a calc
        -- expression and build an evaluator for it.
        --
        --============================================================================
        
        local Calc = {}
        local BuildExpression
        
        ------------------------------------------------------------------------------
        --
        -- Special nodes
        --
        -- These nodes are hardcoded evaluation nodes used by the expression builder.
        -- They are used to contruct certain higher level nodes like exponentiation
        -- and unary negation.
        --
        ------------------------------------------------------------------------------
        
        Calc.mExpressions =
        {
            mZero =
                {
                    mDepth = 1,
                    Evaluate = function () return 0 end,
                },
            mTen =
                {
                    mDepth = 1,
                    Evaluate = function () return 10 end,
                },
        }
        
        ------------------------------------------------------------------------------
        --
        -- Evaluation functions
        --
        -- These function are used to build evaluation functions.
        --
        ------------------------------------------------------------------------------
        local gMathVariables = {mDepth = 0, mDataCount = 0, mSameExpression}
        local gSampleBuffer
        local gIntermediateSampleBuffer
        local gMath =
        {
            Add = function (lLeft, lRight)
                return lLeft + lRight
            end,
        
            Subtract = function (lLeft, lRight)
                return lLeft - lRight
            end,
        
            Multiply = function (lLeft, lRight)
                return lLeft * lRight
            end,
        
            Divide = function (lLeft, lRight)
                if lRight == 0 then
                    return gNan
                end
                return lLeft / lRight
            end,
        
            Power = function (lLeft, lRight)
                return lLeft ^ lRight
            end,
        
            Log = function (lValue)
                return math.log10(gMathAbs(lValue))
            end,
        
            Ln = function (lValue)
                return math.log(gMathAbs(lValue))
            end,
        
            VectorVolt = function (lIndex)
                return gIntermediateSampleBuffer.mVoltage[gMathVariables.mDataCount - gMathVariables.mDepth + lIndex + 1]
            end,
        
            VectorCurr = function (lIndex)
                return gIntermediateSampleBuffer.mCurrent[gMathVariables.mDataCount - gMathVariables.mDepth + lIndex + 1]
            end,
        
            VectorRes = function (lIndex)
                return gIntermediateSampleBuffer.mResistance[gMathVariables.mDataCount - gMathVariables.mDepth + lIndex + 1]
            end,
        
            VectorTime = function (lIndex)
                return gIntermediateSampleBuffer.mTime[gMathVariables.mDataCount - gMathVariables.mDepth + lIndex + 1]
            end,
        }
        
        ------------------------------------------------------------------------------
        --
        -- MakeBinaryNode
        --
        -- Construct a binary evaluation node. This function takes two evaluation
        -- nodes and a math function. It constructs a node that evaluates the left
        -- and right subnodes, then applies the math function to the results.
        --
        ------------------------------------------------------------------------------
        
        Calc.MakeBinaryNode = function (lLeft, lRight, lFunction)
            local lNode = {}
        
            if lRight.mDepth > lLeft.mDepth then
                lNode.mDepth = lRight.mDepth
            else
                lNode.mDepth = lLeft.mDepth
            end
            lNode.Evaluate = function ()
                local lValue1 = lLeft.Evaluate()
                local lValue2 = lRight.Evaluate()
        
                if lValue1 == gNan or lValue2 == gNan then
                    return gNan
                end
                return lFunction(lValue1, lValue2)
            end
            return lNode
        end
        
        ------------------------------------------------------------------------------
        --
        -- MakeFunctionNode
        --
        -- Construct a function evaluation node. This function takes an expression
        -- node and a math function. It constructs a node that evaluates the
        -- subexpression and then applies the math function to the result.
        --
        ------------------------------------------------------------------------------
        
        Calc.MakeFunctionNode = function (lFunction, lExpression)
            lNode = {}
        
            lNode.mDepth = lExpression.mDepth
            lNode.Evaluate = function ()
                local lValue = lExpression.Evaluate()
                if lValue == gNan then
                    return gNan
                end
                return lFunction(lValue)
            end
            return lNode
        end
        
        ------------------------------------------------------------------------------
        --
        -- MakeVectorNode
        --
        -- Construct a vector evaluation node. This function takes an index
        -- and a math function that evaluates the vector. It constructs a node that
        -- evaluates the vector function at the given index.
        --
        ------------------------------------------------------------------------------
        
        Calc.MakeVectorNode = function (lFunction, lIndex)
            lNode = {}
        
            lNode.mDepth = lIndex + 1
            lNode.Evaluate = function ()
                return lFunction(lIndex)
            end
            return lNode
        end
        
        ------------------------------------------------------------------------------
        --
        -- BuildNumber
        --
        -- Parse and build an evaluation node for a number.
        --
        ------------------------------------------------------------------------------
        
        Calc.BuildNumber = function (lText, lStart)
            local lNumber
            local lIndex
        
            lIndex = ParseNRf(lText, lStart)
            if lIndex > lStart then
                lNumber = {}
                lNumber.mDepth = 1
                lNumber.mText = string.sub(lText, lStart, lIndex - 1)
                lNumber.mValue = tonumber(lNumber.mText)
                lNumber.Evaluate = function () return lNumber.mValue end
            end
            return lNumber, lIndex
        end
        
        ------------------------------------------------------------------------------
        --
        --  BuildVector
        --
        --  Parse and build a vector node. This function expects the name of the
        --  vector to already have been parsed and translated to an implementation
        --  function which is passed in as a parameter. This function will parse
        --  brackets and build an evaluation node for the vector.
        --
        ------------------------------------------------------------------------------
        
        Calc.BuildVector = function (lText, lStart, lFunction)
            local lCharCode
            local lIndex
            local lNumber
        
            lCharCode = string.byte(lText, lStart)
            if lCharCode == gCharCodes.mBracketLeft then
                lIndex = lStart + 1
                lCharCode = string.byte(lText, lIndex)
                if lCharCode ~= gCharCodes.mPlus and lCharCode ~= gCharCodes.mMinus then
                    lNumber, lIndex = Calc.BuildNumber(lText, lIndex)
                    if lNumber then
                        lCharCode = string.byte(lText, lIndex)
                        if lCharCode == gCharCodes.mBracketRight then
                            if lNumber.mValue < 2500 then
                                return Calc.MakeVectorNode(lFunction, math.floor(lNumber.mValue)), lIndex + 1
                            else
                                gErrorQueue.Add(821)
                            end
                        else
                            gErrorQueue.Add(814)
                        end
                    else
                        gErrorQueue.Add(811)
                    end
                else
                    gErrorQueue.Add(811)
                end
            else
                return Calc.MakeVectorNode(lFunction, 0), lStart
            end
            return nil, lStart
        end
        
        ------------------------------------------------------------------------------
        --
        --  BuildFunction
        --
        ------------------------------------------------------------------------------
        
        Calc.BuildFunction = function (lText, lStart, lFunction)
            local lExpression
            --local lNode
            local lIndex
        
            lExpression, lIndex = BuildExpression(lText, lStart)
            if lExpression then
                return Calc.MakeFunctionNode(lFunction, lExpression), lIndex
            else
                return nil, lStart
            end
        end
        
        ------------------------------------------------------------------------------
        --
        --  BuildValue
        --
        ------------------------------------------------------------------------------
        
        Calc.BuildValue = function (lText, lStart)
            local lCharCode
            local lIndex
            local lIndex2
            local lName
        
            lCharCode = string.byte(lText, lStart)
            if lCharCode == gCharCodes.mParenLeft then
                return BuildExpression(lText, lStart)
            end
            if string.find(lText, "^[%d.]", lStart) then
                return Calc.BuildNumber(lText, lStart)
            end
            -- The 2400 allows alpha-numeric in identifiers here
            lIndex, lIndex2 = string.find(lText, "^%w+", lStart)
            if lIndex then
                lName = string.sub(lText, lStart, lIndex2)
                if lName == "LOG" then
                    return Calc.BuildFunction(lText, lIndex2 + 1, gMath.Log)
                elseif lName == "LN" then
                    return Calc.BuildFunction(lText, lIndex2 + 1, gMath.Ln)
                elseif lName == "SIN" then
                    return Calc.BuildFunction(lText, lIndex2 + 1, math.sin)
                elseif lName == "COS" then
                    return Calc.BuildFunction(lText, lIndex2 + 1, math.cos)
                elseif lName == "TAN" then
                    return Calc.BuildFunction(lText, lIndex2 + 1, math.tan)
                elseif lName == "ABS" then
                    return Calc.BuildFunction(lText, lIndex2 + 1, gMathAbs)
                --elseif lName == "EXP" then
                --    return Calc.BuildFunction(lText, lIndex2 + 1, math.exp)
                else
                    -- Handle vectors
                    if lCharCode == gCharCodes.mV then
                        return Calc.BuildVector(lText, lIndex2 + 1, gMath.VectorVolt)
                    elseif lCharCode == gCharCodes.mC then
                        return Calc.BuildVector(lText, lIndex2 + 1, gMath.VectorCurr)
                    elseif lCharCode == gCharCodes.mR then
                        return Calc.BuildVector(lText, lIndex2 + 1, gMath.VectorRes)
                    elseif lCharCode == gCharCodes.mT then
                        return Calc.BuildVector(lText, lIndex2 + 1, gMath.VectorTime)
                    end
                end
            end
            return nil, lStart
        end
        
        ------------------------------------------------------------------------------
        --
        --  BuildUnary
        --
        ------------------------------------------------------------------------------
        
        Calc.BuildUnary = function (lText, lStart)
            local lCharCode
            local lRight
        
            lCharCode = string.byte(lText, lStart)
            if lCharCode == gCharCodes.mMinus then
                lStart = lStart + 1
                lRight, lStart = Calc.BuildValue(lText, lStart)
                if lRight then
                    return Calc.MakeBinaryNode(Calc.mExpressions.mZero, lRight, gMath.Subtract), lStart
                else
                    gErrorQueue.Add(-170)
                    return nil, lStart
                end
            end
            if lCharCode == gCharCodes.mPlus then
                lStart = lStart + 1
            end
            return Calc.BuildValue(lText, lStart)
        end
        
        ------------------------------------------------------------------------------
        --
        --  BuildFactor
        --
        ------------------------------------------------------------------------------
        
        Calc.BuildFactor = function (lText, lStart)
            local lIndex = lStart
            local lLeft
            local lRight
            local lNode
            local lCharCode
        
            lNode, lIndex = Calc.BuildUnary(lText, lIndex)
            while lNode do
                lCharCode = string.byte(lText, lIndex)
                if lCharCode == gCharCodes.mCaret then
                    lRight, lIndex = Calc.BuildUnary(lText, lIndex + 1)
                    if lRight then
                        lLeft = lNode
                        lNode = Calc.MakeBinaryNode(lLeft, lRight, gMath.Power)
                    else
                        gErrorQueue.Add(-170)
                        return nil, lIndex
                    end
                else
                    return lNode, lIndex
                end
            end
        end
        
        ------------------------------------------------------------------------------
        --
        --  BuildTerm
        --
        ------------------------------------------------------------------------------
        
        Calc.BuildTerm = function (lText, lStart)
            local lIndex = lStart
            local lLeft
            local lRight
            local lNode
            local lCharCode
        
            lNode, lIndex = Calc.BuildFactor(lText, lIndex)
            while lNode do
                lCharCode = string.byte(lText, lIndex)
                if lCharCode == gCharCodes.mStar or lCharCode == gCharCodes.mSlash then
                    lRight, lIndex = Calc.BuildFactor(lText, lIndex + 1)
                    if lRight then
                        lLeft = lNode
                        if lCharCode == gCharCodes.mStar then
                            lNode = Calc.MakeBinaryNode(lLeft, lRight, gMath.Multiply)
                        else
                            lNode = Calc.MakeBinaryNode(lLeft, lRight, gMath.Divide)
                        end
                    else
                        gErrorQueue.Add(-170)
                        return nil, lIndex
                    end
                else
                    return lNode, lIndex
                end
            end
        end
        
        ------------------------------------------------------------------------------
        --
        --  BuildSum
        --
        ------------------------------------------------------------------------------
        
        Calc.BuildSum = function (lText, lStart)
            local lIndex = lStart
            local lLeft
            local lRight
            local lNode
            local lCharCode
        
            lNode, lIndex = Calc.BuildTerm(lText, lIndex)
            while lNode do
                lCharCode = string.byte(lText, lIndex)
                if lCharCode == gCharCodes.mPlus or lCharCode == gCharCodes.mMinus then
                    lRight, lIndex = Calc.BuildTerm(lText, lIndex + 1)
                    if lRight then
                        lLeft = lNode
                        if lCharCode == gCharCodes.mPlus then
                            lNode = Calc.MakeBinaryNode(lLeft, lRight, gMath.Add)
                        else
                            lNode = Calc.MakeBinaryNode(lLeft, lRight, gMath.Subtract)
                        end
                    else
                        gErrorQueue.Add(-170)
                        return nil, lIndex
                    end
                else
                    return lNode, lIndex
                end
            end
        end
        
        ------------------------------------------------------------------------------
        --
        -- BuildExpression
        --
        -- This function parses an expression and builds an expression tree. The
        -- character at the starting position is expected to be a left parenthesis.
        -- This function also expects the parenthesis to be balanced (as checked by
        -- the preparser).
        --
        -- The top level of the expression tree has the following members:
        --
        --      Evaluate()  A function that evaluates the expression.
        --      mDepth      The maximum vector depth found in the expression.
        --      mText       The string to return from an expression query.
        --
        -- This function returns and expression node and the location of the next
        -- character where parsing should continue.
        --
        ------------------------------------------------------------------------------
        
        BuildExpression = function (lText, lStart)
            local lIndex = lStart
            local lCharCode
            local lSum
        
            lCharCode = string.byte(lText, lIndex)
            if lCharCode == gCharCodes.mParenLeft then
                lIndex = lIndex + 1
                lSum, lIndex = Calc.BuildSum(lText, lIndex)
                if lSum then
                    lCharCode = string.byte(lText, lIndex)
                    if lCharCode == gCharCodes.mParenRight then
                        lSum.mText = string.sub(lText, lStart, lIndex)
                        lIndex = lIndex + 1
                    else
                        gErrorQueue.Add(-170)
                    end
                end
            else
                gErrorQueue.Add(812)
            end
            return lSum, lIndex
        end
        
        --============================================================================
        --
        -- Command Tables
        --
        -- This table holds the SCPI command tree. First the command hierarchy is
        -- defined for the long command forms. Short forms and optional elements
        -- are then defined. Finally, the functions that implement the commands are
        -- defined last.
        --
        --============================================================================
        
        gCommandTree =
        {
            ["*IDN"] =
            {
                mQuery = {},
            },
            ["*RST"] =
            {
                mCommand = {mPriority = true},
            },
            ["*CLS"] =
            {
                mCommand = {},
            },
            ["*OPC"] =
            {
                mCommand = {},
                mQuery = {},
            },
            ["*SAV"] =
            {
                mCommand = {},
            },
            ["*RCL"] =
            {
                 mCommand = {},
            },
            ["*TRG"] = gSpecialCommands["*TRG"],
            ["*SRE"] =
            {
                mCommand = {},
                mQuery = {},
            },
            ["*ESE"] =
            {
                mCommand = {},
                mQuery = {},
            },
            ["*ESR"] =
            {
                mQuery = {},
            },
            ["*OPT"] =
            {
                mQuery = {},
            },
            ["*TST"] =
            {
                mQuery = {},
            },
            ["*WAI"] =
            {
                mCommand = {},
            },
            ["*STB"] =
            {
                mQuery = {mPriority = true},
            },
        -- Calculate Subsystem
            ["CALCULATE1"] =
            {
                ["MATH"] =
                {
                    ["EXPRESSION"] =
                    {
                        ["CATALOG"] =
                        {
                            mQuery = {},
                        },
                        ["NAME"] =
                        {
                            mCommand = {},
                            mQuery = {},
                        },
                        ["DEFINE"] =
                        {
                            mCommand = {},
                            mQuery = {},
                        },
                        ["DELETE"] =
                        {
                            ["SELECTED"] =
                            {
                                mCommand = {},
                            },
                            ["ALL"] =
                            {
                                mCommand = {},
                            }
                        },
                    },
                    ["UNITS"]=
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                },
                ["STATE"] =
                {
                    mCommand = {},
                    mQuery = {},
                },
                ["DATA"] =
                {
                    mCommand = {},
                    mQuery = {},
                    ["LATEST"] =
                    {
                        mQuery = {},
                    },
                },
            },
            ["CALCULATE2"] =
            {
                ["FEED"] =
                {
                    mCommand = {},
                    mQuery = {},
                },
                ["NULL"] =
                {
                    ["OFFSET"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                    ["STATE"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                    ["ACQUIRE"] =
                    {
                        mCommand = {},
                    },
                },
                ["DATA"] =
                {
                    mQuery = {},
                    ["LATEST"] =
                    {
                        mQuery = {},
                    },
                },
                ["LIMIT1"] =
                {
                    ["COMPLIANCE"] =
                    {
                        ["FAIL"] =
                        {
                            mCommand = {},
                            mQuery = {},
                        },
                        --["SOURCE2"] =
                        --{
                            --mCommand = {},
                            --mQuery = {},
                        --},
                    },
                    ["STATE"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                    ["FAIL"] =
                    {
                        mQuery = {},
                    }
                },
                ["LIMIT2"] =
                {
                    ["UPPER"] =
                    {
                        ["DATA"] =
                        {
                            mCommand = {},
                            mQuery = {},
                        },
                        --["SOURCE2"] =
                        --{
                            --mCommand = {},
                            --mQuery = {},
                        --},
                    },
                    ["LOWER"] =
                    {
                        ["DATA"] =
                        {
                            mCommand = {},
                            mQuery = {},
                        },
                        --["SOURCE2"] =
                        --{
                            --mCommand = {},
                            --mQuery = {},
                        --},
                    },
                    ["PASS"] =
                    {
                        --["SOURCE2"] =
                        --{
                            --mCommand = {},
                            --mQuery = {},
                        --},
                    },
                    ["STATE"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                    ["FAIL"] =
                    {
                        mQuery = {},
                    }
                },
                ["LIMIT3"] =
                {
                    ["UPPER"] =
                    {
                        ["DATA"] =
                        {
                            mCommand = {},
                            mQuery = {},
                        },
                        --["SOURCE2"] =
                        --{
                            --mCommand = {},
                            --mQuery = {},
                        --},
                    },
                    ["LOWER"] =
                    {
                        ["DATA"] =
                        {
                            mCommand = {},
                            mQuery = {},
                        },
                        --["SOURCE2"] =
                        --{
                            --mCommand = {},
                            --mQuery = {},
                        --},
                    },
                    ["PASS"] =
                    {
                        --["SOURCE2"] =
                        --{
                            --mCommand = {},
                            --mQuery = {},
                        --},
                    },
                    ["STATE"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                    ["FAIL"] =
                    {
                        mQuery = {},
                    },
                },
                --["LIMIT4"] =
                --{
                    --["SOURCE2"] =
                    --{
                        --mCommand = {},
                        --mQuery = {},
                    --},
                    --["STATE"] =
                    --{
                        --mCommand = {},
                        --mQuery = {},
                    --},
                    --["FAIL"] =
                    --{
                        --mQuery = {},
                    --},
                --},
                ["LIMIT5"] =
                {
                    ["UPPER"] =
                    {
                        ["DATA"] =
                        {
                            mCommand = {},
                            mQuery = {},
                        },
                        --["SOURCE2"] =
                        --{
                            --mCommand = {},
                            --mQuery = {},
                        --},
                    },
                    ["LOWER"] =
                    {
                        ["DATA"] =
                        {
                            mCommand = {},
                            mQuery = {},
                        },
                        --["SOURCE2"] =
                        --{
                            --mCommand = {},
                            --mQuery = {},
                        --},
                    },
                    ["PASS"] =
                    {
                        --["SOURCE2"] =
                        --{
                            --mCommand = {},
                            --mQuery = {},
                        --},
                    },
                    ["STATE"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                    ["FAIL"] =
                    {
                        mQuery = {},
                    }
                },
                ["LIMIT6"] =
                {
                    ["UPPER"] =
                    {
                        ["DATA"] =
                        {
                            mCommand = {},
                            mQuery = {},
                        },
                        --["SOURCE2"] =
                        --{
                            --mCommand = {},
                            --mQuery = {},
                        --},
                    },
                    ["LOWER"] =
                    {
                        ["DATA"] =
                        {
                            mCommand = {},
                            mQuery = {},
                        },
                        --["SOURCE2"] =
                        --{
                            --mCommand = {},
                            --mQuery = {},
                        --},
                    },
                    ["PASS"] =
                    {
                        --["SOURCE2"] =
                        --{
                            --mCommand = {},
                            --mQuery = {},
                        --},
                    },
                    ["STATE"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                    ["FAIL"] =
                    {
                        mQuery = {},
                    }
                },
                ["LIMIT7"] =
                {
                    ["UPPER"] =
                    {
                        ["DATA"] =
                        {
                            mCommand = {},
                            mQuery = {},
                        },
                        --["SOURCE2"] =
                        --{
                            --mCommand = {},
                            --mQuery = {},
                        --},
                    },
                    ["LOWER"] =
                    {
                        ["DATA"] =
                        {
                            mCommand = {},
                            mQuery = {},
                        },
                        --["SOURCE2"] =
                        --{
                            --mCommand = {},
                            --mQuery = {},
                        --},
                    },
                    ["PASS"] =
                    {
                        --["SOURCE2"] =
                        --{
                            --mCommand = {},
                            --mQuery = {},
                        --},
                    },
                    ["STATE"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                    ["FAIL"] =
                    {
                        mQuery = {},
                    },
                },
                ["LIMIT8"] =
                {
                    ["UPPER"] =
                    {
                        ["DATA"] =
                        {
                            mCommand = {},
                            mQuery = {},
                        },
                        --["SOURCE2"] =
                        --{
                            --mCommand = {},
                            --mQuery = {},
                        --},
                    },
                    ["LOWER"] =
                    {
                        ["DATA"] =
                        {
                            mCommand = {},
                            mQuery = {},
                        },
                        --["SOURCE2"] =
                        --{
                            --mCommand = {},
                            --mQuery = {},
                        --},
                    },
                    ["PASS"] =
                    {
                        --["SOURCE2"] =
                        --{
                            --mCommand = {},
                            --mQuery = {},
                        --},
                    },
                    ["STATE"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                    ["FAIL"] =
                    {
                        mQuery = {},
                    },
                },
                ["LIMIT9"] =
                {
                    ["UPPER"] =
                    {
                        ["DATA"] =
                        {
                            mCommand = {},
                            mQuery = {},
                        },
                        --["SOURCE2"] =
                        --{
                            --mCommand = {},
                            --mQuery = {},
                        --},
                    },
                    ["LOWER"] =
                    {
                        ["DATA"] =
                        {
                            mCommand = {},
                            mQuery = {},
                        },
                        --["SOURCE2"] =
                        --{
                            --mCommand = {},
                            --mQuery = {},
                        --},
                    },
                    ["PASS"] =
                    {
                        --["SOURCE2"] =
                        --{
                            --mCommand = {},
                            --mQuery = {},
                        --},
                    },
                    ["STATE"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                    ["FAIL"] =
                    {
                        mQuery = {},
                    },
                },
                ["LIMIT10"] =
                {
                    ["UPPER"] =
                    {
                        ["DATA"] =
                        {
                            mCommand = {},
                            mQuery = {},
                        },
                        --["SOURCE2"] =
                        --{
                            --mCommand = {},
                            --mQuery = {},
                        --},
                    },
                    ["LOWER"] =
                    {
                        ["DATA"] =
                        {
                            mCommand = {},
                            mQuery = {},
                        },
                        --["SOURCE2"] =
                        --{
                            --mCommand = {},
                            --mQuery = {},
                        --},
                    },
                    ["PASS"] =
                    {
                        --["SOURCE2"] =
                        --{
                            --mCommand = {},
                            --mQuery = {},
                        --},
                    },
                    ["STATE"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                    ["FAIL"] =
                    {
                        mQuery = {},
                    },
                },
                ["LIMIT11"] =
                {
                    ["UPPER"] =
                    {
                        ["DATA"] =
                        {
                            mCommand = {},
                            mQuery = {},
                        },
                        --["SOURCE2"] =
                        --{
                            --mCommand = {},
                            --mQuery = {},
                        --},
                    },
                    ["LOWER"] =
                    {
                        ["DATA"] =
                        {
                            mCommand = {},
                            mQuery = {},
                        },
                        --["SOURCE2"] =
                        --{
                            --mCommand = {},
                            --mQuery = {},
                        --},
                    },
                    ["PASS"] =
                    {
                        --["SOURCE2"] =
                        --{
                            --mCommand = {},
                            --mQuery = {},
                        --},
                    },
                    ["STATE"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                    ["FAIL"] =
                    {
                        mQuery = {},
                    },
                },
                ["LIMIT12"] =
                {
                    ["UPPER"] =
                    {
                        ["DATA"] =
                        {
                            mCommand = {},
                            mQuery = {},
                        },
                        --["SOURCE2"] =
                        --{
                            --mCommand = {},
                            --mQuery = {},
                        --},
                    },
                    ["LOWER"] =
                    {
                        ["DATA"] =
                        {
                            mCommand = {},
                            mQuery = {},
                        },
                        --["SOURCE2"] =
                        --{
                            --mCommand = {},
                            --mQuery = {},
                        --},
                    },
                    ["PASS"] =
                    {
                        --["SOURCE2"] =
                        --{
                            --mCommand = {},
                            --mQuery = {},
                        --},
                    },
                    ["STATE"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                    ["FAIL"] =
                    {
                        mQuery = {},
                    },
                },
                ["CLIMITS"] =
                {
                    ["BCONTROL"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                    ["MODE"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                    ["CLEAR"] =
                    {
                        ["IMMEDIATE"] =
                        {
                            mCommand = {},
                        },
                        ["AUTO"] =
                        {
                            mCommand = {},
                            mQuery = {},
                        },
                    },
                    ["PASS"] =
                    {
                        --["SOURCE2"] =
                        --{
                            --mCommand = {},
                            --mQuery = {},
                        --},
                        ["SMLOCATION"] =
                        {
                            mCommand = {},
                            mQuery = {},
                        },
                    },
                    ["FAIL"] =
                    {
                        --["SOURCE2"] =
                        --{
                            --mCommand = {},
                            --mQuery = {},
                        --},
                        ["SMLOCATION"] =
                        {
                            mCommand = {},
                            mQuery = {},
                        },
                    },
                },
            },
            ["CALCULATE3"] =
            {
                ["FORMAT"] =
                {
                    mCommand = {},
                    mQuery = {},
                },
                ["DATA"] =
                {
                    mQuery = {},
                },
            },
        
        -- Display Subsystem
            ["DISPLAY"] =
            {
                ["ENABLE"] =
                {
                    mCommand = {},
                    mQuery = {},
                },
                ["CNDISPLAY"] =
                {
                    mCommand = {},
                },
                ["WINDOW1"] =
                {
                    ["TEXT"] =
                    {
                        ["DATA"] =
                        {
                            mCommand = {},
                            mQuery = {},
                        },
                        ["STATE"] =
                        {
                            mCommand = {},
                            mQuery = {},
                        },
                    },
                    ["DATA"] =
                    {
                        mQuery = {},
                    },
                    ["ATTRIBUTES"] =
                    {
                        mQuery = {},
                    },
                },
                ["WINDOW2"] =
                {
                    ["TEXT"] =
                    {
                        ["DATA"] =
                        {
                            mCommand = {},
                            mQuery = {},
                        },
                        ["STATE"] =
                        {
                            mCommand = {},
                            mQuery = {},
                        },
                    },
                    ["DATA"] =
                    {
                        mQuery = {},
                    },
                    ["ATTRIBUTES"] =
                    {
                        mQuery = {},
                    },
                },
                ["DIGITS"] =
                {
                    mCommand = {},
                    mQuery = {},
                },
            },
        
        -- Format Subsystem
            ["FORMAT"] =
            {
                ["SREGISTER"] =
                {
                    mCommand = {},
                    mQuery = {},
                },
                ["DATA"] =
                {
                    mCommand = {},
                    mQuery = {},
                },
                ["BORDER"] =
                {
                    mCommand = {},
                    mQuery = {},
                },
                ["ELEMENTS"] =
                {
                    ["SENSE1"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                    ["CALCULATE"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                },
                ["SREGISTER"] =
                {
                    mCommand = {},
                    mQuery = {},
                },
                ["SOURCE2"] =
                {
                    mCommand = {},
                    mQuery = {},
                },
            },
            ["DIAGNOSTIC"] =
            {
                ["ECHO"] =
                {
                    mCommand = {}
                },
                ["EXIT"] =
                {
                    mCommand = {},
                },
                ["VERSION"] =
                {
                    mQuery = {}
                },
                ["MODEL"] =
                {
                    mQuery = {}
                },
                ["FWREV"] =
                {
                    mQuery = {}
                },
                ["DISPLAY"] = 
                {
                    ["ERRORS"] = 
                    {
                       mCommand = {},
                       mQuery = {},
                    },
                },
        
            },
        
        -- Output susbystem
            ["OUTPUT1"] =
            {
                ["STATE"] =
                {
                    mCommand = {mPriority = true},
                    --mCommand = {},
                    mQuery = {},
                },
                ["ENABLE"] =
                {
                    ["STATE"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                    ["TRIPPED"] =
                    {
                        mQuery = {},
                    },
                },
                ["SMODE"] =
                {
                    mCommand = {},
                    mQuery = {},
                },
                ["INTERLOCK"] = 
                {
                    ["STATE"] = 
                    {
                        mCommand = {},
                        mQuery = {},
                    }
                },
            },
        
        -- Route subsystem
            ["ROUTE"] =
            {
                ["TERMINALS"] =
                {
                    mCommand = {},
                    mQuery = {},
                },
            },
            ["DATA"] =
            {
            },
        
        -- Sense subsystem
            ["SENSE1"] =
            {
                ["DATA"] =
                {
                    ["LATEST"] =
                    {
                        mQuery = {},
                    },
                },
                ["FUNCTION"] =
                {
                    ["CONCURRENT"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                    ["ON"] =
                    {
                        mCommand = {},
                        mQuery = {},
                        ["ALL"] =
                        {
                            mCommand = {},
                        },
                        ["COUNT"] =
                        {
                            mQuery = {},
                        },
                    },
                    ["OFF"] =
                    {
                        mCommand = {},
                        mQuery = {},
                        ["ALL"] =
                        {
                            mCommand = {},
                        },
                        ["COUNT"] =
                        {
                            mQuery = {},
                        },
                    },
                    ["STATE"] =
                    {
                        mQuery = {},
                    },
                },
                ["CURRENT"] =
                {
                    ["DC"] =
                    {
                        ["RANGE"] =
                        {
                            ["UPPER"] =
                            {
                                mCommand = {},
                                mQuery = {},
                            },
                            ["AUTO"] =
                            {
                                mCommand = {},
                                mQuery = {},
                                ["ULIMIT"] =
                                {
                                    mQuery = {},
                                },
                                ["LLIMIT"] =
                                {
                                    mCommand = {},
                                    mQuery = {},
                                },
                            },
                            --["HOLDOFF"] =
                            --{
                                --mCommand = {},
                                --mQuery = {},
                                --["DELAY"] =
                                --{
                                    --mCommand = {},
                                    --mQuery = {},
                                --},
                            --},
                        },
                        ["NPLCYCLES"] =
                        {
                            mCommand = {},
                            mQuery = {},
                        },
                        ["PROTECTION"] =
                        {
                            ["LEVEL"] =
                            {
                                mCommand = {},
                                mQuery = {},
                            },
                            ["TRIPPED"] =
                            {
                                mQuery = {},
                            },
                            ["RSYNCHRONIZE"] =
                            {
                                mCommand = {},
                                mQuery = {},
                            },
                        },
                    },
                },
                ["VOLTAGE"] =
                {
                    ["DC"] =
                    {
                        ["RANGE"] =
                        {
                            ["UPPER"] =
                            {
                                mCommand = {},
                                mQuery = {},
                            },
                            ["AUTO"] =
                            {
                                mCommand = {},
                                mQuery = {},
                                ["ULIMIT"] =
                                {
                                    mQuery = {},
                                },
                                ["LLIMIT"] =
                                {
                                    mCommand = {},
                                    mQuery = {},
                                },
                            },
                        },
                        ["PROTECTION"] =
                        {
                            ["LEVEL"] =
                            {
                                mCommand = {},
                                mQuery = {},
                            },
                            ["TRIPPED"] =
                            {
                                mQuery = {},
                            },
                            ["RSYNCHRONIZE"] =
                            {
                                mCommand = {},
                                mQuery = {},
                            },
                        },
                    },
                },
                ["RESISTANCE"] =
                {
                    ["MODE"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                    --["OCOMPENSATED"] =
                    --{
                        --mCommand = {},
                        --mQuery = {},
                    --},
                    ["RANGE"] =
                    {
                        ["UPPER"] =
                        {
                            mCommand = {},
                            mQuery = {},
        
                            ["AUTO"] =
                            {
                                mCommand = {},
                                mQuery = {},
                                --["ULIMIT"] =
                                --{
                                    --mCommand = {},
                                    --mQuery = {},
                                --},
                                --["LLIMIT"] =
                                --{
                                    --mCommand = {},
                                    --mQuery = {},
                                --},
                            },
                        },
                    },
                },
                ["AVERAGE"] =
                {
                    ["TCONTROL"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                    ["COUNT"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                    ["STATE"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                },
            },
        
        -- Source subsystem
            ["SOURCE1"] =
            {
                ["CLEAR"] =
                {
                    ["IMMEDIATE"] =
                    {
                        mCommand = {},
                    },
                    ["AUTO"] =
                    {
                        mCommand = {},
                        mQuery = {},
                        ["MODE"] =
                        {
                            mCommand = {},
                            mQuery = {},
                        },
                    },
                },
                ["FUNCTION"] =
                {
                    --["SHAPE"] =
                    --{
                        --mCommand = {},
                        --mQuery = {},
                    --},
                    ["MODE"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                },
                ["DELAY"] =
                {
                    mCommand = {},
                    mQuery = {},
                    ["AUTO"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                },
                ["CURRENT"] =
                {
                    ["MODE"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                    ["RANGE"] =
                    {
                        mCommand = {},
                        mQuery = {},
                        ["AUTO"] =
                        {
                            mCommand = {},
                            mQuery = {},
                        },
                    },
                    ["LEVEL"] =
                    {
                        ["IMMEDIATE"] =
                        {
                            ["AMPLITUDE"] =
                            {
                                mCommand = {},
                                mQuery = {},
                            }
                        },
                        ["TRIGGERED"] =
                        {
                            ["AMPLITUDE"] =
                            {
                                mCommand = {},
                                mQuery = {},
                            },
                            ["SFACTOR"] =
                            {
                                mCommand = {},
                                mQuery = {},
                                ["STATE"] =
                                {
                                    mCommand = {},
                                    mQuery = {},
                                },
                            },
                        },
                    },
                    ["START"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                    ["STOP"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                    ["STEP"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                    ["SPAN"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                    ["CENTER"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                },
                ["VOLTAGE"] =
                {
                    ["MODE"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                    ["RANGE"] =
                    {
                        mCommand = {},
                        mQuery = {},
                        ["AUTO"] =
                        {
                            mCommand = {},
                            mQuery = {},
                        },
                    },
                    ["LEVEL"] =
                    {
                        ["IMMEDIATE"] =
                        {
                            ["AMPLITUDE"] =
                            {
                                mCommand = {},
                                mQuery = {},
                            },
                        },
                        ["TRIGGERED"] =
                        {
                            ["AMPLITUDE"] =
                            {
                                mCommand = {},
                                mQuery = {},
                            },
                            ["SFACTOR"] =
                            {
                                mCommand = {},
                                mQuery = {},
                                ["STATE"] =
                                {
                                    mCommand = {},
                                    mQuery = {},
                                },
                            },
                        },
                    },
                    --["PROTECTION"] =
                    --{
                        --mCommand = {},
                        --mQuery = {},
                        --["LEVEL"] =
                        --{
                            --mCommand = {},
                            --mQuery = {},
                        --},
                        --["TRIPPED"] =
                        --{
                            --mQuery = {},
                        --},
                    --},
                    ["START"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                    ["STOP"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                    ["STEP"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                    ["SPAN"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                    ["CENTER"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                },
                ["SOAK"] =
                {
                    --mCommand = {},
                    mQuery = {},
                },
                ["SWEEP"] =
                {
                    ["SPACING"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                    ["POINTS"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                    ["DIRECTION"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                    ["RANGING"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                    --["CABORT"] =
                    --{
                        --mCommand = {},
                        --mQuery = {},
                    --},
                },
                ["LIST"] =
                {
                    ["CURRENT"] =
                    {
                        mCommand = {},
                        mQuery = {},
                        ["APPEND"] =
                        {
                            mCommand = {},
                        },
                        ["POINTS"] =
                        {
                            mQuery = {},
                        },
                        ["START"] =
                        {
                            mCommand = {},
                            mQuery = {},
                        },
                    },
                    ["VOLTAGE"] =
                    {
                        mCommand = {},
                        mQuery = {},
                        ["APPEND"] =
                        {
                            mCommand = {},
                        },
                        ["POINTS"] =
                        {
                            mQuery = {},
                        },
                        ["START"] =
                        {
                            mCommand = {},
                            mQuery = {},
                        },
                    },
                },
                ["MEMORY"] =
                {
                    ["SAVE"] =
                    {
                        mCommand = {},
                    },
                    ["RECALL"] =
                    {
                        mCommand = {},
                    },
                    ["POINTS"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                    ["START"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                },
                ["PULSE"] =
                {
                    ["WIDTH"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                    ["DELAY"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                },
            },
        
        --[[
            ["SOURCE2"] =
            {
                ["BSIZE"] =
                {
                    mCommand = {},
                    mQuery = {},
                },
                ["TTL"] =
                {
                    ["LEVEL"] =
                    {
                        mCommand = {},
                        mQuery = {},
                        ["ACTUAL"] =
                        {
                            mQuery = {},
                        },
                    },
                    ["DEFAULT"] =
                    {
                    },
                },
                ["TTL4"] =
                {
                    ["MODE"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                    ["BSTATE"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                },
                ["CLEAR"] =
                {
                    ["IMMEDIATE"] =
                    {
                        mCommand = {},
                    },
                    ["AUTO"] =
                    {
                        mCommand = {},
                        mQuery = {},
                        ["DELAY"] =
                        {
                            mCommand = {},
                            mQuery = {},
                        },
                    },
                },
            },
        --]]
        
        -- STATus Subsystem
            ["STATUS"] =
            {
                ["MEASUREMENT"] =
                {
                    ["EVENT"] =
                    {
                        mQuery = {},
                    },
                    ["ENABLE"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                    ["CONDITION"] =
                    {
                        mQuery = {},
                    },
                },
                ["OPERATION"] =
                {
                    ["EVENT"] =
                    {
                        mQuery =  {mPriority = true},
                    },
                    ["ENABLE"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                    ["CONDITION"] =
                    {
                        mQuery =  {mPriority = true},
                    },
                },
                ["QUESTIONABLE"] =
                {
                    ["EVENT"] =
                    {
                        mQuery = {},
                    },
                    ["ENABLE"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                    ["CONDITION"] =
                    {
                        mQuery = {},
                    },
                },
                ["PRESET"] =
                {
                    --mCommand = {mPriority = true},
                     mCommand = {},
                },
                ["QUEUE"] =
                {
                    ["NEXT"] =
                    {
                        mQuery = {},
                    },
                    ["ENABLE"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                    ["DISABLE"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                    ["CLEAR"] =
                    {
                        mCommand = {},
                    },
                },
            },
        
        -- System Subsystem
            ["SYSTEM"] =
            {
                ["PRESET"] =
                {
                    mCommand = {mPriority = true},
                    --mCommand = {},
                },
                ["POSETUP"] =
                {
                    mCommand = {},
                    mQuery = {},
                },
                ["VERSION"] =
                {
                    mQuery = {},
                },
                ["ERROR"] =
                {
                    ["NEXT"] =
                    {
                        mQuery = {},
                    },
                    ["ALL"] =
                    {
                        mQuery = {},
                    },
                    ["COUNT"] =
                    {
                        mQuery = {},
                    },
                    ["CODE"] =
                    {
                        ["NEXT"] =
                        {
                            mQuery = {},
                        },
                        ["ALL"] =
                        {
                            mQuery = {},
                        },
                    },            
                },
                --["CCHECK"] =
                --{
                    --mCommand = {},
                    --["RES"] =
                    --{
                    --  mCommand = {},
                    --},
                --},
                ["CLEAR"] =
                {
                    mCommand = {},
                },
                ["RSENSE"] =
                {
                    mCommand = {},
                    mQuery = {},
                },
                --["KEY"] =
                --{
                    --mCommand = {},
                    --mQuery = {},
                --},
                --["GUARD"] =
                --{
                    --mCommand = {},
                    --mQuery = {},
                --},
                ["BEEPER"] =
                {
                    ["IMMEDIATE"] =
                    {
                        mCommand = {},
                    },
                    ["STATE"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                },
                ["AZERO"] =
                {
                    ["STATE"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                    ["CACHING"] =
                    {
                        ["STATE"] =
                        {
                            mCommand = {},
                            mQuery = {},
                        },
                        ["REFRESH"] =
                        {
                            mCommand = {},
                        },
                        ["RESET"] =
                        {
                            mCommand = {},
                        },
                        ["NPLCYCLES"] =
                        {
                            mQuery = {},
                        },
                    },
                },
                ["LFREQUENCY"] =
                {
                    mCommand = {},
                    mQuery = {},
                    ["AUTO"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                },
                ["TIME"] =
                {
                    mQuery = {},
                    ["RESET"] =
                    {
                        mCommand = {},
                        ["AUTO"] =
                        {
                            mCommand = {},
                            mQuery = {}
                        },
                    },
                },
                ["MEMORY"] =
                {
                    mCommand = {},
                    ["INITIALIZE"] =
                    {
                        mCommand = {},
                    },
                },
                --["LOCAL"] =
                --{
                --},
                ["RWLOCK"] =
                {
                    mCommand = {},
                },
                --["RCMODE"] =
                --{
                    --mCommand = {},
                    --mQuery = {},
                --},
                ["MEP"] =
                {
                    ["STATE"] =
                    {
                        mQuery = {},
                    },
                    --["HOLDOFF"] =
                    --{
                        --mCommand = {},
                        --mQuery = {},
                    --},
                },
                ["REMOTE"] = 
                {
                    mCommand = {}
                },
            },
        
        -- Trace Subsystem
            ["TRACE"] =
            {
                mQuery = {},
                ["DATA"] =
                {
                    mQuery = {},
                },
                ["CLEAR"] =
                {
                    mCommand = {},
                },
                ["FREE"] =
                {
                    mQuery = {},
                },
                ["POINTS"] =
                {
                    mCommand = {},
                    mQuery = {},
                    ["ACTUAL"] =
                    {
                        mQuery = {},
                    },
                },
                ["FEED"] =
                {
                    mCommand = {},
                    mQuery = {},
                    ["CONTROL"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                },
                ["TSTAMP"] =
                {
                    ["FORMAT"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                },
            },
        
        -- Trigger Subsystem
            ["INITIATE"] =
            {
                ["IMMEDIATE"] =
                {
                    mCommand = {},
                },
            },
            ["ABORT"] = gSpecialCommands["ABORT"],
            ["ARM"] =
            {
                ["SEQUENCE1"] =
                {
                    ["LAYER1"] =
                    {
                        ["COUNT"] =
                        {
                            mCommand = {},
                            mQuery = {},
                        },
                        ["SOURCE"] =
                        {
                            mCommand = {},
                            mQuery = {},
                        },
                        ["TIMER"] =
                        {
                            mCommand = {},
                            mQuery = {},
                        },
                        ["TCONFIGURE"] =
                        {
                            ["DIRECTION"] =
                            {
                                mCommand = {},
                                mQuery = {},
                            },
                            ["ASYNCHRONOUS"] =
                            {
                                --["ILINE"] =
                                --{
                                    --mCommand = {},
                                    --mQuery = {},
                                --},
                                --["OLINE"] =
                                --{
                                    --mCommand = {},
                                    --mQuery = {},
                                --},
                                --["OUTPUT"] =
                                --{
                                    --mCommand = {},
                                    --mQuery = {},
                                --},
                            },
                        },
                    },
                },
            },
            ["TRIGGER"] =
            {
                ["CLEAR"] =
                {
                    mCommand = {},
                },
                ["SEQUENCE1"] =
                {
                    ["COUNT"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                    ["DELAY"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                    ["SOURCE"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                    ["TCONFIGURE"] =
                    {
                        ["DIRECTION"] =
                        {
                            mCommand = {},
                            mQuery = {},
                        },
                        ["ASYNCHRONOUS"] =
                        {
                            --["ILINE"] =
                            --{
                                --mCommand = {},
                                --mQuery = {},
                            --},
                            ["INPUT"] =
                            {
                                mCommand = {},
                                mQuery = {},
                            },
                            --["OLINE"] =
                            --{
                                --mCommand = {},
                                --mQuery = {},
                            --},
                            --["OUTPUT"] =
                            --{
                                --mCommand = {},
                                --mQuery = {},
                            --},
                        },
                    },
                },
            },
        
        -- SCPI oriented measurement commands
            ["READ"] =
            {
                mQuery = {},
            },
            ["FETCH"] =
            {
                mQuery = {},
            },
            ["CONFIGURE"] =
            {
                ["CURRENT"] =
                {
                    ["DC"] =
                    {
                        mCommand = {},
                    }
                },
                ["VOLTAGE"] =
                {
                    ["DC"] =
                    {
                        mCommand = {},
                    }
                },
                ["RESISTANCE"] =
                {
                    mCommand = {},
                },
            },
            ["MEASURE"] =
            {
                mQuery = {},
                ["CURRENT"] =
                {
                    ["DC"] =
                    {
                        mQuery = {},
                    }
                },
                ["VOLTAGE"] =
                {
                    ["DC"] =
                    {
                        mQuery = {},
                    }
                },
                ["RESISTANCE"] =
                {
                    mQuery = {},
                },
            },
        }
        
        if gDigioSupport then
            gCommandTree["SOURCE2"] =
            {
                ["BSIZE"] =
                {
                    mCommand = {},
                    mQuery = {},
                },
                ["TTL"] =
                {
                    ["LEVEL"] =
                    {
                        mCommand = {},
                        mQuery = {},
                        ["ACTUAL"] =
                        {
                            mQuery = {},
                        },
                    },
                    ["DEFAULT"] =
                    {
                    },
                },
                ["TTL4"] =
                {
                    ["MODE"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                    ["BSTATE"] =
                    {
                        mCommand = {},
                        mQuery = {},
                    },
                },
                ["CLEAR"] =
                {
                    ["IMMEDIATE"] =
                    {
                        mCommand = {},
                    },
                    ["AUTO"] =
                    {
                        mCommand = {},
                        mQuery = {},
                        ["DELAY"] =
                        {
                            mCommand = {},
                            mQuery = {},
                        },
                    },
                },
            }
        
            gCommandTree["CALCULATE2"]["LIMIT1"]["COMPLIANCE"]["SOURCE2"] =
            {
                mCommand = {},
                mQuery = {},
            }
        
            gCommandTree["CALCULATE2"]["LIMIT2"]["UPPER"]["SOURCE2"] =
            {
                mCommand = {},
                mQuery = {},
            }
            gCommandTree["CALCULATE2"]["LIMIT2"]["LOWER"]["SOURCE2"] =
            {
                mCommand = {},
                mQuery = {},
            }
            gCommandTree["CALCULATE2"]["LIMIT2"]["PASS"]["SOURCE2"] =
            {
                mCommand = {},
                mQuery = {},
            }
        
            gCommandTree["CALCULATE2"]["LIMIT3"]["UPPER"]["SOURCE2"] =
            {
                mCommand = {},
                mQuery = {},
            }
            gCommandTree["CALCULATE2"]["LIMIT3"]["LOWER"]["SOURCE2"] =
            {
                mCommand = {},
                mQuery = {},
            }
            gCommandTree["CALCULATE2"]["LIMIT3"]["PASS"]["SOURCE2"] =
            {
                mCommand = {},
                mQuery = {},
            }
        
            gCommandTree["CALCULATE2"]["LIMIT5"]["UPPER"]["SOURCE2"] =
            {
                mCommand = {},
                mQuery = {},
            }
            gCommandTree["CALCULATE2"]["LIMIT5"]["LOWER"]["SOURCE2"] =
            {
                mCommand = {},
                mQuery = {},
            }
            gCommandTree["CALCULATE2"]["LIMIT5"]["PASS"]["SOURCE2"] =
            {
                mCommand = {},
                mQuery = {},
            }
        
            gCommandTree["CALCULATE2"]["LIMIT6"]["UPPER"]["SOURCE2"] =
            {
                mCommand = {},
                mQuery = {},
            }
            gCommandTree["CALCULATE2"]["LIMIT6"]["LOWER"]["SOURCE2"] =
            {
                mCommand = {},
                mQuery = {},
            }
            gCommandTree["CALCULATE2"]["LIMIT6"]["PASS"]["SOURCE2"] =
            {
                mCommand = {},
                mQuery = {},
            }
        
            gCommandTree["CALCULATE2"]["LIMIT7"]["UPPER"]["SOURCE2"] =
            {
                mCommand = {},
                mQuery = {},
            }
            gCommandTree["CALCULATE2"]["LIMIT7"]["LOWER"]["SOURCE2"] =
            {
                mCommand = {},
                mQuery = {},
            }
            gCommandTree["CALCULATE2"]["LIMIT7"]["PASS"]["SOURCE2"] =
            {
                mCommand = {},
                mQuery = {},
            }
        
            gCommandTree["CALCULATE2"]["LIMIT8"]["UPPER"]["SOURCE2"] =
            {
                mCommand = {},
                mQuery = {},
            }
            gCommandTree["CALCULATE2"]["LIMIT8"]["LOWER"]["SOURCE2"] =
            {
                mCommand = {},
                mQuery = {},
            }
            gCommandTree["CALCULATE2"]["LIMIT8"]["PASS"]["SOURCE2"] =
            {
                mCommand = {},
                mQuery = {},
            }
        
            gCommandTree["CALCULATE2"]["LIMIT9"]["UPPER"]["SOURCE2"] =
            {
                mCommand = {},
                mQuery = {},
            }
            gCommandTree["CALCULATE2"]["LIMIT9"]["LOWER"]["SOURCE2"] =
            {
                mCommand = {},
                mQuery = {},
            }
            gCommandTree["CALCULATE2"]["LIMIT9"]["PASS"]["SOURCE2"] =
            {
                mCommand = {},
                mQuery = {},
            }
        
            gCommandTree["CALCULATE2"]["LIMIT10"]["UPPER"]["SOURCE2"] =
            {
                mCommand = {},
                mQuery = {},
            }
            gCommandTree["CALCULATE2"]["LIMIT10"]["LOWER"]["SOURCE2"] =
            {
                mCommand = {},
                mQuery = {},
            }
            gCommandTree["CALCULATE2"]["LIMIT10"]["PASS"]["SOURCE2"] =
            {
                mCommand = {},
                mQuery = {},
            }
        
            gCommandTree["CALCULATE2"]["LIMIT11"]["UPPER"]["SOURCE2"] =
            {
                mCommand = {},
                mQuery = {},
            }
            gCommandTree["CALCULATE2"]["LIMIT11"]["LOWER"]["SOURCE2"] =
            {
                mCommand = {},
                mQuery = {},
            }
            gCommandTree["CALCULATE2"]["LIMIT11"]["PASS"]["SOURCE2"] =
            {
                mCommand = {},
                mQuery = {},
            }
        
             gCommandTree["CALCULATE2"]["LIMIT12"]["UPPER"]["SOURCE2"] =
            {
                mCommand = {},
                mQuery = {},
            }
            gCommandTree["CALCULATE2"]["LIMIT12"]["LOWER"]["SOURCE2"] =
            {
                mCommand = {},
                mQuery = {},
            }
            gCommandTree["CALCULATE2"]["LIMIT12"]["PASS"]["SOURCE2"] =
            {
                mCommand = {},
                mQuery = {},
            }
        
            gCommandTree["CALCULATE2"]["CLIMITS"]["PASS"]["SOURCE2"] =
            {
                mCommand = {},
                mQuery = {},
            }
        
            gCommandTree["CALCULATE2"]["CLIMITS"]["FAIL"]["SOURCE2"] =
            {
                mCommand = {},
                mQuery = {},
            }
        
        
            gCommandTree["ARM"]["SEQUENCE1"]["LAYER1"]["TCONFIGURE"]["ASYNCHRONOUS"]["ILINE"] =
            {
                mCommand = {},
                mQuery = {},
            }
            gCommandTree["ARM"]["SEQUENCE1"]["LAYER1"]["TCONFIGURE"]["ASYNCHRONOUS"]["OLINE"] =
            {
                mCommand = {},
                mQuery = {},
            }
            gCommandTree["ARM"]["SEQUENCE1"]["LAYER1"]["TCONFIGURE"]["ASYNCHRONOUS"]["OUTPUT"] =
            {
                mCommand = {},
                mQuery = {},
            }
        
        
            gCommandTree["TRIGGER"]["SEQUENCE1"]["TCONFIGURE"]["ASYNCHRONOUS"]["ILINE"] =
            {
                mCommand = {},
                mQuery = {},
            }
            gCommandTree["TRIGGER"]["SEQUENCE1"]["TCONFIGURE"]["ASYNCHRONOUS"]["OLINE"] =
            {
                mCommand = {},
                mQuery = {},
            }
            gCommandTree["TRIGGER"]["SEQUENCE1"]["TCONFIGURE"]["ASYNCHRONOUS"]["OUTPUT"] =
            {
                mCommand = {},
                mQuery = {},
            }
        end
        
        -- Aliases
        gCommandTree["ARM"]["ASYNCHRONOUS"] = gCommandTree["ARM"]["SEQUENCE1"]["LAYER1"]["TCONFIGURE"]["ASYNCHRONOUS"]
        gCommandTree["ARM"]["COUNT"] = gCommandTree["ARM"]["SEQUENCE1"]["LAYER1"]["COUNT"]
        gCommandTree["ARM"]["DIRECTION"] = gCommandTree["ARM"]["SEQUENCE1"]["LAYER1"]["TCONFIGURE"]["DIRECTION"]
        gCommandTree["ARM"]["ILINE"] = gCommandTree["ARM"]["SEQUENCE1"]["LAYER1"]["TCONFIGURE"]["ASYNCHRONOUS"]["ILINE"]
        gCommandTree["ARM"]["LAYER1"] = gCommandTree["ARM"]["SEQUENCE1"]["LAYER1"]
        gCommandTree["ARM"]["OLINE"] = gCommandTree["ARM"]["SEQUENCE1"]["LAYER1"]["TCONFIGURE"]["ASYNCHRONOUS"]["OLINE"]
        gCommandTree["ARM"]["OUTPUT"] = gCommandTree["ARM"]["SEQUENCE1"]["LAYER1"]["TCONFIGURE"]["ASYNCHRONOUS"]["OUTPUT"]
        gCommandTree["ARM"]["SEQUENCE1"]["ASYNCHRONOUS"] = gCommandTree["ARM"]["SEQUENCE1"]["LAYER1"]["ASYNCHRONOUS"]
        gCommandTree["ARM"]["SEQUENCE1"]["COUNT"] = gCommandTree["ARM"]["SEQUENCE1"]["LAYER1"]["COUNT"]
        gCommandTree["ARM"]["SEQUENCE1"]["DIRECTION"] = gCommandTree["ARM"]["SEQUENCE1"]["LAYER1"]["TCONFIGURE"]["DIRECTION"]
        gCommandTree["ARM"]["SEQUENCE1"]["ILINE"] = gCommandTree["ARM"]["SEQUENCE1"]["LAYER1"]["TCONFIGURE"]["ASYNCHRONOUS"]["ILINE"]
        gCommandTree["ARM"]["SEQUENCE1"]["LAYER1"]["ASYNCHRONOUS"] = gCommandTree["ARM"]["SEQUENCE1"]["LAYER1"]["TCONFIGURE"]["ASYNCHRONOUS"]
        gCommandTree["ARM"]["SEQUENCE1"]["LAYER1"]["DIRECTION"] = gCommandTree["ARM"]["SEQUENCE1"]["LAYER1"]["TCONFIGURE"]["DIRECTION"]
        gCommandTree["ARM"]["SEQUENCE1"]["LAYER1"]["ILINE"] = gCommandTree["ARM"]["SEQUENCE1"]["LAYER1"]["TCONFIGURE"]["ASYNCHRONOUS"]["ILINE"]
        gCommandTree["ARM"]["SEQUENCE1"]["LAYER1"]["OLINE"] = gCommandTree["ARM"]["SEQUENCE1"]["LAYER1"]["TCONFIGURE"]["ASYNCHRONOUS"]["OLINE"]
        gCommandTree["ARM"]["SEQUENCE1"]["LAYER1"]["OUTPUT"] = gCommandTree["ARM"]["SEQUENCE1"]["LAYER1"]["TCONFIGURE"]["ASYNCHRONOUS"]["OUTPUT"]
        gCommandTree["ARM"]["SEQUENCE1"]["LAYER1"]["TCONFIGURE"]["ILINE"] = gCommandTree["ARM"]["SEQUENCE1"]["LAYER1"]["TCONFIGURE"]["ASYNCHRONOUS"]["ILINE"]
        gCommandTree["ARM"]["SEQUENCE1"]["LAYER1"]["TCONFIGURE"]["OLINE"] = gCommandTree["ARM"]["SEQUENCE1"]["LAYER1"]["TCONFIGURE"]["ASYNCHRONOUS"]["OLINE"]
        gCommandTree["ARM"]["SEQUENCE1"]["LAYER1"]["TCONFIGURE"]["OUTPUT"] = gCommandTree["ARM"]["SEQUENCE1"]["LAYER1"]["TCONFIGURE"]["ASYNCHRONOUS"]["OUTPUT"]
        gCommandTree["ARM"]["SEQUENCE1"]["OLINE"] = gCommandTree["ARM"]["SEQUENCE1"]["LAYER1"]["TCONFIGURE"]["ASYNCHRONOUS"]["OLINE"]
        gCommandTree["ARM"]["SEQUENCE1"]["OUTPUT"] = gCommandTree["ARM"]["SEQUENCE1"]["LAYER1"]["TCONFIGURE"]["ASYNCHRONOUS"]["OUTPUT"]
        gCommandTree["ARM"]["SEQUENCE1"]["SOURCE"] = gCommandTree["ARM"]["SEQUENCE1"]["LAYER1"]["SOURCE"]
        gCommandTree["ARM"]["SEQUENCE1"]["TCONFIGURE"] = gCommandTree["ARM"]["SEQUENCE1"]["LAYER1"]["TCONFIGURE"]
        gCommandTree["ARM"]["SEQUENCE1"]["TIMER"] = gCommandTree["ARM"]["SEQUENCE1"]["LAYER1"]["TIMER"]
        gCommandTree["ARM"]["SOURCE"] = gCommandTree["ARM"]["SEQUENCE1"]["LAYER1"]["SOURCE"]
        gCommandTree["ARM"]["TCONFIGURE"] = gCommandTree["ARM"]["SEQUENCE1"]["LAYER1"]["TCONFIGURE"]
        gCommandTree["ARM"]["TIMER"] = gCommandTree["ARM"]["SEQUENCE1"]["LAYER1"]["TIMER"]
        gCommandTree["AVERAGE"] = gCommandTree["SENSE1"]["AVERAGE"]
        gCommandTree["CURRENT"] = gCommandTree["SENSE1"]["CURRENT"]
        gCommandTree["CALCULATE1"]["MATH"].mCommand = gCommandTree["CALCULATE1"]["MATH"]["EXPRESSION"]["DEFINE"].mCommand
        gCommandTree["CALCULATE1"]["MATH"].mQuery = gCommandTree["CALCULATE1"]["MATH"]["EXPRESSION"]["DEFINE"].mQuery
        gCommandTree["CALCULATE1"]["MATH"]["DEFINE"] = gCommandTree["CALCULATE1"]["MATH"]["EXPRESSION"]["DEFINE"]
        gCommandTree["CALCULATE1"]["MATH"]["DELETE"] = gCommandTree["CALCULATE1"]["MATH"]["EXPRESSION"]["DELETE"]
        gCommandTree["CALCULATE1"]["MATH"]["CATALOG"] = gCommandTree["CALCULATE1"]["MATH"]["EXPRESSION"]["CATALOG"]
        gCommandTree["CALCULATE1"]["MATH"]["EXPRESSION"].mCommand = gCommandTree["CALCULATE1"]["MATH"]["EXPRESSION"]["DEFINE"].mCommand
        gCommandTree["CALCULATE1"]["MATH"]["EXPRESSION"].mQuery = gCommandTree["CALCULATE1"]["MATH"]["EXPRESSION"]["DEFINE"].mQuery
        gCommandTree["CALCULATE1"]["MATH"]["EXPRESSION"]["DELETE"].mCommand = gCommandTree["CALCULATE1"]["MATH"]["EXPRESSION"]["DELETE"]["SELECTED"].mCommand
        gCommandTree["CALCULATE1"]["MATH"]["NAME"] = gCommandTree["CALCULATE1"]["MATH"]["EXPRESSION"]["NAME"]
        gCommandTree["CALCULATE2"]["CLIMITS"]["CLEAR"].mCommand = gCommandTree["CALCULATE2"]["CLIMITS"]["CLEAR"]["IMMEDIATE"].mCommand
        gCommandTree["CALCULATE2"]["LIMIT2"]["LOWER"].mCommand = gCommandTree["CALCULATE2"]["LIMIT2"]["LOWER"]["DATA"].mCommand
        gCommandTree["CALCULATE2"]["LIMIT2"]["LOWER"].mQuery = gCommandTree["CALCULATE2"]["LIMIT2"]["LOWER"]["DATA"].mQuery
        gCommandTree["CALCULATE2"]["LIMIT2"]["UPPER"].mCommand = gCommandTree["CALCULATE2"]["LIMIT2"]["UPPER"]["DATA"].mCommand
        gCommandTree["CALCULATE2"]["LIMIT2"]["UPPER"].mQuery = gCommandTree["CALCULATE2"]["LIMIT2"]["UPPER"]["DATA"].mQuery
        gCommandTree["CALCULATE2"]["LIMIT3"]["LOWER"].mCommand = gCommandTree["CALCULATE2"]["LIMIT3"]["LOWER"]["DATA"].mCommand
        gCommandTree["CALCULATE2"]["LIMIT3"]["LOWER"].mQuery = gCommandTree["CALCULATE2"]["LIMIT3"]["LOWER"]["DATA"].mQuery
        gCommandTree["CALCULATE2"]["LIMIT3"]["UPPER"].mCommand = gCommandTree["CALCULATE2"]["LIMIT3"]["UPPER"]["DATA"].mCommand
        gCommandTree["CALCULATE2"]["LIMIT3"]["UPPER"].mQuery = gCommandTree["CALCULATE2"]["LIMIT3"]["UPPER"]["DATA"].mQuery
        gCommandTree["CALCULATE2"]["LIMIT5"]["LOWER"].mCommand = gCommandTree["CALCULATE2"]["LIMIT5"]["LOWER"]["DATA"].mCommand
        gCommandTree["CALCULATE2"]["LIMIT5"]["LOWER"].mQuery = gCommandTree["CALCULATE2"]["LIMIT5"]["LOWER"]["DATA"].mQuery
        gCommandTree["CALCULATE2"]["LIMIT5"]["UPPER"].mCommand = gCommandTree["CALCULATE2"]["LIMIT5"]["UPPER"]["DATA"].mCommand
        gCommandTree["CALCULATE2"]["LIMIT5"]["UPPER"].mQuery = gCommandTree["CALCULATE2"]["LIMIT5"]["UPPER"]["DATA"].mQuery
        gCommandTree["CALCULATE2"]["LIMIT6"]["LOWER"].mCommand = gCommandTree["CALCULATE2"]["LIMIT6"]["LOWER"]["DATA"].mCommand
        gCommandTree["CALCULATE2"]["LIMIT6"]["LOWER"].mQuery = gCommandTree["CALCULATE2"]["LIMIT6"]["LOWER"]["DATA"].mQuery
        gCommandTree["CALCULATE2"]["LIMIT6"]["UPPER"].mCommand = gCommandTree["CALCULATE2"]["LIMIT6"]["UPPER"]["DATA"].mCommand
        gCommandTree["CALCULATE2"]["LIMIT6"]["UPPER"].mQuery = gCommandTree["CALCULATE2"]["LIMIT6"]["UPPER"]["DATA"].mQuery
        gCommandTree["CALCULATE2"]["LIMIT7"]["LOWER"].mCommand = gCommandTree["CALCULATE2"]["LIMIT7"]["LOWER"]["DATA"].mCommand
        gCommandTree["CALCULATE2"]["LIMIT7"]["LOWER"].mQuery = gCommandTree["CALCULATE2"]["LIMIT7"]["LOWER"]["DATA"].mQuery
        gCommandTree["CALCULATE2"]["LIMIT7"]["UPPER"].mCommand = gCommandTree["CALCULATE2"]["LIMIT7"]["UPPER"]["DATA"].mCommand
        gCommandTree["CALCULATE2"]["LIMIT7"]["UPPER"].mQuery = gCommandTree["CALCULATE2"]["LIMIT7"]["UPPER"]["DATA"].mQuery
        gCommandTree["CALCULATE2"]["LIMIT8"]["LOWER"].mCommand = gCommandTree["CALCULATE2"]["LIMIT8"]["LOWER"]["DATA"].mCommand
        gCommandTree["CALCULATE2"]["LIMIT8"]["LOWER"].mQuery = gCommandTree["CALCULATE2"]["LIMIT8"]["LOWER"]["DATA"].mQuery
        gCommandTree["CALCULATE2"]["LIMIT8"]["UPPER"].mCommand = gCommandTree["CALCULATE2"]["LIMIT8"]["UPPER"]["DATA"].mCommand
        gCommandTree["CALCULATE2"]["LIMIT8"]["UPPER"].mQuery = gCommandTree["CALCULATE2"]["LIMIT8"]["UPPER"]["DATA"].mQuery
        gCommandTree["CALCULATE2"]["LIMIT9"]["LOWER"].mCommand = gCommandTree["CALCULATE2"]["LIMIT9"]["LOWER"]["DATA"].mCommand
        gCommandTree["CALCULATE2"]["LIMIT9"]["LOWER"].mQuery = gCommandTree["CALCULATE2"]["LIMIT9"]["LOWER"]["DATA"].mQuery
        gCommandTree["CALCULATE2"]["LIMIT9"]["UPPER"].mCommand = gCommandTree["CALCULATE2"]["LIMIT9"]["UPPER"]["DATA"].mCommand
        gCommandTree["CALCULATE2"]["LIMIT9"]["UPPER"].mQuery = gCommandTree["CALCULATE2"]["LIMIT9"]["UPPER"]["DATA"].mQuery
        gCommandTree["CALCULATE2"]["LIMIT10"]["LOWER"].mCommand = gCommandTree["CALCULATE2"]["LIMIT10"]["LOWER"]["DATA"].mCommand
        gCommandTree["CALCULATE2"]["LIMIT10"]["LOWER"].mQuery = gCommandTree["CALCULATE2"]["LIMIT10"]["LOWER"]["DATA"].mQuery
        gCommandTree["CALCULATE2"]["LIMIT10"]["UPPER"].mCommand = gCommandTree["CALCULATE2"]["LIMIT10"]["UPPER"]["DATA"].mCommand
        gCommandTree["CALCULATE2"]["LIMIT10"]["UPPER"].mQuery = gCommandTree["CALCULATE2"]["LIMIT10"]["UPPER"]["DATA"].mQuery
        gCommandTree["CALCULATE2"]["LIMIT11"]["LOWER"].mCommand = gCommandTree["CALCULATE2"]["LIMIT11"]["LOWER"]["DATA"].mCommand
        gCommandTree["CALCULATE2"]["LIMIT11"]["LOWER"].mQuery = gCommandTree["CALCULATE2"]["LIMIT11"]["LOWER"]["DATA"].mQuery
        gCommandTree["CALCULATE2"]["LIMIT11"]["UPPER"].mCommand = gCommandTree["CALCULATE2"]["LIMIT11"]["UPPER"]["DATA"].mCommand
        gCommandTree["CALCULATE2"]["LIMIT11"]["UPPER"].mQuery = gCommandTree["CALCULATE2"]["LIMIT11"]["UPPER"]["DATA"].mQuery
        gCommandTree["CALCULATE2"]["LIMIT12"]["LOWER"].mCommand = gCommandTree["CALCULATE2"]["LIMIT12"]["LOWER"]["DATA"].mCommand
        gCommandTree["CALCULATE2"]["LIMIT12"]["LOWER"].mQuery = gCommandTree["CALCULATE2"]["LIMIT12"]["LOWER"]["DATA"].mQuery
        gCommandTree["CALCULATE2"]["LIMIT12"]["UPPER"].mCommand = gCommandTree["CALCULATE2"]["LIMIT12"]["UPPER"]["DATA"].mCommand
        gCommandTree["CALCULATE2"]["LIMIT12"]["UPPER"].mQuery = gCommandTree["CALCULATE2"]["LIMIT12"]["UPPER"]["DATA"].mQuery
        gCommandTree["CONFIGURE"].mQuery = gCommandTree["SENSE1"]["FUNCTION"]["ON"].mQuery
        gCommandTree["CONFIGURE"]["CURRENT"].mCommand = gCommandTree["CONFIGURE"]["CURRENT"]["DC"].mCommand
        gCommandTree["CONFIGURE"]["VOLTAGE"].mCommand = gCommandTree["CONFIGURE"]["VOLTAGE"]["DC"].mCommand
        gCommandTree["DATA"].mQuery = gCommandTree["SENSE1"]["DATA"]["LATEST"].mQuery
        gCommandTree["DATA"]["CLEAR"] = gCommandTree["TRACE"]["CLEAR"]
        gCommandTree["DATA"]["DATA"] = gCommandTree["TRACE"]["DATA"]
        gCommandTree["DATA"]["FEED"] = gCommandTree["TRACE"]["FEED"]
        gCommandTree["DATA"]["FREE"] = gCommandTree["TRACE"]["FREE"]
        gCommandTree["DATA"]["LATEST"] = gCommandTree["SENSE1"]["DATA"]["LATEST"]
        gCommandTree["DATA"]["POINTS"] = gCommandTree["TRACE"]["POINTS"]
        gCommandTree["DATA"]["TSTAMP"] = gCommandTree["TRACE"]["TSTAMP"]
        gCommandTree["DISPLAY"]["ATTRIBUTES"] = gCommandTree["DISPLAY"]["WINDOW1"]["ATTRIBUTES"]
        gCommandTree["DISPLAY"]["DATA"] = gCommandTree["DISPLAY"]["WINDOW1"]["DATA"]
        gCommandTree["DISPLAY"]["TEXT"] = gCommandTree["DISPLAY"]["WINDOW1"]["TEXT"]
        gCommandTree["DISPLAY"]["WINDOW1"]["TEXT"].mCommand = gCommandTree["DISPLAY"]["WINDOW1"]["TEXT"]["DATA"].mCommand
        gCommandTree["DISPLAY"]["WINDOW1"]["TEXT"].mQuery = gCommandTree["DISPLAY"]["WINDOW1"]["TEXT"]["DATA"].mQuery
        gCommandTree["DISPLAY"]["WINDOW2"]["TEXT"].mCommand = gCommandTree["DISPLAY"]["WINDOW2"]["TEXT"]["DATA"].mCommand
        gCommandTree["DISPLAY"]["WINDOW2"]["TEXT"].mQuery = gCommandTree["DISPLAY"]["WINDOW2"]["TEXT"]["DATA"].mQuery
        gCommandTree["FORMAT"].mCommand = gCommandTree["FORMAT"]["DATA"].mCommand
        gCommandTree["FORMAT"].mQuery = gCommandTree["FORMAT"]["DATA"].mQuery
        gCommandTree["FORMAT"]["ELEMENTS"].mCommand = gCommandTree["FORMAT"]["ELEMENTS"]["SENSE1"].mCommand
        gCommandTree["FORMAT"]["ELEMENTS"].mQuery = gCommandTree["FORMAT"]["ELEMENTS"]["SENSE1"].mQuery
        gCommandTree["FUNCTION"] = gCommandTree["SENSE1"]["FUNCTION"]
        gCommandTree["INITIATE"].mCommand = gCommandTree["INITIATE"]["IMMEDIATE"].mCommand
        gCommandTree["MEASURE"]["CURRENT"].mQuery = gCommandTree["MEASURE"]["CURRENT"]["DC"].mQuery
        gCommandTree["MEASURE"]["VOLTAGE"].mQuery = gCommandTree["MEASURE"]["VOLTAGE"]["DC"].mQuery
        gCommandTree["OUTPUT1"].mCommand = gCommandTree["OUTPUT1"]["STATE"].mCommand
        gCommandTree["OUTPUT1"].mQuery = gCommandTree["OUTPUT1"]["STATE"].mQuery
        gCommandTree["OUTPUT1"]["ENABLE"].mCommand = gCommandTree["OUTPUT1"]["ENABLE"]["STATE"].mCommand
        gCommandTree["OUTPUT1"]["ENABLE"].mQuery = gCommandTree["OUTPUT1"]["ENABLE"]["STATE"].mQuery
        gCommandTree["RESISTANCE"] = gCommandTree["SENSE1"]["RESISTANCE"]
        gCommandTree["SENSE1"]["AVERAGE"].mCommand = gCommandTree["SENSE1"]["AVERAGE"]["STATE"].mCommand
        gCommandTree["SENSE1"]["AVERAGE"].mQuery = gCommandTree["SENSE1"]["AVERAGE"]["STATE"].mQuery
        gCommandTree["SENSE1"]["CURRENT"]["DC"]["PROTECTION"].mCommand = gCommandTree["SENSE1"]["CURRENT"]["DC"]["PROTECTION"]["LEVEL"].mCommand
        gCommandTree["SENSE1"]["CURRENT"]["DC"]["PROTECTION"].mQuery = gCommandTree["SENSE1"]["CURRENT"]["DC"]["PROTECTION"]["LEVEL"].mQuery
        gCommandTree["SENSE1"]["CURRENT"]["DC"]["RANGE"].mCommand = gCommandTree["SENSE1"]["CURRENT"]["DC"]["RANGE"]["UPPER"].mCommand
        gCommandTree["SENSE1"]["CURRENT"]["DC"]["RANGE"].mQuery = gCommandTree["SENSE1"]["CURRENT"]["DC"]["RANGE"]["UPPER"].mQuery
        gCommandTree["SENSE1"]["CURRENT"]["NPLCYCLES"] = gCommandTree["SENSE1"]["CURRENT"]["DC"]["NPLCYCLES"]
        gCommandTree["SENSE1"]["CURRENT"]["PROTECTION"] = gCommandTree["SENSE1"]["CURRENT"]["DC"]["PROTECTION"]
        gCommandTree["SENSE1"]["CURRENT"]["RANGE"] = gCommandTree["SENSE1"]["CURRENT"]["DC"]["RANGE"]
        gCommandTree["SENSE1"]["DATA"].mQuery = gCommandTree["SENSE1"]["DATA"]["LATEST"].mQuery
        gCommandTree["SENSE1"]["FUNCTION"].mCommand = gCommandTree["SENSE1"]["FUNCTION"]["ON"].mCommand
        gCommandTree["SENSE1"]["FUNCTION"].mQuery = gCommandTree["SENSE1"]["FUNCTION"]["ON"].mQuery
        gCommandTree["SENSE1"]["FUNCTION"]["ALL"] = gCommandTree["SENSE1"]["FUNCTION"]["ON"]["ALL"]
        gCommandTree["SENSE1"]["FUNCTION"]["COUNT"] = gCommandTree["SENSE1"]["FUNCTION"]["ON"]["COUNT"]
        gCommandTree["SENSE1"]["RESISTANCE"]["NPLCYCLES"] = gCommandTree["SENSE1"]["CURRENT"]["DC"]["NPLCYCLES"]
        gCommandTree["SENSE1"]["RESISTANCE"]["RANGE"].mCommand = gCommandTree["SENSE1"]["RESISTANCE"]["RANGE"]["UPPER"].mCommand
        gCommandTree["SENSE1"]["RESISTANCE"]["RANGE"].mQuery = gCommandTree["SENSE1"]["RESISTANCE"]["RANGE"]["UPPER"].mQuery
        gCommandTree["SENSE1"]["RESISTANCE"]["RANGE"]["AUTO"] = gCommandTree["SENSE1"]["RESISTANCE"]["RANGE"]["UPPER"]["AUTO"]
        gCommandTree["SENSE1"]["VOLTAGE"]["DC"]["NPLCYCLES"] = gCommandTree["SENSE1"]["CURRENT"]["DC"]["NPLCYCLES"]
        gCommandTree["SENSE1"]["VOLTAGE"]["DC"]["PROTECTION"].mCommand = gCommandTree["SENSE1"]["VOLTAGE"]["DC"]["PROTECTION"]["LEVEL"].mCommand
        gCommandTree["SENSE1"]["VOLTAGE"]["DC"]["PROTECTION"].mQuery = gCommandTree["SENSE1"]["VOLTAGE"]["DC"]["PROTECTION"]["LEVEL"].mQuery
        gCommandTree["SENSE1"]["VOLTAGE"]["DC"]["RANGE"].mCommand = gCommandTree["SENSE1"]["VOLTAGE"]["DC"]["RANGE"]["UPPER"].mCommand
        gCommandTree["SENSE1"]["VOLTAGE"]["DC"]["RANGE"].mQuery = gCommandTree["SENSE1"]["VOLTAGE"]["DC"]["RANGE"]["UPPER"].mQuery
        gCommandTree["SENSE1"]["VOLTAGE"]["NPLCYCLES"] = gCommandTree["SENSE1"]["CURRENT"]["DC"]["NPLCYCLES"]
        gCommandTree["SENSE1"]["VOLTAGE"]["PROTECTION"] = gCommandTree["SENSE1"]["VOLTAGE"]["DC"]["PROTECTION"]
        gCommandTree["SENSE1"]["VOLTAGE"]["RANGE"] = gCommandTree["SENSE1"]["VOLTAGE"]["DC"]["RANGE"]
        gCommandTree["SOURCE1"]["CLEAR"].mCommand = gCommandTree["SOURCE1"]["CLEAR"]["IMMEDIATE"].mCommand
        gCommandTree["SOURCE1"]["CURRENT"].mCommand = gCommandTree["SOURCE1"]["CURRENT"]["LEVEL"]["IMMEDIATE"]["AMPLITUDE"].mCommand
        gCommandTree["SOURCE1"]["CURRENT"].mQuery = gCommandTree["SOURCE1"]["CURRENT"]["LEVEL"]["IMMEDIATE"]["AMPLITUDE"].mQuery
        gCommandTree["SOURCE1"]["CURRENT"]["AMPLITUDE"] = gCommandTree["SOURCE1"]["CURRENT"]["LEVEL"]["IMMEDIATE"]["AMPLITUDE"]
        gCommandTree["SOURCE1"]["CURRENT"]["IMMEDIATE"] = gCommandTree["SOURCE1"]["CURRENT"]["LEVEL"]["IMMEDIATE"]
        gCommandTree["SOURCE1"]["CURRENT"]["LEVEL"].mCommand = gCommandTree["SOURCE1"]["CURRENT"]["LEVEL"]["IMMEDIATE"]["AMPLITUDE"].mCommand
        gCommandTree["SOURCE1"]["CURRENT"]["LEVEL"].mQuery = gCommandTree["SOURCE1"]["CURRENT"]["LEVEL"]["IMMEDIATE"]["AMPLITUDE"].mQuery
        gCommandTree["SOURCE1"]["CURRENT"]["LEVEL"]["AMPLITUDE"] = gCommandTree["SOURCE1"]["CURRENT"]["LEVEL"]["IMMEDIATE"]["AMPLITUDE"]
        gCommandTree["SOURCE1"]["CURRENT"]["LEVEL"]["IMMEDIATE"].mCommand = gCommandTree["SOURCE1"]["CURRENT"]["LEVEL"]["IMMEDIATE"]["AMPLITUDE"].mCommand
        gCommandTree["SOURCE1"]["CURRENT"]["LEVEL"]["IMMEDIATE"].mQuery = gCommandTree["SOURCE1"]["CURRENT"]["LEVEL"]["IMMEDIATE"]["AMPLITUDE"].mQuery
        gCommandTree["SOURCE1"]["CURRENT"]["LEVEL"]["TRIGGERED"].mCommand = gCommandTree["SOURCE1"]["CURRENT"]["LEVEL"]["TRIGGERED"]["AMPLITUDE"].mCommand
        gCommandTree["SOURCE1"]["CURRENT"]["LEVEL"]["TRIGGERED"].mQuery = gCommandTree["SOURCE1"]["CURRENT"]["LEVEL"]["TRIGGERED"]["AMPLITUDE"].mQuery
        gCommandTree["SOURCE1"]["CURRENT"]["TRIGGERED"] = gCommandTree["SOURCE1"]["CURRENT"]["LEVEL"]["TRIGGERED"]
        gCommandTree["SOURCE1"]["FUNCTION"].mCommand = gCommandTree["SOURCE1"]["FUNCTION"]["MODE"].mCommand
        gCommandTree["SOURCE1"]["FUNCTION"].mQuery = gCommandTree["SOURCE1"]["FUNCTION"]["MODE"].mQuery
        gCommandTree["SOURCE1"]["VOLTAGE"].mCommand = gCommandTree["SOURCE1"]["VOLTAGE"]["LEVEL"]["IMMEDIATE"]["AMPLITUDE"].mCommand
        gCommandTree["SOURCE1"]["VOLTAGE"].mQuery = gCommandTree["SOURCE1"]["VOLTAGE"]["LEVEL"]["IMMEDIATE"]["AMPLITUDE"].mQuery
        gCommandTree["SOURCE1"]["VOLTAGE"]["AMPLITUDE"] = gCommandTree["SOURCE1"]["VOLTAGE"]["LEVEL"]["IMMEDIATE"]["AMPLITUDE"]
        gCommandTree["SOURCE1"]["VOLTAGE"]["IMMEDIATE"] = gCommandTree["SOURCE1"]["VOLTAGE"]["LEVEL"]["IMMEDIATE"]
        gCommandTree["SOURCE1"]["VOLTAGE"]["LEVEL"].mCommand = gCommandTree["SOURCE1"]["VOLTAGE"]["LEVEL"]["IMMEDIATE"]["AMPLITUDE"].mCommand
        gCommandTree["SOURCE1"]["VOLTAGE"]["LEVEL"].mQuery = gCommandTree["SOURCE1"]["VOLTAGE"]["LEVEL"]["IMMEDIATE"]["AMPLITUDE"].mQuery
        gCommandTree["SOURCE1"]["VOLTAGE"]["LEVEL"]["AMPLITUDE"] = gCommandTree["SOURCE1"]["VOLTAGE"]["LEVEL"]["IMMEDIATE"]["AMPLITUDE"]
        gCommandTree["SOURCE1"]["VOLTAGE"]["LEVEL"]["IMMEDIATE"].mCommand = gCommandTree["SOURCE1"]["VOLTAGE"]["LEVEL"]["IMMEDIATE"]["AMPLITUDE"].mCommand
        gCommandTree["SOURCE1"]["VOLTAGE"]["LEVEL"]["IMMEDIATE"].mQuery = gCommandTree["SOURCE1"]["VOLTAGE"]["LEVEL"]["IMMEDIATE"]["AMPLITUDE"].mQuery
        gCommandTree["SOURCE1"]["VOLTAGE"]["LEVEL"]["TRIGGERED"].mCommand = gCommandTree["SOURCE1"]["VOLTAGE"]["LEVEL"]["TRIGGERED"]["AMPLITUDE"].mCommand
        gCommandTree["SOURCE1"]["VOLTAGE"]["LEVEL"]["TRIGGERED"].mQuery = gCommandTree["SOURCE1"]["VOLTAGE"]["LEVEL"]["TRIGGERED"]["AMPLITUDE"].mQuery
        gCommandTree["SOURCE1"]["VOLTAGE"]["TRIGGERED"] = gCommandTree["SOURCE1"]["VOLTAGE"]["LEVEL"]["TRIGGERED"]
        
        if gDigioSupport then
            gCommandTree["SOURCE2"]["CLEAR"].mCommand = gCommandTree["SOURCE2"]["CLEAR"]["IMMEDIATE"].mCommand
            gCommandTree["SOURCE2"]["TTL"].mCommand = gCommandTree["SOURCE2"]["TTL"]["LEVEL"].mCommand
            gCommandTree["SOURCE2"]["TTL"].mQuery = gCommandTree["SOURCE2"]["TTL"]["LEVEL"].mQuery
            gCommandTree["SOURCE2"]["TTL"]["ACTUAL"] = gCommandTree["SOURCE2"]["TTL"]["LEVEL"]["ACTUAL"]
            gCommandTree["SOURCE2"]["TTL"]["DEFAULT"].mCommand = gCommandTree["SOURCE2"]["TTL"]["LEVEL"].mCommand
            gCommandTree["SOURCE2"]["TTL"]["DEFAULT"].mQuery = gCommandTree["SOURCE2"]["TTL"]["LEVEL"].mQuery
        end
        
        gCommandTree["STATUS"]["MEASUREMENT"].mQuery = gCommandTree["STATUS"]["MEASUREMENT"]["EVENT"].mQuery
        gCommandTree["STATUS"]["OPERATION"].mQuery = gCommandTree["STATUS"]["OPERATION"]["EVENT"].mQuery
        gCommandTree["STATUS"]["QUESTIONABLE"].mQuery = gCommandTree["STATUS"]["QUESTIONABLE"]["EVENT"].mQuery
        gCommandTree["STATUS"]["QUEUE"].mQuery = gCommandTree["STATUS"]["QUEUE"]["NEXT"].mQuery
        gCommandTree["SYSTEM"]["AZERO"].mCommand = gCommandTree["SYSTEM"]["AZERO"]["STATE"].mCommand
        gCommandTree["SYSTEM"]["AZERO"].mQuery = gCommandTree["SYSTEM"]["AZERO"]["STATE"].mQuery
        gCommandTree["SYSTEM"]["AZERO"]["CACHING"].mCommand = gCommandTree["SYSTEM"]["AZERO"]["CACHING"]["STATE"].mCommand
        gCommandTree["SYSTEM"]["AZERO"]["CACHING"].mQuery = gCommandTree["SYSTEM"]["AZERO"]["CACHING"]["STATE"].mQuery
        gCommandTree["SYSTEM"]["BEEPER"].mCommand = gCommandTree["SYSTEM"]["BEEPER"]["IMMEDIATE"].mCommand
        gCommandTree["SYSTEM"]["ERROR"].mQuery = gCommandTree["SYSTEM"]["ERROR"]["NEXT"].mQuery
        gCommandTree["SYSTEM"]["ERROR"]["CODE"].mQuery = gCommandTree["SYSTEM"]["ERROR"]["CODE"]["NEXT"].mQuery
        gCommandTree["SYSTEM"]["MEP"].mQuery = gCommandTree["SYSTEM"]["MEP"]["STATE"].mQuery
        gCommandTree["TRACE"]["TSTAMP"].mCommand = gCommandTree["TRACE"]["TSTAMP"]["FORMAT"].mCommand
        gCommandTree["TRACE"]["TSTAMP"].mQuery = gCommandTree["TRACE"]["TSTAMP"]["FORMAT"].mQuery
        gCommandTree["TRIGGER"]["COUNT"] = gCommandTree["TRIGGER"]["SEQUENCE1"]["COUNT"]
        gCommandTree["TRIGGER"]["DELAY"] = gCommandTree["TRIGGER"]["SEQUENCE1"]["DELAY"]
        gCommandTree["TRIGGER"]["DIRECTION"] = gCommandTree["TRIGGER"]["SEQUENCE1"]["TCONFIGURE"]["DIRECTION"]
        gCommandTree["TRIGGER"]["ILINE"] = gCommandTree["TRIGGER"]["SEQUENCE1"]["TCONFIGURE"]["ASYNCHRONOUS"]["ILINE"]
        gCommandTree["TRIGGER"]["INPUT"] = gCommandTree["TRIGGER"]["SEQUENCE1"]["TCONFIGURE"]["ASYNCHRONOUS"]["INPUT"]
        gCommandTree["TRIGGER"]["OLINE"] = gCommandTree["TRIGGER"]["SEQUENCE1"]["TCONFIGURE"]["ASYNCHRONOUS"]["OLINE"]
        gCommandTree["TRIGGER"]["OUTPUT"] = gCommandTree["TRIGGER"]["SEQUENCE1"]["TCONFIGURE"]["ASYNCHRONOUS"]["OUTPUT"]
        gCommandTree["TRIGGER"]["SOURCE"] = gCommandTree["TRIGGER"]["SEQUENCE1"]["SOURCE"]
        gCommandTree["TRIGGER"]["SEQUENCE1"]["ASYNCHRONOUS"] = gCommandTree["TRIGGER"]["SEQUENCE1"]["TCONFIGURE"]["ASYNCHRONOUS"]
        gCommandTree["TRIGGER"]["SEQUENCE1"]["DIRECTION"] = gCommandTree["TRIGGER"]["SEQUENCE1"]["TCONFIGURE"]["DIRECTION"]
        gCommandTree["TRIGGER"]["SEQUENCE1"]["ILINE"] = gCommandTree["TRIGGER"]["SEQUENCE1"]["TCONFIGURE"]["ASYNCHRONOUS"]["ILINE"]
        gCommandTree["TRIGGER"]["SEQUENCE1"]["INPUT"] = gCommandTree["TRIGGER"]["SEQUENCE1"]["TCONFIGURE"]["ASYNCHRONOUS"]["INPUT"]
        gCommandTree["TRIGGER"]["SEQUENCE1"]["OLINE"] = gCommandTree["TRIGGER"]["SEQUENCE1"]["TCONFIGURE"]["ASYNCHRONOUS"]["OLINE"]
        gCommandTree["TRIGGER"]["SEQUENCE1"]["OUTPUT"] = gCommandTree["TRIGGER"]["SEQUENCE1"]["TCONFIGURE"]["ASYNCHRONOUS"]["OUTPUT"]
        gCommandTree["TRIGGER"]["SEQUENCE1"]["TCONFIGURE"]["ILINE"] = gCommandTree["TRIGGER"]["SEQUENCE1"]["TCONFIGURE"]["ASYNCHRONOUS"]["ILINE"]
        gCommandTree["TRIGGER"]["SEQUENCE1"]["TCONFIGURE"]["INPUT"] = gCommandTree["TRIGGER"]["SEQUENCE1"]["TCONFIGURE"]["ASYNCHRONOUS"]["INPUT"]
        gCommandTree["TRIGGER"]["SEQUENCE1"]["TCONFIGURE"]["OLINE"] = gCommandTree["TRIGGER"]["SEQUENCE1"]["TCONFIGURE"]["ASYNCHRONOUS"]["OLINE"]
        gCommandTree["TRIGGER"]["SEQUENCE1"]["TCONFIGURE"]["OUTPUT"] = gCommandTree["TRIGGER"]["SEQUENCE1"]["TCONFIGURE"]["ASYNCHRONOUS"]["OUTPUT"]
        gCommandTree["TRIGGER"]["TCONFIGURE"] = gCommandTree["TRIGGER"]["SEQUENCE1"]["TCONFIGURE"]
        gCommandTree["VOLTAGE"] = gCommandTree["SENSE1"]["VOLTAGE"]
        
        -- Short forms
        gCommandTree["ABOR"] = gCommandTree["ABORT"]
        gCommandTree["ARM"]["ASYN"] = gCommandTree["ARM"]["ASYNCHRONOUS"]
        gCommandTree["ARM"]["COUN"] = gCommandTree["ARM"]["COUNT"]
        gCommandTree["ARM"]["DIR"] = gCommandTree["ARM"]["DIRECTION"]
        gCommandTree["ARM"]["ILIN"] = gCommandTree["ARM"]["ILINE"]
        gCommandTree["ARM"]["LAY"] = gCommandTree["ARM"]["LAYER1"]
        gCommandTree["ARM"]["LAY1"] = gCommandTree["ARM"]["LAYER1"]
        gCommandTree["ARM"]["LAYER"] = gCommandTree["ARM"]["LAYER1"]
        gCommandTree["ARM"]["OLIN"] = gCommandTree["ARM"]["OLINE"]
        gCommandTree["ARM"]["OUTP"] = gCommandTree["ARM"]["OUTPUT"]
        gCommandTree["ARM"]["SEQ"] = gCommandTree["ARM"]["SEQUENCE1"]
        gCommandTree["ARM"]["SEQ1"] = gCommandTree["ARM"]["SEQUENCE1"]
        gCommandTree["ARM"]["SEQUENCE"] = gCommandTree["ARM"]["SEQUENCE1"]
        gCommandTree["ARM"]["SEQ"]["ASYN"] = gCommandTree["ARM"]["SEQ"]["ASYNCHRONOUS"]
        gCommandTree["ARM"]["SEQ"]["COUN"] = gCommandTree["ARM"]["SEQ"]["COUNT"]
        gCommandTree["ARM"]["SEQ"]["DIR"] = gCommandTree["ARM"]["SEQ"]["DIRECTION"]
        gCommandTree["ARM"]["SEQ"]["ILIN"] = gCommandTree["ARM"]["SEQ"]["ILINE"]
        gCommandTree["ARM"]["SEQ"]["LAY"] = gCommandTree["ARM"]["SEQ"]["LAYER1"]
        gCommandTree["ARM"]["SEQ"]["LAY1"] = gCommandTree["ARM"]["SEQ"]["LAYER1"]
        gCommandTree["ARM"]["SEQ"]["LAYER"] = gCommandTree["ARM"]["SEQ"]["LAYER1"]
        gCommandTree["ARM"]["SEQ"]["LAY"]["ASYN"] = gCommandTree["ARM"]["SEQ"]["LAY"]["ASYNCHRONOUS"]
        gCommandTree["ARM"]["SEQ"]["LAY"]["COUN"] = gCommandTree["ARM"]["SEQ"]["LAY"]["COUNT"]
        gCommandTree["ARM"]["SEQ"]["LAY"]["DIR"] = gCommandTree["ARM"]["SEQ"]["LAY"]["DIRECTION"]
        gCommandTree["ARM"]["SEQ"]["LAY"]["ILIN"] = gCommandTree["ARM"]["SEQ"]["LAY"]["ILINE"]
        gCommandTree["ARM"]["SEQ"]["LAY"]["OLIN"] = gCommandTree["ARM"]["SEQ"]["LAY"]["OLINE"]
        gCommandTree["ARM"]["SEQ"]["LAY"]["OUTP"] = gCommandTree["ARM"]["SEQ"]["LAY"]["OUTPUT"]
        gCommandTree["ARM"]["SEQ"]["LAY"]["SOUR"] = gCommandTree["ARM"]["SEQ"]["LAY"]["SOURCE"]
        gCommandTree["ARM"]["SEQ"]["LAY"]["TCON"] = gCommandTree["ARM"]["SEQ"]["LAY"]["TCONFIGURE"]
        gCommandTree["ARM"]["SEQ"]["LAY"]["TCON"]["ASYN"] = gCommandTree["ARM"]["SEQ"]["LAY"]["TCON"]["ASYNCHRONOUS"]
        gCommandTree["ARM"]["SEQ"]["LAY"]["TCON"]["ASYN"]["ILIN"] = gCommandTree["ARM"]["SEQ"]["LAY"]["TCON"]["ASYN"]["ILINE"]
        gCommandTree["ARM"]["SEQ"]["LAY"]["TCON"]["ASYN"]["OLIN"] = gCommandTree["ARM"]["SEQ"]["LAY"]["TCON"]["ASYN"]["OLINE"]
        gCommandTree["ARM"]["SEQ"]["LAY"]["TCON"]["ASYN"]["OUTP"] = gCommandTree["ARM"]["SEQ"]["LAY"]["TCON"]["ASYN"]["OUTPUT"]
        gCommandTree["ARM"]["SEQ"]["LAY"]["TCON"]["DIR"] = gCommandTree["ARM"]["SEQ"]["LAY"]["TCON"]["DIRECTION"]
        gCommandTree["ARM"]["SEQ"]["LAY"]["TCON"]["ILIN"] = gCommandTree["ARM"]["SEQ"]["LAY"]["TCON"]["ILINE"]
        gCommandTree["ARM"]["SEQ"]["LAY"]["TCON"]["OLIN"] = gCommandTree["ARM"]["SEQ"]["LAY"]["TCON"]["OLINE"]
        gCommandTree["ARM"]["SEQ"]["LAY"]["TCON"]["OUTP"] = gCommandTree["ARM"]["SEQ"]["LAY"]["TCON"]["OUTPUT"]
        gCommandTree["ARM"]["SEQ"]["LAY"]["TIM"] = gCommandTree["ARM"]["SEQ"]["LAY"]["TIMER"]
        gCommandTree["ARM"]["SEQ"]["OLIN"] = gCommandTree["ARM"]["SEQ"]["OLINE"]
        gCommandTree["ARM"]["SEQ"]["OUTP"] = gCommandTree["ARM"]["SEQ"]["OUTPUT"]
        gCommandTree["ARM"]["SEQ"]["SOUR"] = gCommandTree["ARM"]["SEQ"]["SOURCE"]
        gCommandTree["ARM"]["SEQ"]["TCON"] = gCommandTree["ARM"]["SEQ"]["TCONFIGURE"]
        gCommandTree["ARM"]["SEQ"]["TIM"] = gCommandTree["ARM"]["SEQ"]["TIMER"]
        gCommandTree["ARM"]["SOUR"] = gCommandTree["ARM"]["SOURCE"]
        gCommandTree["ARM"]["TIM"] = gCommandTree["ARM"]["TIMER"]
        gCommandTree["ARM"]["TCON"] = gCommandTree["ARM"]["TCONFIGURE"]
        gCommandTree["ARM"]["TCON"]["DIR"] = gCommandTree["ARM"]["TCON"]["DIRECTION"]
        gCommandTree["AVER"] = gCommandTree["AVERAGE"]
        gCommandTree["CALC"] = gCommandTree["CALCULATE1"]
        gCommandTree["CALC1"] = gCommandTree["CALCULATE1"]
        gCommandTree["CALCULATE"] = gCommandTree["CALCULATE1"]
        gCommandTree["CALC"]["DATA"]["LAT"] = gCommandTree["CALC"]["DATA"]["LATEST"]
        gCommandTree["CALC"]["MATH"]["CAT"] = gCommandTree["CALC"]["MATH"]["CATALOG"]
        gCommandTree["CALC"]["MATH"]["DEF"] = gCommandTree["CALC"]["MATH"]["DEFINE"]
        gCommandTree["CALC"]["MATH"]["DEL"] = gCommandTree["CALC"]["MATH"]["DELETE"]
        gCommandTree["CALC"]["MATH"]["UNIT"] = gCommandTree["CALC"]["MATH"]["UNITS"]
        gCommandTree["CALC"]["MATH"]["EXPR"] = gCommandTree["CALC"]["MATH"]["EXPRESSION"]
        gCommandTree["CALC"]["MATH"]["EXPR"]["CAT"] = gCommandTree["CALC"]["MATH"]["EXPR"]["CATALOG"]
        gCommandTree["CALC"]["MATH"]["EXPR"]["DEF"] = gCommandTree["CALC"]["MATH"]["EXPR"]["DEFINE"]
        gCommandTree["CALC"]["MATH"]["EXPR"]["DEL"] = gCommandTree["CALC"]["MATH"]["EXPR"]["DELETE"]
        gCommandTree["CALC"]["MATH"]["EXPR"]["DEL"]["SEL"] = gCommandTree["CALC"]["MATH"]["EXPR"]["DEL"]["SELECTED"]
        gCommandTree["CALC"]["STAT"] = gCommandTree["CALC"]["STATE"]
        gCommandTree["CALC2"] = gCommandTree["CALCULATE2"]
        gCommandTree["CALC2"]["CLIM"] = gCommandTree["CALC2"]["CLIMITS"]
        gCommandTree["CALC2"]["CLIM"]["BCON"] = gCommandTree["CALC2"]["CLIM"]["BCONTROL"]
        gCommandTree["CALC2"]["CLIM"]["CLE"] = gCommandTree["CALC2"]["CLIM"]["CLEAR"]
        gCommandTree["CALC2"]["CLIM"]["CLE"]["IMM"] = gCommandTree["CALC2"]["CLIM"]["CLEAR"]["IMMEDIATE"]
        gCommandTree["CALC2"]["CLIM"]["FAIL"]["SML"] = gCommandTree["CALC2"]["CLIM"]["FAIL"]["SMLOCATION"]
        --gCommandTree["CALC2"]["CLIM"]["FAIL"]["SOUR2"] = gCommandTree["CALC2"]["CLIM"]["FAIL"]["SOURCE2"]
        gCommandTree["CALC2"]["CLIM"]["PASS"]["SML"] = gCommandTree["CALC2"]["CLIM"]["PASS"]["SMLOCATION"]
        --gCommandTree["CALC2"]["CLIM"]["PASS"]["SOUR2"] = gCommandTree["CALC2"]["CLIM"]["PASS"]["SOURCE2"]
        gCommandTree["CALC2"]["DATA"]["LAT"] = gCommandTree["CALC2"]["DATA"]["LATEST"]
        gCommandTree["CALC2"]["LIM"] = gCommandTree["CALC2"]["LIMIT1"]
        gCommandTree["CALC2"]["LIM1"] = gCommandTree["CALC2"]["LIMIT1"]
        gCommandTree["CALC2"]["LIMIT"] = gCommandTree["CALC2"]["LIMIT1"]
        gCommandTree["CALC2"]["LIM"]["COMP"] = gCommandTree["CALC2"]["LIM"]["COMPLIANCE"]
        --gCommandTree["CALC2"]["LIM"]["COMP"]["SOUR2"] = gCommandTree["CALC2"]["LIM"]["COMP"]["SOURCE2"]
        gCommandTree["CALC2"]["LIM"]["STAT"] = gCommandTree["CALC2"]["LIM"]["STATE"]
        gCommandTree["CALC2"]["LIM2"] = gCommandTree["CALC2"]["LIMIT2"]
        gCommandTree["CALC2"]["LIM2"]["LOW"] = gCommandTree["CALC2"]["LIM2"]["LOWER"]
        --gCommandTree["CALC2"]["LIM2"]["LOW"]["SOUR2"] = gCommandTree["CALC2"]["LIM2"]["LOW"]["SOURCE2"]
        --gCommandTree["CALC2"]["LIM2"]["PASS"]["SOUR2"] = gCommandTree["CALC2"]["LIM2"]["PASS"]["SOURCE2"]
        gCommandTree["CALC2"]["LIM2"]["STAT"] = gCommandTree["CALC2"]["LIM2"]["STATE"]
        gCommandTree["CALC2"]["LIM2"]["UPP"] = gCommandTree["CALC2"]["LIM2"]["UPPER"]
        --gCommandTree["CALC2"]["LIM2"]["UPP"]["SOUR2"] = gCommandTree["CALC2"]["LIM2"]["UPP"]["SOURCE2"]
        gCommandTree["CALC2"]["LIM3"] = gCommandTree["CALC2"]["LIMIT3"]
        gCommandTree["CALC2"]["LIM3"]["LOW"] = gCommandTree["CALC2"]["LIM3"]["LOWER"]
        --gCommandTree["CALC2"]["LIM3"]["LOW"]["SOUR2"] = gCommandTree["CALC2"]["LIM3"]["LOW"]["SOURCE2"]
        --gCommandTree["CALC2"]["LIM3"]["PASS"]["SOUR2"] = gCommandTree["CALC2"]["LIM3"]["PASS"]["SOURCE2"]
        gCommandTree["CALC2"]["LIM3"]["STAT"] = gCommandTree["CALC2"]["LIM3"]["STATE"]
        gCommandTree["CALC2"]["LIM3"]["UPP"] = gCommandTree["CALC2"]["LIM3"]["UPPER"]
        --gCommandTree["CALC2"]["LIM3"]["UPP"]["SOUR2"] = gCommandTree["CALC2"]["LIM3"]["UPP"]["SOURCE2"]
        --gCommandTree["CALC2"]["LIM4"] = gCommandTree["CALC2"]["LIMIT4"]
        --gCommandTree["CALC2"]["LIM4"]["SOUR2"] = gCommandTree["CALC2"]["LIM4"]["SOURCE2"]
        --gCommandTree["CALC2"]["LIM4"]["STAT"] = gCommandTree["CALC2"]["LIM4"]["STATE"]
        gCommandTree["CALC2"]["LIM5"] = gCommandTree["CALC2"]["LIMIT5"]
        gCommandTree["CALC2"]["LIM5"]["LOW"] = gCommandTree["CALC2"]["LIM5"]["LOWER"]
        --gCommandTree["CALC2"]["LIM5"]["LOW"]["SOUR2"] = gCommandTree["CALC2"]["LIM5"]["LOW"]["SOURCE2"]
        --gCommandTree["CALC2"]["LIM5"]["PASS"]["SOUR2"] = gCommandTree["CALC2"]["LIM5"]["PASS"]["SOURCE2"]
        gCommandTree["CALC2"]["LIM5"]["STAT"] = gCommandTree["CALC2"]["LIM5"]["STATE"]
        gCommandTree["CALC2"]["LIM5"]["UPP"] = gCommandTree["CALC2"]["LIM5"]["UPPER"]
        --gCommandTree["CALC2"]["LIM5"]["UPP"]["SOUR2"] = gCommandTree["CALC2"]["LIM5"]["UPP"]["SOURCE2"]
        gCommandTree["CALC2"]["LIM6"] = gCommandTree["CALC2"]["LIMIT6"]
        gCommandTree["CALC2"]["LIM6"]["LOW"] = gCommandTree["CALC2"]["LIM6"]["LOWER"]
        --gCommandTree["CALC2"]["LIM6"]["LOW"]["SOUR2"] = gCommandTree["CALC2"]["LIM6"]["LOW"]["SOURCE2"]
        --gCommandTree["CALC2"]["LIM6"]["PASS"]["SOUR2"] = gCommandTree["CALC2"]["LIM6"]["PASS"]["SOURCE2"]
        gCommandTree["CALC2"]["LIM6"]["STAT"] = gCommandTree["CALC2"]["LIM6"]["STATE"]
        gCommandTree["CALC2"]["LIM6"]["UPP"] = gCommandTree["CALC2"]["LIM6"]["UPPER"]
        --gCommandTree["CALC2"]["LIM6"]["UPP"]["SOUR2"] = gCommandTree["CALC2"]["LIM6"]["UPP"]["SOURCE2"]
        gCommandTree["CALC2"]["LIM7"] = gCommandTree["CALC2"]["LIMIT7"]
        gCommandTree["CALC2"]["LIM7"]["LOW"] = gCommandTree["CALC2"]["LIM7"]["LOWER"]
        --gCommandTree["CALC2"]["LIM7"]["LOW"]["SOUR2"] = gCommandTree["CALC2"]["LIM7"]["LOW"]["SOURCE2"]
        --gCommandTree["CALC2"]["LIM7"]["PASS"]["SOUR2"] = gCommandTree["CALC2"]["LIM7"]["PASS"]["SOURCE2"]
        gCommandTree["CALC2"]["LIM7"]["STAT"] = gCommandTree["CALC2"]["LIM7"]["STATE"]
        gCommandTree["CALC2"]["LIM7"]["UPP"] = gCommandTree["CALC2"]["LIM7"]["UPPER"]
        --gCommandTree["CALC2"]["LIM7"]["UPP"]["SOUR2"] = gCommandTree["CALC2"]["LIM7"]["UPP"]["SOURCE2"]
        gCommandTree["CALC2"]["LIM8"] = gCommandTree["CALC2"]["LIMIT8"]
        gCommandTree["CALC2"]["LIM8"]["LOW"] = gCommandTree["CALC2"]["LIM8"]["LOWER"]
        --gCommandTree["CALC2"]["LIM8"]["LOW"]["SOUR2"] = gCommandTree["CALC2"]["LIM8"]["LOW"]["SOURCE2"]
        --gCommandTree["CALC2"]["LIM8"]["PASS"]["SOUR2"] = gCommandTree["CALC2"]["LIM8"]["PASS"]["SOURCE2"]
        gCommandTree["CALC2"]["LIM8"]["STAT"] = gCommandTree["CALC2"]["LIM8"]["STATE"]
        gCommandTree["CALC2"]["LIM8"]["UPP"] = gCommandTree["CALC2"]["LIM8"]["UPPER"]
        --gCommandTree["CALC2"]["LIM8"]["UPP"]["SOUR2"] = gCommandTree["CALC2"]["LIM8"]["UPP"]["SOURCE2"]
        gCommandTree["CALC2"]["LIM9"] = gCommandTree["CALC2"]["LIMIT9"]
        gCommandTree["CALC2"]["LIM9"]["LOW"] = gCommandTree["CALC2"]["LIM9"]["LOWER"]
        --gCommandTree["CALC2"]["LIM9"]["LOW"]["SOUR2"] = gCommandTree["CALC2"]["LIM9"]["LOW"]["SOURCE2"]
        --gCommandTree["CALC2"]["LIM9"]["PASS"]["SOUR2"] = gCommandTree["CALC2"]["LIM9"]["PASS"]["SOURCE2"]
        gCommandTree["CALC2"]["LIM9"]["STAT"] = gCommandTree["CALC2"]["LIM9"]["STATE"]
        gCommandTree["CALC2"]["LIM9"]["UPP"] = gCommandTree["CALC2"]["LIM9"]["UPPER"]
        --gCommandTree["CALC2"]["LIM9"]["UPP"]["SOUR2"] = gCommandTree["CALC2"]["LIM9"]["UPP"]["SOURCE2"]
        gCommandTree["CALC2"]["LIM10"] = gCommandTree["CALC2"]["LIMIT10"]
        gCommandTree["CALC2"]["LIM10"]["LOW"] = gCommandTree["CALC2"]["LIM10"]["LOWER"]
        --gCommandTree["CALC2"]["LIM10"]["LOW"]["SOUR2"] = gCommandTree["CALC2"]["LIM10"]["LOW"]["SOURCE2"]
        --gCommandTree["CALC2"]["LIM10"]["PASS"]["SOUR2"] = gCommandTree["CALC2"]["LIM10"]["PASS"]["SOURCE2"]
        gCommandTree["CALC2"]["LIM10"]["STAT"] = gCommandTree["CALC2"]["LIM10"]["STATE"]
        gCommandTree["CALC2"]["LIM10"]["UPP"] = gCommandTree["CALC2"]["LIM10"]["UPPER"]
        --gCommandTree["CALC2"]["LIM10"]["UPP"]["SOUR2"] = gCommandTree["CALC2"]["LIM10"]["UPP"]["SOURCE2"]
        gCommandTree["CALC2"]["LIM11"] = gCommandTree["CALC2"]["LIMIT11"]
        gCommandTree["CALC2"]["LIM11"]["LOW"] = gCommandTree["CALC2"]["LIM11"]["LOWER"]
        --gCommandTree["CALC2"]["LIM11"]["LOW"]["SOUR2"] = gCommandTree["CALC2"]["LIM11"]["LOW"]["SOURCE2"]
        --gCommandTree["CALC2"]["LIM11"]["PASS"]["SOUR2"] = gCommandTree["CALC2"]["LIM11"]["PASS"]["SOURCE2"]
        gCommandTree["CALC2"]["LIM11"]["STAT"] = gCommandTree["CALC2"]["LIM11"]["STATE"]
        gCommandTree["CALC2"]["LIM11"]["UPP"] = gCommandTree["CALC2"]["LIM11"]["UPPER"]
        --gCommandTree["CALC2"]["LIM11"]["UPP"]["SOUR2"] = gCommandTree["CALC2"]["LIM11"]["UPP"]["SOURCE2"]
        gCommandTree["CALC2"]["LIM12"] = gCommandTree["CALC2"]["LIMIT12"]
        gCommandTree["CALC2"]["LIM12"]["LOW"] = gCommandTree["CALC2"]["LIM12"]["LOWER"]
        --gCommandTree["CALC2"]["LIM12"]["LOW"]["SOUR2"] = gCommandTree["CALC2"]["LIM12"]["LOW"]["SOURCE2"]
        --gCommandTree["CALC2"]["LIM12"]["PASS"]["SOUR2"] = gCommandTree["CALC2"]["LIM12"]["PASS"]["SOURCE2"]
        gCommandTree["CALC2"]["LIM12"]["STAT"] = gCommandTree["CALC2"]["LIM12"]["STATE"]
        gCommandTree["CALC2"]["LIM12"]["UPP"] = gCommandTree["CALC2"]["LIM12"]["UPPER"]
        --gCommandTree["CALC2"]["LIM12"]["UPP"]["SOUR2"] = gCommandTree["CALC2"]["LIM12"]["UPP"]["SOURCE2"]
        gCommandTree["CALC2"]["NULL"]["ACQ"] = gCommandTree["CALC2"]["NULL"]["ACQUIRE"]
        gCommandTree["CALC2"]["NULL"]["OFFS"] = gCommandTree["CALC2"]["NULL"]["OFFSET"]
        gCommandTree["CALC2"]["NULL"]["STAT"] = gCommandTree["CALC2"]["NULL"]["STATE"]
        
        if gDigioSupport then
            gCommandTree["CALC2"]["CLIM"]["FAIL"]["SOUR2"] = gCommandTree["CALC2"]["CLIM"]["FAIL"]["SOURCE2"]
            gCommandTree["CALC2"]["CLIM"]["PASS"]["SOUR2"] = gCommandTree["CALC2"]["CLIM"]["PASS"]["SOURCE2"]
            gCommandTree["CALC2"]["LIM"]["COMP"]["SOUR2"] = gCommandTree["CALC2"]["LIM"]["COMP"]["SOURCE2"]
            gCommandTree["CALC2"]["LIM2"]["LOW"]["SOUR2"] = gCommandTree["CALC2"]["LIM2"]["LOW"]["SOURCE2"]
            gCommandTree["CALC2"]["LIM2"]["PASS"]["SOUR2"] = gCommandTree["CALC2"]["LIM2"]["PASS"]["SOURCE2"]
            gCommandTree["CALC2"]["LIM2"]["UPP"]["SOUR2"] = gCommandTree["CALC2"]["LIM2"]["UPP"]["SOURCE2"]
            gCommandTree["CALC2"]["LIM3"]["LOW"]["SOUR2"] = gCommandTree["CALC2"]["LIM3"]["LOW"]["SOURCE2"]
            gCommandTree["CALC2"]["LIM3"]["PASS"]["SOUR2"] = gCommandTree["CALC2"]["LIM3"]["PASS"]["SOURCE2"]
            gCommandTree["CALC2"]["LIM3"]["UPP"]["SOUR2"] = gCommandTree["CALC2"]["LIM3"]["UPP"]["SOURCE2"]
            gCommandTree["CALC2"]["LIM5"]["LOW"]["SOUR2"] = gCommandTree["CALC2"]["LIM5"]["LOW"]["SOURCE2"]
            gCommandTree["CALC2"]["LIM5"]["PASS"]["SOUR2"] = gCommandTree["CALC2"]["LIM5"]["PASS"]["SOURCE2"]
            gCommandTree["CALC2"]["LIM5"]["UPP"]["SOUR2"] = gCommandTree["CALC2"]["LIM5"]["UPP"]["SOURCE2"]
            gCommandTree["CALC2"]["LIM6"]["LOW"]["SOUR2"] = gCommandTree["CALC2"]["LIM6"]["LOW"]["SOURCE2"]
            gCommandTree["CALC2"]["LIM6"]["PASS"]["SOUR2"] = gCommandTree["CALC2"]["LIM6"]["PASS"]["SOURCE2"]
            gCommandTree["CALC2"]["LIM6"]["UPP"]["SOUR2"] = gCommandTree["CALC2"]["LIM6"]["UPP"]["SOURCE2"]
            gCommandTree["CALC2"]["LIM7"]["LOW"]["SOUR2"] = gCommandTree["CALC2"]["LIM7"]["LOW"]["SOURCE2"]
            gCommandTree["CALC2"]["LIM7"]["PASS"]["SOUR2"] = gCommandTree["CALC2"]["LIM7"]["PASS"]["SOURCE2"]
            gCommandTree["CALC2"]["LIM7"]["UPP"]["SOUR2"] = gCommandTree["CALC2"]["LIM7"]["UPP"]["SOURCE2"]
            gCommandTree["CALC2"]["LIM8"]["LOW"]["SOUR2"] = gCommandTree["CALC2"]["LIM8"]["LOW"]["SOURCE2"]
            gCommandTree["CALC2"]["LIM8"]["PASS"]["SOUR2"] = gCommandTree["CALC2"]["LIM8"]["PASS"]["SOURCE2"]
            gCommandTree["CALC2"]["LIM8"]["UPP"]["SOUR2"] = gCommandTree["CALC2"]["LIM8"]["UPP"]["SOURCE2"]
            gCommandTree["CALC2"]["LIM9"]["LOW"]["SOUR2"] = gCommandTree["CALC2"]["LIM9"]["LOW"]["SOURCE2"]
            gCommandTree["CALC2"]["LIM9"]["PASS"]["SOUR2"] = gCommandTree["CALC2"]["LIM9"]["PASS"]["SOURCE2"]
            gCommandTree["CALC2"]["LIM9"]["UPP"]["SOUR2"] = gCommandTree["CALC2"]["LIM9"]["UPP"]["SOURCE2"]
            gCommandTree["CALC2"]["LIM10"]["LOW"]["SOUR2"] = gCommandTree["CALC2"]["LIM10"]["LOW"]["SOURCE2"]
            gCommandTree["CALC2"]["LIM10"]["PASS"]["SOUR2"] = gCommandTree["CALC2"]["LIM10"]["PASS"]["SOURCE2"]
            gCommandTree["CALC2"]["LIM10"]["UPP"]["SOUR2"] = gCommandTree["CALC2"]["LIM10"]["UPP"]["SOURCE2"]
            gCommandTree["CALC2"]["LIM11"]["LOW"]["SOUR2"] = gCommandTree["CALC2"]["LIM11"]["LOW"]["SOURCE2"]
            gCommandTree["CALC2"]["LIM11"]["PASS"]["SOUR2"] = gCommandTree["CALC2"]["LIM11"]["PASS"]["SOURCE2"]
            gCommandTree["CALC2"]["LIM11"]["UPP"]["SOUR2"] = gCommandTree["CALC2"]["LIM11"]["UPP"]["SOURCE2"]
            gCommandTree["CALC2"]["LIM12"]["LOW"]["SOUR2"] = gCommandTree["CALC2"]["LIM12"]["LOW"]["SOURCE2"]
            gCommandTree["CALC2"]["LIM12"]["PASS"]["SOUR2"] = gCommandTree["CALC2"]["LIM12"]["PASS"]["SOURCE2"]
            gCommandTree["CALC2"]["LIM12"]["UPP"]["SOUR2"] = gCommandTree["CALC2"]["LIM12"]["UPP"]["SOURCE2"]
        end
        
        gCommandTree["CALC3"] = gCommandTree["CALCULATE3"]
        gCommandTree["CALC3"]["FORM"] = gCommandTree["CALC3"]["FORMAT"]
        gCommandTree["CONF"] = gCommandTree["CONFIGURE"]
        gCommandTree["CONF"]["CURR"] = gCommandTree["CONF"]["CURRENT"]
        gCommandTree["CONF"]["VOLT"] = gCommandTree["CONF"]["VOLTAGE"]
        gCommandTree["CONF"]["RES"] = gCommandTree["CONF"]["RESISTANCE"]
        gCommandTree["CURR"] = gCommandTree["CURRENT"]
        gCommandTree["DATA"]["CLE"] = gCommandTree["DATA"]["CLEAR"]
        gCommandTree["DATA"]["LAT"] = gCommandTree["DATA"]["LATEST"]
        gCommandTree["DATA"]["POIN"] = gCommandTree["DATA"]["POINTS"]
        gCommandTree["DATA"]["TST"] = gCommandTree["DATA"]["TSTAMP"]
        gCommandTree["DIAG"] = gCommandTree["DIAGNOSTIC"]
        gCommandTree["DIAG"]["DISP"] = gCommandTree["DIAGNOSTIC"]["DISPLAY"]
        gCommandTree["DIAG"]["DISP"]["ERR"] = gCommandTree["DIAGNOSTIC"]["DISP"]["ERRORS"]
        gCommandTree["DISP"] = gCommandTree["DISPLAY"]
        gCommandTree["DISP"]["ATTR"] = gCommandTree["DISP"]["ATTRIBUTES"]
        gCommandTree["DISP"]["CND"] = gCommandTree["DISP"]["CNDISPLAY"]
        gCommandTree["DISP"]["DIG"] = gCommandTree["DISP"]["DIGITS"]
        gCommandTree["DISP"]["ENAB"] = gCommandTree["DISP"]["ENABLE"]
        gCommandTree["DISP"]["WIND"] = gCommandTree["DISP"]["WINDOW1"]
        gCommandTree["DISP"]["WIND1"] = gCommandTree["DISP"]["WINDOW1"]
        gCommandTree["DISP"]["WINDOW"] = gCommandTree["DISP"]["WINDOW1"]
        gCommandTree["DISP"]["WIND"]["ATTR"] = gCommandTree["DISP"]["WIND"]["ATTRIBUTES"]
        gCommandTree["DISP"]["WIND"]["TEXT"]["STAT"] = gCommandTree["DISP"]["WIND"]["TEXT"]["STATE"]
        gCommandTree["DISP"]["WIND2"] = gCommandTree["DISP"]["WINDOW2"]
        gCommandTree["DISP"]["WIND2"]["ATTR"] = gCommandTree["DISP"]["WIND2"]["ATTRIBUTES"]
        gCommandTree["DISP"]["WIND2"]["TEXT"]["STAT"] = gCommandTree["DISP"]["WIND2"]["TEXT"]["STATE"]
        gCommandTree["FETC"] = gCommandTree["FETCH"]
        gCommandTree["FORM"] = gCommandTree["FORMAT"]
        gCommandTree["FORM"]["BORD"] = gCommandTree["FORM"]["BORDER"]
        gCommandTree["FORM"]["ELEM"] = gCommandTree["FORM"]["ELEMENTS"]
        gCommandTree["FORM"]["ELEM"]["CALC"] = gCommandTree["FORM"]["ELEM"]["CALCULATE"]
        gCommandTree["FORM"]["ELEM"]["SENS"] = gCommandTree["FORM"]["ELEM"]["SENSE1"]
        gCommandTree["FORM"]["ELEM"]["SENS1"] = gCommandTree["FORM"]["ELEM"]["SENSE1"]
        gCommandTree["FORM"]["ELEM"]["SENSE"] = gCommandTree["FORM"]["ELEM"]["SENSE1"]
        gCommandTree["FORM"]["SOUR2"] = gCommandTree["FORM"]["SOURCE2"]
        gCommandTree["FORM"]["SREG"] = gCommandTree["FORM"]["SREGISTER"]
        gCommandTree["FUNC"] = gCommandTree["FUNCTION"]
        gCommandTree["INIT"] = gCommandTree["INITIATE"]
        gCommandTree["INIT"]["IMM"] = gCommandTree["INIT"]["IMMEDIATE"]
        gCommandTree["MEAS"] = gCommandTree["MEASURE"]
        gCommandTree["MEAS"]["CURR"] = gCommandTree["MEAS"]["CURRENT"]
        gCommandTree["MEAS"]["VOLT"] = gCommandTree["MEAS"]["VOLTAGE"]
        gCommandTree["MEAS"]["RES"] = gCommandTree["MEAS"]["RESISTANCE"]
        gCommandTree["OUTP"] = gCommandTree["OUTPUT1"]
        gCommandTree["OUTP1"] = gCommandTree["OUTPUT1"]
        gCommandTree["OUTPUT"] = gCommandTree["OUTPUT1"]
        gCommandTree["OUTP"]["ENAB"] = gCommandTree["OUTP"]["ENABLE"]
        gCommandTree["OUTP"]["ENAB"]["STAT"] = gCommandTree["OUTP"]["ENAB"]["STATE"]
        gCommandTree["OUTP"]["ENAB"]["TRIP"] = gCommandTree["OUTP"]["ENAB"]["TRIPPED"]
        gCommandTree["OUTP"]["SMOD"] = gCommandTree["OUTP"]["SMODE"]
        gCommandTree["OUTP"]["STAT"] = gCommandTree["OUTP"]["STATE"]
        gCommandTree["OUTP"]["INT"] = gCommandTree["OUTP"]["INTERLOCK"]
        gCommandTree["OUTP"]["INT"]["STAT"] = gCommandTree["OUTP"]["INT"]["STATE"]
        gCommandTree["RES"] = gCommandTree["RESISTANCE"]
        gCommandTree["ROUT"] = gCommandTree["ROUTE"]
        gCommandTree["ROUT"]["TERM"] = gCommandTree["ROUT"]["TERMINALS"]
        gCommandTree["SENS"] = gCommandTree["SENSE1"]
        gCommandTree["SENS1"] = gCommandTree["SENSE1"]
        gCommandTree["SENSE"] = gCommandTree["SENSE1"]
        gCommandTree["SENS"]["AVER"] = gCommandTree["SENS"]["AVERAGE"]
        gCommandTree["SENS"]["AVER"]["COUN"] = gCommandTree["SENS"]["AVER"]["COUNT"]
        gCommandTree["SENS"]["AVER"]["TCON"] = gCommandTree["SENS"]["AVER"]["TCONTROL"]
        gCommandTree["SENS"]["AVER"]["STAT"] = gCommandTree["SENS"]["AVER"]["STATE"]
        gCommandTree["SENS"]["CURR"] = gCommandTree["SENS"]["CURRENT"]
        gCommandTree["SENS"]["CURR"]["DC"]["NPLC"] = gCommandTree["SENS"]["CURR"]["DC"]["NPLCYCLES"]
        gCommandTree["SENS"]["CURR"]["DC"]["PROT"] = gCommandTree["SENS"]["CURR"]["DC"]["PROTECTION"]
        gCommandTree["SENS"]["CURR"]["DC"]["PROT"]["LEV"] = gCommandTree["SENS"]["CURR"]["DC"]["PROT"]["LEVEL"]
        gCommandTree["SENS"]["CURR"]["DC"]["PROT"]["RSYN"] = gCommandTree["SENS"]["CURR"]["DC"]["PROT"]["RSYNCHRONIZE"]
        gCommandTree["SENS"]["CURR"]["DC"]["PROT"]["TRIP"] = gCommandTree["SENS"]["CURR"]["DC"]["PROT"]["TRIPPED"]
        gCommandTree["SENS"]["CURR"]["DC"]["RANG"] = gCommandTree["SENS"]["CURR"]["DC"]["RANGE"]
        gCommandTree["SENS"]["CURR"]["DC"]["RANG"]["AUTO"]["LLIM"] = gCommandTree["SENS"]["CURR"]["DC"]["RANG"]["AUTO"]["LLIMIT"]
        gCommandTree["SENS"]["CURR"]["DC"]["RANG"]["AUTO"]["ULIM"] = gCommandTree["SENS"]["CURR"]["DC"]["RANG"]["AUTO"]["ULIMIT"]
        gCommandTree["SENS"]["CURR"]["DC"]["RANG"]["UPP"] = gCommandTree["SENS"]["CURR"]["DC"]["RANG"]["UPPER"]
        gCommandTree["SENS"]["CURR"]["NPLC"] = gCommandTree["SENS"]["CURR"]["NPLCYCLES"]
        gCommandTree["SENS"]["CURR"]["PROT"] = gCommandTree["SENS"]["CURR"]["PROTECTION"]
        gCommandTree["SENS"]["CURR"]["RANG"] = gCommandTree["SENS"]["CURR"]["RANGE"]
        gCommandTree["SENS"]["DATA"]["LAT"] = gCommandTree["SENS"]["DATA"]["LATEST"]
        gCommandTree["SENS"]["FUNC"] = gCommandTree["SENS"]["FUNCTION"]
        gCommandTree["SENS"]["FUNC"]["CONC"] = gCommandTree["SENS"]["FUNC"]["CONCURRENT"]
        gCommandTree["SENS"]["FUNC"]["COUN"] = gCommandTree["SENS"]["FUNC"]["COUNT"]
        gCommandTree["SENS"]["FUNC"]["OFF"]["COUN"] = gCommandTree["SENS"]["FUNC"]["OFF"]["COUNT"]
        gCommandTree["SENS"]["FUNC"]["ON"]["COUN"] = gCommandTree["SENS"]["FUNC"]["ON"]["COUNT"]
        gCommandTree["SENS"]["FUNC"]["STAT"] = gCommandTree["SENS"]["FUNC"]["STATE"]
        gCommandTree["SENS"]["RES"] = gCommandTree["SENS"]["RESISTANCE"]
        gCommandTree["SENS"]["RES"]["NPLC"] = gCommandTree["SENS"]["RES"]["NPLCYCLES"]
        gCommandTree["SENS"]["RES"]["OCOM"] = gCommandTree["SENS"]["RES"]["OCOMPENSATED"]
        gCommandTree["SENS"]["RES"]["RANG"] = gCommandTree["SENS"]["RES"]["RANGE"]
        gCommandTree["SENS"]["RES"]["RANG"]["UPP"] = gCommandTree["SENS"]["RES"]["RANG"]["UPPER"]
        gCommandTree["SENS"]["VOLT"] = gCommandTree["SENS"]["VOLTAGE"]
        gCommandTree["SENS"]["VOLT"]["DC"]["NPLC"] = gCommandTree["SENS"]["VOLT"]["DC"]["NPLCYCLES"]
        gCommandTree["SENS"]["VOLT"]["DC"]["PROT"] = gCommandTree["SENS"]["VOLT"]["DC"]["PROTECTION"]
        gCommandTree["SENS"]["VOLT"]["DC"]["PROT"]["LEV"] = gCommandTree["SENS"]["VOLT"]["DC"]["PROT"]["LEVEL"]
        gCommandTree["SENS"]["VOLT"]["DC"]["PROT"]["RSYN"] = gCommandTree["SENS"]["VOLT"]["DC"]["PROT"]["RSYNCHRONIZE"]
        gCommandTree["SENS"]["VOLT"]["DC"]["PROT"]["TRIP"] = gCommandTree["SENS"]["VOLT"]["DC"]["PROT"]["TRIPPED"]
        gCommandTree["SENS"]["VOLT"]["DC"]["RANG"] = gCommandTree["SENS"]["VOLT"]["DC"]["RANGE"]
        gCommandTree["SENS"]["VOLT"]["DC"]["RANG"]["AUTO"]["LLIM"] = gCommandTree["SENS"]["VOLT"]["DC"]["RANG"]["AUTO"]["LLIMIT"]
        gCommandTree["SENS"]["VOLT"]["DC"]["RANG"]["AUTO"]["ULIM"] = gCommandTree["SENS"]["VOLT"]["DC"]["RANG"]["AUTO"]["ULIMIT"]
        gCommandTree["SENS"]["VOLT"]["DC"]["RANG"]["UPP"] = gCommandTree["SENS"]["VOLT"]["DC"]["RANG"]["UPPER"]
        gCommandTree["SENS"]["VOLT"]["NPLC"] = gCommandTree["SENS"]["VOLT"]["NPLCYCLES"]
        gCommandTree["SENS"]["VOLT"]["PROT"] = gCommandTree["SENS"]["VOLT"]["PROTECTION"]
        gCommandTree["SENS"]["VOLT"]["RANG"] = gCommandTree["SENS"]["VOLT"]["RANGE"]
        gCommandTree["SOUR"] = gCommandTree["SOURCE1"]
        gCommandTree["SOUR1"] = gCommandTree["SOURCE1"]
        gCommandTree["SOURCE"] = gCommandTree["SOURCE1"]
        gCommandTree["SOUR"]["CLE"] = gCommandTree["SOUR"]["CLEAR"]
        gCommandTree["SOUR"]["CLE"]["IMM"] = gCommandTree["SOUR"]["CLE"]["IMMEDIATE"]
        gCommandTree["SOUR"]["CURR"] = gCommandTree["SOUR"]["CURRENT"]
        gCommandTree["SOUR"]["CURR"]["AMPL"] = gCommandTree["SOUR"]["CURR"]["AMPLITUDE"]
        gCommandTree["SOUR"]["CURR"]["CENT"] = gCommandTree["SOUR"]["CURR"]["CENTER"]
        gCommandTree["SOUR"]["CURR"]["IMM"] = gCommandTree["SOUR"]["CURR"]["IMMEDIATE"]
        gCommandTree["SOUR"]["CURR"]["LEV"] = gCommandTree["SOUR"]["CURR"]["LEVEL"]
        gCommandTree["SOUR"]["CURR"]["LEV"]["AMPL"] = gCommandTree["SOUR"]["CURR"]["LEV"]["AMPLITUDE"]
        gCommandTree["SOUR"]["CURR"]["LEV"]["IMM"] = gCommandTree["SOUR"]["CURR"]["LEV"]["IMMEDIATE"]
        gCommandTree["SOUR"]["CURR"]["LEV"]["IMM"]["AMPL"] = gCommandTree["SOUR"]["CURR"]["LEV"]["IMM"]["AMPLITUDE"]
        gCommandTree["SOUR"]["CURR"]["LEV"]["TRIG"] = gCommandTree["SOUR"]["CURR"]["LEV"]["TRIGGERED"]
        gCommandTree["SOUR"]["CURR"]["LEV"]["TRIG"]["AMPL"] = gCommandTree["SOUR"]["CURR"]["LEV"]["TRIG"]["AMPLITUDE"]
        gCommandTree["SOUR"]["CURR"]["LEV"]["TRIG"]["SFAC"] = gCommandTree["SOUR"]["CURR"]["LEV"]["TRIG"]["SFACTOR"]
        gCommandTree["SOUR"]["CURR"]["LEV"]["TRIG"]["SFAC"]["STAT"] = gCommandTree["SOUR"]["CURR"]["LEV"]["TRIG"]["SFAC"]["STATE"]
        gCommandTree["SOUR"]["CURR"]["RANG"] = gCommandTree["SOUR"]["CURR"]["RANGE"]
        gCommandTree["SOUR"]["CURR"]["STAR"] = gCommandTree["SOUR"]["CURR"]["START"]
        gCommandTree["SOUR"]["CURR"]["TRIG"] = gCommandTree["SOUR"]["CURR"]["TRIGGERED"]
        gCommandTree["SOUR"]["DEL"] = gCommandTree["SOUR"]["DELAY"]
        gCommandTree["SOUR"]["FUNC"] = gCommandTree["SOUR"]["FUNCTION"]
        gCommandTree["SOUR"]["FUNC"]["SHAP"] = gCommandTree["SOUR"]["FUNC"]["SHAPE"]
        gCommandTree["SOUR"]["LIST"]["CURR"] = gCommandTree["SOUR"]["LIST"]["CURRENT"]
        gCommandTree["SOUR"]["LIST"]["CURR"]["APP"] = gCommandTree["SOUR"]["LIST"]["CURR"]["APPEND"]
        gCommandTree["SOUR"]["LIST"]["CURR"]["POIN"] = gCommandTree["SOUR"]["LIST"]["CURR"]["POINTS"]
        gCommandTree["SOUR"]["LIST"]["CURR"]["STAR"] = gCommandTree["SOUR"]["LIST"]["CURR"]["START"]
        gCommandTree["SOUR"]["LIST"]["VOLT"] = gCommandTree["SOUR"]["LIST"]["VOLTAGE"]
        gCommandTree["SOUR"]["LIST"]["VOLT"]["APP"] = gCommandTree["SOUR"]["LIST"]["VOLT"]["APPEND"]
        gCommandTree["SOUR"]["LIST"]["VOLT"]["POIN"] = gCommandTree["SOUR"]["LIST"]["VOLT"]["POINTS"]
        gCommandTree["SOUR"]["LIST"]["VOLT"]["STAR"] = gCommandTree["SOUR"]["LIST"]["VOLT"]["START"]
        gCommandTree["SOUR"]["MEM"] = gCommandTree["SOUR"]["MEMORY"]
        gCommandTree["SOUR"]["MEM"]["POIN"] = gCommandTree["SOUR"]["MEM"]["POINTS"]
        gCommandTree["SOUR"]["MEM"]["REC"] = gCommandTree["SOUR"]["MEM"]["RECALL"]
        gCommandTree["SOUR"]["MEM"]["STAR"] = gCommandTree["SOUR"]["MEM"]["START"]
        gCommandTree["SOUR"]["PULS"] = gCommandTree["SOUR"]["PULSE"]
        gCommandTree["SOUR"]["PULS"]["WIDT"] = gCommandTree["SOUR"]["PULS"]["WIDTH"]
        gCommandTree["SOUR"]["PULS"]["DEL"] = gCommandTree["SOUR"]["PULS"]["DELAY"]
        gCommandTree["SOUR"]["SWE"] = gCommandTree["SOUR"]["SWEEP"]
        gCommandTree["SOUR"]["SWE"]["CAB"] = gCommandTree["SOUR"]["SWE"]["CABORT"]
        gCommandTree["SOUR"]["SWE"]["DIR"] = gCommandTree["SOUR"]["SWE"]["DIRECTION"]
        gCommandTree["SOUR"]["SWE"]["POIN"] = gCommandTree["SOUR"]["SWE"]["POINTS"]
        gCommandTree["SOUR"]["SWE"]["RANG"] = gCommandTree["SOUR"]["SWE"]["RANGING"]
        gCommandTree["SOUR"]["SWE"]["SPAC"] = gCommandTree["SOUR"]["SWE"]["SPACING"]
        gCommandTree["SOUR"]["VOLT"] = gCommandTree["SOUR"]["VOLTAGE"]
        gCommandTree["SOUR"]["VOLT"]["AMPL"] = gCommandTree["SOUR"]["VOLT"]["AMPLITUDE"]
        gCommandTree["SOUR"]["VOLT"]["CENT"] = gCommandTree["SOUR"]["VOLT"]["CENTER"]
        gCommandTree["SOUR"]["VOLT"]["IMM"] = gCommandTree["SOUR"]["VOLT"]["IMMEDIATE"]
        gCommandTree["SOUR"]["VOLT"]["LEV"] = gCommandTree["SOUR"]["VOLT"]["LEVEL"]
        gCommandTree["SOUR"]["VOLT"]["LEV"]["AMPL"] = gCommandTree["SOUR"]["VOLT"]["LEV"]["AMPLITUDE"]
        gCommandTree["SOUR"]["VOLT"]["LEV"]["IMM"] = gCommandTree["SOUR"]["VOLT"]["LEV"]["IMMEDIATE"]
        gCommandTree["SOUR"]["VOLT"]["LEV"]["IMM"]["AMPL"] = gCommandTree["SOUR"]["VOLT"]["LEV"]["IMM"]["AMPLITUDE"]
        gCommandTree["SOUR"]["VOLT"]["LEV"]["TRIG"] = gCommandTree["SOUR"]["VOLT"]["LEV"]["TRIGGERED"]
        gCommandTree["SOUR"]["VOLT"]["LEV"]["TRIG"]["AMPL"] = gCommandTree["SOUR"]["VOLT"]["LEV"]["TRIG"]["AMPLITUDE"]
        gCommandTree["SOUR"]["VOLT"]["LEV"]["TRIG"]["SFAC"] = gCommandTree["SOUR"]["VOLT"]["LEV"]["TRIG"]["SFACTOR"]
        gCommandTree["SOUR"]["VOLT"]["LEV"]["TRIG"]["SFAC"]["STAT"] = gCommandTree["SOUR"]["VOLT"]["LEV"]["TRIG"]["SFAC"]["STATE"]
        gCommandTree["SOUR"]["VOLT"]["RANG"] = gCommandTree["SOUR"]["VOLT"]["RANGE"]
        gCommandTree["SOUR"]["VOLT"]["STAR"] = gCommandTree["SOUR"]["VOLT"]["START"]
        gCommandTree["SOUR"]["VOLT"]["TRIG"] = gCommandTree["SOUR"]["VOLT"]["TRIGGERED"]
        if gDigioSupport then
            gCommandTree["SOUR2"] = gCommandTree["SOURCE2"]
            gCommandTree["SOUR2"]["BSIZ"] = gCommandTree["SOUR2"]["BSIZE"]
            gCommandTree["SOUR2"]["CLE"] = gCommandTree["SOUR2"]["CLEAR"]
            gCommandTree["SOUR2"]["CLE"]["AUTO"]["DEL"] = gCommandTree["SOUR2"]["CLE"]["AUTO"]["DELAY"]
            gCommandTree["SOUR2"]["CLE"]["IMM"] = gCommandTree["SOUR2"]["CLE"]["IMMEDIATE"]
            gCommandTree["SOUR2"]["TTL"]["ACT"] = gCommandTree["SOUR2"]["TTL"]["ACTUAL"]
            gCommandTree["SOUR2"]["TTL"]["DEF"] = gCommandTree["SOUR2"]["TTL"]["DEFAULT"]
            gCommandTree["SOUR2"]["TTL"]["LEV"] = gCommandTree["SOUR2"]["TTL"]["LEVEL"]
            gCommandTree["SOUR2"]["TTL"]["LEV"]["ACT"] = gCommandTree["SOUR2"]["TTL"]["LEV"]["ACTUAL"]
            gCommandTree["SOUR2"]["TTL4"]["BST"] = gCommandTree["SOUR2"]["TTL4"]["BSTATE"]
        end
        gCommandTree["STAT"] = gCommandTree["STATUS"]
        gCommandTree["STAT"]["MEAS"] = gCommandTree["STAT"]["MEASUREMENT"]
        gCommandTree["STAT"]["MEAS"]["COND"] = gCommandTree["STAT"]["MEAS"]["CONDITION"]
        gCommandTree["STAT"]["MEAS"]["ENAB"] = gCommandTree["STAT"]["MEAS"]["ENABLE"]
        gCommandTree["STAT"]["MEAS"]["EVEN"] = gCommandTree["STAT"]["MEAS"]["EVENT"]
        gCommandTree["STAT"]["OPER"] = gCommandTree["STAT"]["OPERATION"]
        gCommandTree["STAT"]["OPER"]["COND"] = gCommandTree["STAT"]["OPER"]["CONDITION"]
        gCommandTree["STAT"]["OPER"]["ENAB"] = gCommandTree["STAT"]["OPER"]["ENABLE"]
        gCommandTree["STAT"]["OPER"]["EVEN"] = gCommandTree["STAT"]["OPER"]["EVENT"]
        gCommandTree["STAT"]["QUES"] = gCommandTree["STAT"]["QUESTIONABLE"]
        gCommandTree["STAT"]["QUES"]["COND"] = gCommandTree["STAT"]["QUES"]["CONDITION"]
        gCommandTree["STAT"]["QUES"]["ENAB"] = gCommandTree["STAT"]["QUES"]["ENABLE"]
        gCommandTree["STAT"]["QUES"]["EVEN"] = gCommandTree["STAT"]["QUES"]["EVENT"]
        gCommandTree["STAT"]["PRES"] = gCommandTree["STAT"]["PRESET"]
        gCommandTree["STAT"]["QUE"] = gCommandTree["STAT"]["QUEUE"]
        gCommandTree["STAT"]["QUE"]["CLE"] = gCommandTree["STAT"]["QUE"]["CLEAR"]
        gCommandTree["STAT"]["QUE"]["DIS"] = gCommandTree["STAT"]["QUE"]["DISABLE"]
        gCommandTree["STAT"]["QUE"]["ENAB"] = gCommandTree["STAT"]["QUE"]["ENABLE"]
        gCommandTree["SYST"] = gCommandTree["SYSTEM"]
        gCommandTree["SYST"]["AZER"] = gCommandTree["SYST"]["AZERO"]
        gCommandTree["SYST"]["AZER"]["CACH"] = gCommandTree["SYST"]["AZER"]["CACHING"]
        gCommandTree["SYST"]["AZER"]["CACH"]["STAT"] = gCommandTree["SYST"]["AZER"]["CACH"]["STATE"]
        gCommandTree["SYST"]["AZER"]["CACH"]["REFR"] = gCommandTree["SYST"]["AZER"]["CACH"]["REFRESH"]
        gCommandTree["SYST"]["AZER"]["CACH"]["RES"] = gCommandTree["SYST"]["AZER"]["CACH"]["RESET"]
        gCommandTree["SYST"]["AZER"]["CACH"]["NPLC"] = gCommandTree["SYST"]["AZER"]["CACH"]["NPLCYCLES"]
        gCommandTree["SYST"]["AZER"]["STAT"] = gCommandTree["SYST"]["AZER"]["STATE"]
        gCommandTree["SYST"]["BEEP"] = gCommandTree["SYST"]["BEEPER"]
        gCommandTree["SYST"]["BEEP"]["IMM"] = gCommandTree["SYST"]["BEEP"]["IMMEDIATE"]
        gCommandTree["SYST"]["BEEP"]["STAT"] = gCommandTree["SYST"]["BEEP"]["STATE"]
        --gCommandTree["SYST"]["CCH"] = gCommandTree["SYST"]["CCHECK"]
        gCommandTree["SYST"]["CLE"] = gCommandTree["SYST"]["CLEAR"]
        gCommandTree["SYST"]["ERR"] = gCommandTree["SYST"]["ERROR"]
        gCommandTree["SYST"]["ERR"]["COUN"] = gCommandTree["SYST"]["ERR"]["COUNT"]
        --gCommandTree["SYST"]["GUAR"] = gCommandTree["SYST"]["GUARD"]
        gCommandTree["SYST"]["LFR"] = gCommandTree["SYST"]["LFREQUENCY"]
        gCommandTree["SYST"]["LOC"] = gCommandTree["SYST"]["LOCAL"]
        gCommandTree["SYST"]["MEM"] = gCommandTree["SYST"]["MEMORY"]
        gCommandTree["SYST"]["MEM"]["INIT"] = gCommandTree["SYST"]["MEM"]["INITIALIZE"]
        gCommandTree["SYST"]["MEP"]["STAT"] = gCommandTree["SYST"]["MEP"]["STATE"]
        gCommandTree["SYST"]["MEP"]["HOLD"] = gCommandTree["SYST"]["MEP"]["HOLDOFF"]
        gCommandTree["SYST"]["POS"] = gCommandTree["SYST"]["POSETUP"]
        gCommandTree["SYST"]["PRES"] = gCommandTree["SYST"]["PRESET"]
        gCommandTree["SYST"]["RCM"] = gCommandTree["SYST"]["RCMODE"]
        gCommandTree["SYST"]["RSEN"] = gCommandTree["SYST"]["RSENSE"]
        gCommandTree["SYST"]["RWL"] = gCommandTree["SYST"]["RWLOCK"]
        gCommandTree["SYST"]["REM"] = gCommandTree["SYST"]["REMOTE"]
        gCommandTree["SYST"]["TIME"]["RES"] = gCommandTree["SYST"]["TIME"]["RESET"]
        gCommandTree["SYST"]["VERS"] = gCommandTree["SYST"]["VERSION"]
        gCommandTree["TRAC"] = gCommandTree["TRACE"]
        gCommandTree["TRAC"]["CLE"] = gCommandTree["TRAC"]["CLEAR"]
        gCommandTree["TRAC"]["POIN"] = gCommandTree["TRAC"]["POINTS"]
        gCommandTree["TRAC"]["POIN"]["ACT"] = gCommandTree["TRAC"]["POIN"]["ACTUAL"]
        gCommandTree["TRAC"]["FEED"]["CONT"] = gCommandTree["TRAC"]["FEED"]["CONTROL"]
        gCommandTree["TRAC"]["TST"] = gCommandTree["TRAC"]["TSTAMP"]
        gCommandTree["TRAC"]["TST"]["FORM"] = gCommandTree["TRAC"]["TST"]["FORMAT"]
        gCommandTree["TRIG"] = gCommandTree["TRIGGER"]
        gCommandTree["TRIG"]["CLE"] = gCommandTree["TRIG"]["CLEAR"]
        gCommandTree["TRIG"]["COUN"] = gCommandTree["TRIG"]["COUNT"]
        gCommandTree["TRIG"]["DEL"] = gCommandTree["TRIG"]["DELAY"]
        gCommandTree["TRIG"]["DIR"] = gCommandTree["TRIG"]["DIRECTION"]
        gCommandTree["TRIG"]["INP"] = gCommandTree["TRIG"]["INPUT"]
        gCommandTree["TRIG"]["SEQ"] = gCommandTree["TRIG"]["SEQUENCE1"]
        gCommandTree["TRIG"]["SEQ1"] = gCommandTree["TRIG"]["SEQUENCE1"]
        gCommandTree["TRIG"]["SEQUENCE"] = gCommandTree["TRIG"]["SEQUENCE1"]
        gCommandTree["TRIG"]["SEQ"]["ASYN"] = gCommandTree["TRIG"]["SEQ"]["ASYNCHRONOUS"]
        gCommandTree["TRIG"]["SEQ"]["COUN"] = gCommandTree["TRIG"]["SEQ"]["COUNT"]
        gCommandTree["TRIG"]["SEQ"]["DEL"] = gCommandTree["TRIG"]["SEQ"]["DELAY"]
        gCommandTree["TRIG"]["SEQ"]["DIR"] = gCommandTree["TRIG"]["SEQ"]["DIRECTION"]
        gCommandTree["TRIG"]["SEQ"]["INP"] = gCommandTree["TRIG"]["SEQ"]["INPUT"]
        gCommandTree["TRIG"]["SEQ"]["SOUR"] = gCommandTree["TRIG"]["SEQ"]["SOURCE"]
        gCommandTree["TRIG"]["SEQ"]["TCON"] = gCommandTree["TRIG"]["SEQ"]["TCONFIGURE"]
        gCommandTree["TRIG"]["SEQ"]["TCON"]["ASYN"] = gCommandTree["TRIG"]["SEQ"]["TCON"]["ASYNCHRONOUS"]
        gCommandTree["TRIG"]["SEQ"]["TCON"]["ASYN"]["INP"] = gCommandTree["TRIG"]["SEQ"]["TCON"]["ASYN"]["INPUT"]
        gCommandTree["TRIG"]["SEQ"]["TCON"]["DIR"] = gCommandTree["TRIG"]["SEQ"]["TCON"]["DIRECTION"]
        gCommandTree["TRIG"]["SEQ"]["TCON"]["INP"] = gCommandTree["TRIG"]["SEQ"]["TCON"]["INPUT"]
        gCommandTree["TRIG"]["SOUR"] = gCommandTree["TRIG"]["SOURCE"]
        gCommandTree["TRIG"]["TCON"] = gCommandTree["TRIG"]["TCONFIGURE"]
        
        if gDigioSupport then
            gCommandTree["TRIG"]["ILIN"] = gCommandTree["TRIG"]["ILINE"]
            gCommandTree["TRIG"]["OLIN"] = gCommandTree["TRIG"]["OLINE"]
            gCommandTree["TRIG"]["OUTP"] = gCommandTree["TRIG"]["OUTPUT"]
            gCommandTree["TRIG"]["SEQ"]["ILIN"] = gCommandTree["TRIG"]["SEQ"]["ILINE"]
            gCommandTree["TRIG"]["SEQ"]["OLIN"] = gCommandTree["TRIG"]["SEQ"]["OLINE"]
            gCommandTree["TRIG"]["SEQ"]["OUTP"] = gCommandTree["TRIG"]["SEQ"]["OUTPUT"]
            gCommandTree["TRIG"]["SEQ"]["TCON"]["ASYN"]["ILIN"] = gCommandTree["TRIG"]["SEQ"]["TCON"]["ASYN"]["ILINE"]
            gCommandTree["TRIG"]["SEQ"]["TCON"]["ASYN"]["OLIN"] = gCommandTree["TRIG"]["SEQ"]["TCON"]["ASYN"]["OLINE"]
            gCommandTree["TRIG"]["SEQ"]["TCON"]["ASYN"]["OUTP"] = gCommandTree["TRIG"]["SEQ"]["TCON"]["ASYN"]["OUTPUT"]
            gCommandTree["TRIG"]["SEQ"]["TCON"]["ILIN"] = gCommandTree["TRIG"]["SEQ"]["TCON"]["ILINE"]
            gCommandTree["TRIG"]["SEQ"]["TCON"]["OLIN"] = gCommandTree["TRIG"]["SEQ"]["TCON"]["OLINE"]
            gCommandTree["TRIG"]["SEQ"]["TCON"]["OUTP"] = gCommandTree["TRIG"]["SEQ"]["TCON"]["OUTPUT"]
        end
        
        gCommandTree["VOLT"] = gCommandTree["VOLTAGE"]
        
        -- State Variables Table
        local gStateVariables =
        {
        -- Calculate Subsystem
            Calc1_Stat,
            Calc1_Selected = {},
            Calc1_Selected_Index,
            Calc1_Undefined_Expression_Exists = false,    
            Calc2_Feed,
            Calc2_Null_Offs,
            Calc2_Null_Stat,
            Calc2_Lim1_Fail,
            Calc2_Lim1_Sour2,
            Calc2_Lim1_Stat, 
            Calc2_Lim1_Result,
            Calc2_Lim_Upp = {},
            Calc2_Lim_Upp_Sour2 = {},
            Calc2_Lim_Low = {},
            Calc2_Lim_Low_Sour2 = {},
            Calc2_Lim_Pass_Sour2 = {},
            Calc2_Lim_Stat = {},
            Calc2_Lim_Result = {},
            Calc2_Clim_Bcon,
            Calc2_Clim_Mode,
            Calc2_Clim_Cle_Auto,
            Calc2_Clim_Pass_Sour2,
            Calc2_Clim_Fail_Sour2,
            Calc2_Clim_Pass_Sml,
            Calc2_Clim_Fail_Sml,    
            Calc3_Form,     
              
        -- Display Subsystem
            Disp_Enab,
            Disp_Wind1_Text_Data,
            Disp_Wind2_Text_Data,
            Disp_State,
        
        -- Format Subsystem
            Form_Data_Type,
            Form_Elem_Sens1 = {},
            Form_Elem_Calc = {},
            Form_Sreg,
            Form_Sour2,    
            
        -- Output susbystem
            Outp_Smod,
            Outp_Interlock,
            
        -- Route Subsystem
            Route_Term,   
            
        -- Sense Subsystem
            Sens_Func_Conc,
            Sens_Func = {},
            Sens_Curr_Prot,
            Sens_Volt_Prot,   
            Sens_Curr_Prot_Rsyn,
            Sens_Volt_Prot_Rsyn,
            Sens_Res_Mode,
            Sens_Res_Range,
            
        -- Source Subsystem
            Sour_Cle_Auto_State,
            Sour_Cle_Auto_Mode,
            Sour_Func_Shape,
            Sour_Func_Mode,
            Sour_Curr_Mode,
            Sour_Curr_Trig_Ampl,
            Sour_Curr_Trig_Sfac,
            Sour_Curr_Trig_Sfac_State,
            Sour_Curr_Start,
            Sour_Curr_Stop,
            Sour_Curr_Step,
            Sour_Curr_Span,
            Sour_Curr_Cent,    
            Sour_Volt_Mode,
            Sour_Volt_Trig_Ampl,
            Sour_Volt_Trig_Sfac,
            Sour_Volt_Trig_Sfac_State,
            Sour_Volt_Start,
            Sour_Volt_Stop,
            Sour_Volt_Step,
            Sour_Volt_Span,
            Sour_Volt_Cent,
            Sour_Swe_Spac,
            Sour_Swe_Poin,
            Sour_Swe_Dir,
            Sour_Swe_Rang,
            Sour_Swe_Cab,
            Sour_List_Curr_Start,
            Sour_List_Curr_Values = {},
            Sour_List_Curr_Max,
            Sour_List_Volt_Start,
            Sour_List_Volt_Values = {},
            Sour_List_Volt_Max,
            Sour_Puls_Widt,
            Sour_Puls_Del,
            Sour_Mem_Poin,
            Sour_Mem_Start,
            Sour_Del,
            Sour_Del_Auto,
            Sour2_Bsize,
            Sour2_Bsize_MaxValue,
            Sour2_Ttl_Lev,
            Sour2_Ttl_Act,    
            Sour2_Ttl4_Mode,
            Sour2_Ttl4_Bst,
            Sour2_Cle_Auto,
            Sour2_Cle_Del,    
        
        -- System Subsystem
            Syst_Time_Res_Auto,
        
        -- Trigger Subsystem
            Arm_Sour,
            Arm_Tim,
            Arm_Dir,
            Arm_Ilin,
            Arm_Olin,
            Arm_Outp = {},    
            Trig_Del,
            Trig_Sour,
            Trig_Dir,
            Trig_Ilin,
            Trig_Inp,
            Trig_Olin,
            Trig_Outp = {},   
            
        -- TRACe Subsytem
            Trac_Poin,
            Trac_Feed,
            Trac_Cont,
            Trac_Tst_Form, 
        }
        
        --============================================================================
        --
        -- Error Queue
        --
        -- The lErrors table contain Error number and Error Message of
        -- status and error messages, state of the error(Enabled/Disabled)
        --
        -- The functions below assist in adding the errors to the error queue
        -- and print the error codes and messages
        --
        -- mStatusBit = 15 is a dummy value and does not effect any
        -- stauts register bits. Any other mStatusBit value
        -- updates the Standard Event Status Register.
        --
        ------------------------------------------------------------------------------
        
        local lErrors =
        {
            -- Error Events
            [-440] = {mState = true, mCode = "-440", mStatusBit = 2, mMessage = '-440,"Query UNTERMINATED after indefinite response"' },
            [-430] = {mState = true, mCode = "-430", mStatusBit = 2, mMessage = '-430,"Query DEADLOCKED"' },
            [-420] = {mState = true, mCode = "-420", mStatusBit = 2, mMessage = '-420,"Query UNTERMINATED"' },
            [-410] = {mState = true, mCode = "-410", mStatusBit = 2, mMessage = '-410,"Query INTERRUPTED"' },
            [-363] = {mState = true, mCode = "-363", mStatusBit = 3, mMessage = '-363,"Input buffer overrun"' },
            [-362] = {mState = true, mCode = "-362", mStatusBit = 3, mMessage = '-362,"Framing error in program message"' },
            [-361] = {mState = true, mCode = "-361", mStatusBit = 3, mMessage = '-361,"Parity error in program message"' },
            [-360] = {mState = true, mCode = "-360", mStatusBit = 3, mMessage = '-360,"Communications error"' },
            [-350] = {mState = true, mCode = "-350", mStatusBit = 3, mMessage = '-350,"Queue overflow"' },
        
            [-330] = {mState = true, mCode = "-330", mStatusBit = 3, mMessage = '-330,"Self-test failed"' },
            [-314] = {mState = true, mCode = "-314", mStatusBit = 3, mMessage = '-314,"Save/recall memory lost"' },
            [-315] = {mState = true, mCode = "-315", mStatusBit = 3, mMessage = '-315,"Configuration memory lost"' },
            [-285] = {mState = true, mCode = "-285", mStatusBit = 4, mMessage = '-285,"Program syntax error"' },
            [-284] = {mState = true, mCode = "-284", mStatusBit = 4, mMessage = '-284,"Program currently running"' },
            [-282] = {mState = true, mCode = "-282", mStatusBit = 4, mMessage = '-282,"Illegal program name"' },
            [-281] = {mState = true, mCode = "-281", mStatusBit = 4, mMessage = '-281,"Cannot create program"' },
            [-260] = {mState = true, mCode = "-260", mStatusBit = 4, mMessage = '-260,"Expression error"' },
            [-241] = {mState = true, mCode = "-241", mStatusBit = 4, mMessage = '-241,"Hardware missing"' },
            [-230] = {mState = true, mCode = "-230", mStatusBit = 4, mMessage = '-230,"Data corrupt or stale"' },
        
            [-225] = {mState = true, mCode = "-225", mStatusBit = 4, mMessage = '-225,"Out of memory"' },
            [-224] = {mState = true, mCode = "-224", mStatusBit = 4, mMessage = '-224,"Illegal parameter value"' },
            [-223] = {mState = true, mCode = "-223", mStatusBit = 4, mMessage = '-223,"Too much data"' },
            [-222] = {mState = true, mCode = "-222", mStatusBit = 4, mMessage = '-222,"Parameter data out of range"' },
            [-221] = {mState = true, mCode = "-221", mStatusBit = 4, mMessage = '-221,"Settings conflict"' },
            [-220] = {mState = true, mCode = "-220", mStatusBit = 4, mMessage = '-220,"Parameter error"' },
        
            [-215] = {mState = true, mCode = "-215", mStatusBit = 4, mMessage = '-215,"Arm deadlock"' },
            [-214] = {mState = true, mCode = "-214", mStatusBit = 4, mMessage = '-214,"Trigger deadlock"' },
            [-213] = {mState = true, mCode = "-213", mStatusBit = 4, mMessage = '-213,"Init ignored"' },
            [-212] = {mState = true, mCode = "-212", mStatusBit = 4, mMessage = '-212,"Arm ignored"' },
            [-211] = {mState = true, mCode = "-211", mStatusBit = 4, mMessage = '-211,"Trigger ignored"' },
            [-210] = {mState = true, mCode = "-210", mStatusBit = 4, mMessage = '-210,"Trigger error"' },
            [-202] = {mState = true, mCode = "-202", mStatusBit = 4, mMessage = '-202,"Settings lost due to rtl"' },
            [-201] = {mState = true, mCode = "-201", mStatusBit = 4, mMessage = '-201,"Invalid while in local"' },
            [-200] = {mState = true, mCode = "-200", mStatusBit = 4, mMessage = '-200,"Execution error"' },
            [-178] = {mState = true, mCode = "-178", mStatusBit = 5, mMessage = '-178,"Expression data not allowed"' },
            [-171] = {mState = true, mCode = "-171", mStatusBit = 5, mMessage = '-171,"Invalid expression"' },
            [-170] = {mState = true, mCode = "-170", mStatusBit = 5, mMessage = '-170,"Expression error"' },
            [-168] = {mState = true, mCode = "-168", mStatusBit = 5, mMessage = '-168,"Block data not allowed"' },
            [-161] = {mState = true, mCode = "-161", mStatusBit = 5, mMessage = '-161,"Invalid block data"' },
            [-160] = {mState = true, mCode = "-160", mStatusBit = 5, mMessage = '-160,"Block data error"' },
            [-158] = {mState = true, mCode = "-158", mStatusBit = 5, mMessage = '-158,"String data not allowed"' },
            [-154] = {mState = true, mCode = "-154", mStatusBit = 5, mMessage = '-154,"String too long"' },
            [-151] = {mState = true, mCode = "-151", mStatusBit = 5, mMessage = '-151,"Invalid string data"' },
            [-150] = {mState = true, mCode = "-150", mStatusBit = 5, mMessage = '-150,"String data error"' },
            [-148] = {mState = true, mCode = "-148", mStatusBit = 5, mMessage = '-148,"Character data not allowed"' },
        
            [-144] = {mState = true, mCode = "-144", mStatusBit = 5, mMessage = '-144,"Character data too long"' },
            [-141] = {mState = true, mCode = "-141", mStatusBit = 5, mMessage = '-141,"Invalid character data"' },
            [-140] = {mState = true, mCode = "-140", mStatusBit = 5, mMessage = '-140,"Character data error"' },
            [-128] = {mState = true, mCode = "-128", mStatusBit = 5, mMessage = '-128,"Numeric data not allowed"' },
            [-124] = {mState = true, mCode = "-124", mStatusBit = 5, mMessage = '-124,"Too many digits"' },
        
            [-123] = {mState = true, mCode = "-123", mStatusBit = 5, mMessage = '-123,"Exponent too large"' },
            [-121] = {mState = true, mCode = "-121", mStatusBit = 5, mMessage = '-121,"Invalid character in number"' },
            [-120] = {mState = true, mCode = "-120", mStatusBit = 5, mMessage = '-120,"Numeric data error"' },
            [-114] = {mState = true, mCode = "-114", mStatusBit = 5, mMessage = '-114,"Header suffix out of range"' },
            [-113] = {mState = true, mCode = "-113", mStatusBit = 5, mMessage = '-113,"Undefined header"' },
        
            [-112] = {mState = true, mCode = "-112", mStatusBit = 5, mMessage = '-112,"Program mnemonic too long"' },
            [-111] = {mState = true, mCode = "-111", mStatusBit = 5, mMessage = '-111,"Header separator error"' },
            [-110] = {mState = true, mCode = "-110", mStatusBit = 5, mMessage = '-110,"Command header error"' },
            [-109] = {mState = true, mCode = "-109", mStatusBit = 5, mMessage = '-109,"Missing parameter"' },
            [-108] = {mState = true, mCode = "-108", mStatusBit = 5, mMessage = '-108,"Parameter not allowed"' },
        
            [-105] = {mState = true, mCode = "-105", mStatusBit = 5, mMessage = '-105,"GET not allowed"' },
            [-104] = {mState = true, mCode = "-104", mStatusBit = 5, mMessage = '-104,"Data type error"' },
            [-103] = {mState = true, mCode = "-103", mStatusBit = 5, mMessage = '-103,"Invalid separator"' },
            [-102] = {mState = true, mCode = "-102", mStatusBit = 5, mMessage = '-102,"Syntax error"' },
            [-101] = {mState = true, mCode = "-101", mStatusBit = 5, mMessage = '-101,"Invalid character"' },
            [-100] = {mState = true, mCode = "-100", mStatusBit = 5, mMessage = '-100,"Command error"' },
        
            -- Status Events
            -- Measurement events:
            [0]   = {mState = false, mCode = "0", mStatusBit = 15, mMessage = '0,"No error"' },
            [100] = {mState = false, mCode = "100", mStatusBit = 15, mMessage = '100,"Limit 1 failed"' },
            [101] = {mState = false, mCode = "101", mStatusBit = 15, mMessage = '101,"Low limit 2 failed"' },
            [102] = {mState = false, mCode = "102", mStatusBit = 15, mMessage = '102,"High limit 2 failed"' },
            [103] = {mState = false, mCode = "103", mStatusBit = 15, mMessage = '103,"Low limit 3 failed"' },
            [104] = {mState = false, mCode = "104", mStatusBit = 15, mMessage = '104,"High limit 3 failed"' },
            [105] = {mState = false, mCode = "105", mStatusBit = 15, mMessage = '105,"Active limit tests passed"' },
            [106] = {mState = false, mCode = "106", mStatusBit = 15, mMessage = '106,"Reading available"' },
            [107] = {mState = false, mCode = "107", mStatusBit = 15, mMessage = '107,"Reading overflow"' },
            [108] = {mState = false, mCode = "108", mStatusBit = 15, mMessage = '108,"Buffer available"' },
            [109] = {mState = false, mCode = "109", mStatusBit = 15, mMessage = '109,"Buffer full"' },
            [110] = {mState = false, mCode = "110", mStatusBit = 15, mMessage = '110,"Limit 4 failed"' },
            [111] = {mState = false, mCode = "111", mStatusBit = 15, mMessage = '111,"OUTPUT enable asserted"' },
            [112] = {mState = false, mCode = "112", mStatusBit = 15, mMessage = '112,"Temperature limit exceeded"' },
            [113] = {mState = false, mCode = "113", mStatusBit = 15, mMessage = '113,"Voltage limit exceeded"' },
            [114] = {mState = false, mCode = "114", mStatusBit = 15, mMessage = '114,"Source in compliance"' },
        
            -- Standard events:
            [200] = {mState = false, mCode = "200", mStatusBit = 15, mMessage = '200,"Operation complete"' },
        
            -- Operation events:
            [300] = {mState = false, mCode = "300", mStatusBit = 15, mMessage = '300,"Device calibrating"' },
            [303] = {mState = false, mCode = "303", mStatusBit = 15, mMessage = '303,"Device sweeping"' },
            [305] = {mState = false, mCode = "305", mStatusBit = 15, mMessage = '305,"Waiting in trigger layer"' },
            [306] = {mState = false, mCode = "306", mStatusBit = 15, mMessage = '306,"Waiting in arm layer"' },
            [310] = {mState = false, mCode = "310", mStatusBit = 15, mMessage = '310,"Entering idle layer"' },
        
            -- Questionable events:
            [408] = {mState = false, mCode = "408", mStatusBit = 15, mMessage = '408,"Questionable Calibration"' },
            [414] = {mState = false, mCode = "414", mStatusBit = 15, mMessage = '414,"Command Warning"' },
        
            -- Error Events
            -- Calibration errors:
            [500] = {mState = true, mCode = "500", mStatusBit = 3, mMessage = '500,"Date of calibration not set"' },
            [501] = {mState = true, mCode = "501", mStatusBit = 3, mMessage = '501,"Next date of calibration not set"' },
            [502] = {mState = true, mCode = "502", mStatusBit = 3, mMessage = '502,"Calibration data invalid"' },
            [503] = {mState = true, mCode = "503", mStatusBit = 3, mMessage = '503,"DAC calibration overflow"' },
            [504] = {mState = true, mCode = "504", mStatusBit = 3, mMessage = '504,"DAC calibration underflow"' },
            [505] = {mState = true, mCode = "505", mStatusBit = 3, mMessage = '505,"Source offset data invalid"' },
            [506] = {mState = true, mCode = "506", mStatusBit = 3, mMessage = '506,"Source gain data invalid"' },
            [507] = {mState = true, mCode = "507", mStatusBit = 3, mMessage = '507,"Measurement offset data invalid"' },
            [508] = {mState = true, mCode = "508", mStatusBit = 3, mMessage = '508,"Measurement gain data invalid"' },
            [509] = {mState = true, mCode = "509", mStatusBit = 3, mMessage = '509,"Not permitted with cal locked"' },
            [510] = {mState = true, mCode = "510", mStatusBit = 3, mMessage = '510,"Not permitted with cal un-locked"' },
        
            -- Lost data errors:
            [601] = {mState = true, mCode = "601", mStatusBit = 3, mMessage = '601,"Reading buffer data lost"' },
            [602] = {mState = true, mCode = "602", mStatusBit = 3, mMessage = '602,"GPIB address lost"' },
            [603] = {mState = true, mCode = "603", mStatusBit = 3, mMessage = '603,"Power-on state lost"' },
            [604] = {mState = true, mCode = "604", mStatusBit = 3, mMessage = '604,"DC calibration data lost"' },
            [605] = {mState = true, mCode = "605", mStatusBit = 3, mMessage = '605,"Calibration dates lost"' },
            [606] = {mState = true, mCode = "606", mStatusBit = 3, mMessage = '606,"GPIB communication language lost"' },
        
            -- Communication errors:
            [700] = {mState = true, mCode = "700", mStatusBit = 3, mMessage = '700,"Invalid system communication"' },
            [701] = {mState = true, mCode = "701", mStatusBit = 3, mMessage = '701,"ASCII only with RS-232"' },
            [702] = {mState = true, mCode = "702", mStatusBit = 3, mMessage = '702,"Preamp Timeout"' },
        
            -- Additional command execution errors:
            [800] = {mState = true, mCode = "800", mStatusBit = 4, mMessage = '800,"Illegal with storage active"' },
            [801] = {mState = true, mCode = "801", mStatusBit = 4, mMessage = '801,"Insufficient vector data"' },
            [802] = {mState = true, mCode = "802", mStatusBit = 4, mMessage = '802,"OUTPUT blocked by output enable"' },
            [803] = {mState = true, mCode = "803", mStatusBit = 4, mMessage = '803,"Not permitted with OUTPUT off"' },
            [804] = {mState = true, mCode = "804", mStatusBit = 4, mMessage = '804,"Expression list full"' },
            [805] = {mState = true, mCode = "805", mStatusBit = 4, mMessage = '805,"Undefined expression exists"' },
            [806] = {mState = true, mCode = "806", mStatusBit = 4, mMessage = '806,"Expression not found"' },
            [807] = {mState = true, mCode = "807", mStatusBit = 4, mMessage = '807,"Definition not allowed"' },
            [808] = {mState = true, mCode = "808", mStatusBit = 4, mMessage = '808,"Expression cannot be deleted"' },
            [809] = {mState = true, mCode = "809", mStatusBit = 4, mMessage = '809,"Source memory location revised"' },
            [810] = {mState = true, mCode = "810", mStatusBit = 4, mMessage = '810,"OUTPUT blocked by Over Temp"' },
            [811] = {mState = true, mCode = "811", mStatusBit = 4, mMessage = '811,"Not an operator or number"' },
            [812] = {mState = true, mCode = "812", mStatusBit = 4, mMessage = '812,"Mismatched parenthesis"' },
            [813] = {mState = true, mCode = "813", mStatusBit = 4, mMessage = '813,"Not a number of data handle"' },
            [814] = {mState = true, mCode = "814", mStatusBit = 4, mMessage = '814,"Mismatched brackets"' },
            [815] = {mState = true, mCode = "815", mStatusBit = 4, mMessage = '815,"Too many parenthesis"' },
            [816] = {mState = true, mCode = "816", mStatusBit = 4, mMessage = '816,"Entire expression not parsed"' },
            [817] = {mState = true, mCode = "817", mStatusBit = 4, mMessage = '817,"Unknown token"' },
            [818] = {mState = true, mCode = "818", mStatusBit = 4, mMessage = '818,"Error parsing mantissa"' },
            [819] = {mState = true, mCode = "819", mStatusBit = 4, mMessage = '819,"Error parsing exponent"' },
            [820] = {mState = true, mCode = "820", mStatusBit = 4, mMessage = '820,"Error parsing value"' },
            [821] = {mState = true, mCode = "821", mStatusBit = 4, mMessage = '821,"Invalid data handle index"' },
            [822] = {mState = true, mCode = "822", mStatusBit = 4, mMessage = '822,"Too small for sense range"' },
            [823] = {mState = true, mCode = "823", mStatusBit = 4, mMessage = '823,"Invalid with source read-back on"' },
            [824] = {mState = true, mCode = "824", mStatusBit = 4, mMessage = '824,"Cannot exceed compliance range"' },
            [825] = {mState = true, mCode = "825", mStatusBit = 4, mMessage = '825,"Invalid with auto-ohms on"' },
            [826] = {mState = true, mCode = "826", mStatusBit = 4, mMessage = '826,"Attempt to exceed power limit"' },
            [827] = {mState = true, mCode = "827", mStatusBit = 4, mMessage = '827,"Invalid with ohms guard on"' },
            [828] = {mState = true, mCode = "828", mStatusBit = 4, mMessage = '828,"Invalid on 1 amp range"' },
            [829] = {mState = true, mCode = "829", mStatusBit = 4, mMessage = '829,"Invalid on 1kV range"' },
            [830] = {mState = true, mCode = "830", mStatusBit = 4, mMessage = '830,"Invalid with INF ARM:COUNT"' },
            [831] = {mState = true, mCode = "831", mStatusBit = 4, mMessage = '831,"Invalid in Pulse Mode"' },
            [900] = {mState = true, mCode = "900", mStatusBit = 3, mMessage = '900,"Internal System Error"' }
        }
        
        ------------------------------------------------------------------------------
        --
        -- gErrorQueue.Add
        --
        -- Put an error into the error queue.
        --
        ------------------------------------------------------------------------------
        
        gErrorQueue.Add = function (lErrorNumber)
            local lError = lErrors[lErrorNumber]
               
            if lError.mStatusBit ~= 15 then
                StatusModel.SetEvent(standardStatus, lError.mStatusBit + 1)
            end
        
            if lError.mState then
                local lCount = table.getn(gErrorQueue)
        
                if lCount < 8 then
                    table.insert(gErrorQueue, lError)
                    StatusModel.SetSummary(3)
                elseif lCount == 8 then
                    table.insert(gErrorQueue, lErrors[-350])
                end    
                -- Display Error Message on Front Panel and Beep
                if gDisplayErrors then        
                    local lDisplayScreen = display.screen
                    display.screen = display.USER
                    local lDisplayText1 = display.gettext(false, 1)
                    local lDisplayText2 = display.gettext(false, 2)     
                    display.clear()
                    display.setcursor(1, 1)
                    display.settext("ERROR ID: CODE = ")
                    display.setcursor(2, 1)
                    display.settext(lError.mMessage)
                    if beeper.enable == beeper.ON then
                        beeper.beep(0.8, 50)
                    end
                    delay(2)        
                    display.setcursor(1, 1)
                    display.settext(lDisplayText1)
                    display.setcursor(2, 1)
                    display.settext(lDisplayText2)
                    display.screen = lDisplayScreen
                end
            end
        end
        
        --[[
            ReadErrorQueue prints the errors from the error queue
            if the queue is empty '0,"No error"' is printed
        --]]
        gErrorQueue.ReadError = function ()
            local lCount = table.getn(gErrorQueue)
            
            if lCount == 0 then
                Print('0,"No error"')
            else
                Print(gErrorQueue[1].mMessage)
                table.remove(gErrorQueue, 1)
                if lCount == 1 then
                    StatusModel.ClearSummary(3)
                end
            end
        end
        
        --[[
            ReadErrorCode prints the error codes from the error queue
            if the queue is empty '0' is printed
        --]]
        gErrorQueue.ReadErrorCode = function ()
            local lCount = table.getn(gErrorQueue)
            
            if lCount == 0 then
                Print('0')
            else
                Print(gErrorQueue[1].mCode)
                table.remove(gErrorQueue, 1)
                if lCount == 1 then
                    StatusModel.ClearSummary(3)
                end
            end
        end
        
        --[[
            ErrorCount prints the number of errors in the queue
        --]]
        gErrorQueue.ErrorCount = function ()
            Print(tostring(table.getn(gErrorQueue)))
        end
        
        --[[
            ReadErrorAll prints all the errors from the error queue
            and clears the error queue.
            if the queue is empty '0,"No error"' is printed
        --]]
        gErrorQueue.ReadErrorAll = function ()
            if table.getn(gErrorQueue) == 0 then
                Print('0,"No error"')
            else
                for i = 1, table.getn(gErrorQueue) do
                    if i > 1 then
                        Print(',')
                    end
                    Print(gErrorQueue[1].mMessage)
                    table.remove(gErrorQueue, 1)
                end
                StatusModel.ClearSummary(3)
            end
        end
        
        --[[
            ReadErrorCodeAll prints all the error codes from the error queue
            and clears the error queue.
            if the queue is empty '0' is printed
        --]]
        gErrorQueue.ReadErrorCodeAll = function ()
            if table.getn(gErrorQueue) == 0 then
                Print('0')
            else
                for i = 1, table.getn(gErrorQueue) do
                    if i > 1 then
                        Print(',')
                    end
                    Print(gErrorQueue[1].mCode)
                    table.remove(gErrorQueue, 1)
                end
                StatusModel.ClearSummary(3)
            end
        end
        
        --[[
            Clear removes all the errors from the error queue
        --]]
        gErrorQueue.Clear = function ()
            if table.getn(gErrorQueue) == 0 then
                return
            else
                for i = 1, table.getn(gErrorQueue) do
                    table.remove(gErrorQueue, 1)
                end
                StatusModel.ClearSummary(3)
            end
        end
        
        --[[
            DisableAllErrorEvents disables all the error and statue events
        --]]
        gErrorQueue.DisableAllErrorEvents = function ()
            for k, v in pairs(lErrors) do
                lErrors[k].mState = false
            end
        end
        
        --[[
            ChangeErrorEventState sets the state of the error events in lErrors table
        --]]
        gErrorQueue.ChangeErrorEventState = function (lStart, lStop, lState)
            -- if start index is greater than end index swap them
            if lStart > lStop then
               local tempStart = lStart
               lStart = lStop
               lStop = tempStart
            end
        
            -- Set the state
            for k = lStart, lStop do
                if lErrors[k] then
                    lErrors[k].mState = lState
                end
            end
        end
        
        --[[
            EnableErrorEvents enables the spcecified list of error and statue events
            and disables the rest
        --]]
        gErrorQueue.EnableErrorEvents = function (lEventNumList)
            gErrorQueue.DisableAllErrorEvents()
            for k = 1, table.getn(lEventNumList), 2 do
                gErrorQueue.ChangeErrorEventState(lEventNumList[k], lEventNumList[k+1], true)
            end
        end
        
        --[[
            DisableErrorEvents disable the spcecified list of error and statue events
        --]]
        gErrorQueue.DisableErrorEvents = function (lEventNumList)
            --if table.getn(lEventNumList) then
                for k = 1, table.getn(lEventNumList), 2 do
                    gErrorQueue.ChangeErrorEventState(lEventNumList[k], lEventNumList[k+1], false)
                end
            --end
        end
        
        --[[
            PrintErrorEvents prints the list Enabled/Disabled error and statue events
        --]]
        gErrorQueue.PrintErrorEvents = function (lState)
            local lAddToPrintQue = true
            local lStart, lEnd
            local lCount = 0
            local lComma = false
            
            Print("(")
            for i = -440, 900 do
                if lErrors[i] then
                    if lErrors[i].mState == lState then
                        if lAddToPrintQue then
                            lStart = lErrors[i].mCode
                            lAddToPrintQue = false
                        end
                        lEnd = lErrors[i].mCode
                        lCount = lCount + 1
                    else
                        if lAddToPrintQue == false then
                            if lCount > 1 then
                                if lComma then
                                    Print(",")
                                end
                                if tonumber(lStart) >= 0 then
                                   Print("+")
                                end
                                Print(lStart)
                                Print(":")
                                if tonumber(lEnd) >= 0 then
                                   Print("+")
                                end
                                Print(lEnd)
                                lComma = true
                                lCount = 0
                                lAddToPrintQue = true
                            else
                                if lComma then
                                    Print(",")
                                end
                                if tonumber(lEnd) >= 0 then
                                   Print("+")
                                end
                                Print(lEnd)
                                lComma = true
                                lCount = 0
                                lAddToPrintQue = true
                            end
                        end
                    end
                end
            end
            if lCount > 1 then
                if lComma then
                    Print(",")
                end
                if tonumber(lStart) >= 0 then
                   Print("+")
                end
                Print(lStart)
                Print(":")
                if tonumber(lEnd) >= 0 then
                   Print("+")
                end
                Print(lEnd)
            elseif lCount == 1 then
                if lComma then
                    Print(",")
                end
                if tonumber(lEnd) >= 0 then
                   Print("+")
                end
                Print(lEnd)
            end
            Print(")")
        end
        
        ------------------------------------------------------------------------------
         -- Global variable declarations
         --[[
                These variables are global to the Persona2400 script but are
                local outside the script
         --]]
        ------------------------------------------------------------------------------
        -- Trace Buffer
        local gTraceBuffer = {mVoltage = {}, mCurrent = {}, mResistance = {}, mStatus = {}, mTime = {}, mData = {}, mCount = 0}
        
        -- Sample Buffer
        gSampleBuffer = {mVoltage = {}, mCurrent = {}, mResistance = {}, mStatus = {}, mTime = {}, mCount = 0}
        
        -- Intermediate sample buffer used for math equations
        gIntermediateSampleBuffer = {mVoltage = {}, mCurrent = {}, mResistance = {}, mStatus = {}, mTime = {}, mCount = 0}
        
        -- Calculate1 Data Buffer
        local gCalculate1Buffer = {mData = {}, mTime = {}, mStatus = {}, mCount = 0}
        
        -- Calculate2 Data Buffer
        local gCalculate2Buffer = {mData = {}, mTime = {}, mStatus = {}, mCount = 0}
        
        -- Calc 1 buffer index
        local gCalc1BufferIndex = 1
        
        -- Flags to check if Limits or Null offset is enabled in calc2
        local gCalculate2 = {mLimits = false, mNullOffset = false}
        
        -- Source memory location that is being executed
        local gMemoryLocation
        -- Source memory slot indexed by gMemoryLocation
        local gMemorySlot
        -- Next Source memory location (source memory sweeps brancing operations)
        local gNextMemoryLocation
        
        -- Sample buffer Index
        local gSampleBufferIndex
        
        -- Calculate2 buffer Index
        local gCalc2BufferIndex
        
        -- Runs the sourmemSweep
        local InitiateSourceMemorySweep
        
        local gInsertComma
        local gProcessedAtleastOneLimit = false
        
        -- First failure limit(upper/lower), First failure test (limit1, 2, 3, 5-12), Failed limit (upper/lower)
        local gLimitCapture = {mFirstFailureLimit = 0, mFirstFailureTest = 0, mFailedLimit, mFailedMemoryLocation}
        
        -- system Clock variable
        local gSystemClockOffset
        
        -- status word of the reading buffer
        local gStatusWord = 0
        
        -- list sweep values
        local gListSweep = {}
        
        -- stores the state of the smu when the measurements are turned off
        local gSmuState = {}
        
        local gSweepPoints = 0
        
        local gAbortExecuted = false
        local gTrgExecuted = false
        
        -- Calculate1 subsystem math catalog
        local gMathCatalog = { [1] = "POWER", [2] = "OFFCOMPOHM", [3] = "VOLTCOEF", [4] = "VARALPHA"}
        
        -- Calculate1 subsystem math expressions
        local SetupNonVolatileExpressions = function ()
            gMathCatalog["POWER"] = {}
            gMathCatalog["POWER"].mExpression = BuildExpression("(VOLT*CURR)", 1)
            gMathCatalog["POWER"].mName = "POWER"
            gMathCatalog["POWER"].mUnits = 'W  '
            gMathCatalog["POWER"].mTempUnits = 'W  '
            gMathCatalog["POWER"].mDefined = true
        
            gMathCatalog["OFFCOMPOHM"] = {}
            gMathCatalog["OFFCOMPOHM"].mExpression = BuildExpression("(ABS((VOLT[1]-VOLT[0])/(CURR[1]-CURR[0])))", 1)
            gMathCatalog["OFFCOMPOHM"].mName = "OFFCOMPOHM"
            gMathCatalog["OFFCOMPOHM"].mUnits = '   '
            gMathCatalog["OFFCOMPOHM"].mTempUnits = '   '
            gMathCatalog["OFFCOMPOHM"].mDefined = true
        
            gMathCatalog["VOLTCOEF"] = {}
            gMathCatalog["VOLTCOEF"].mExpression = BuildExpression("((RES[1]-RES[0])/RES[0]/(VOLT[1]-VOLT[0])*100)", 1)
            gMathCatalog["VOLTCOEF"].mName = "VOLTCOEF"
            gMathCatalog["VOLTCOEF"].mUnits = '%/V'
            gMathCatalog["VOLTCOEF"].mTempUnits = '%/V'
            gMathCatalog["VOLTCOEF"].mDefined = true
        
            gMathCatalog["VARALPHA"] = {}
            gMathCatalog["VARALPHA"].mExpression = BuildExpression("(LOG(CURR[1]/CURR[0])/LOG(VOLT[1]/VOLT[0]))", 1)
            gMathCatalog["VARALPHA"].mName = "VARALPHA"
            gMathCatalog["VARALPHA"].mUnits = '\170  '
            gMathCatalog["VARALPHA"].mTempUnits = '\170  '
            gMathCatalog["VARALPHA"].mDefined = true
        end
        
        -----------------------------------------------------------------------------
        -- Source memory sweep structure
        --[[
            These tables hold the sourcememory sweep settings
        --]]
        -----------------------------------------------------------------------------
        --[[
            Scratch pad memory location which gets updated when the settings are changed
        --]]
        local lMemScratch = {}
        
        --[[
            Initialize the sourcememory sweep settings
        --]]
        local lsourceMemInit =
        {
            Sens_Nplc = 1,
            Sens_Func_Conc = true,
            Sens_Func_Volt = false,
            Sens_Func_Curr = true,
            Sens_Func_Res = false,
            Sens_Func_Any = true,
            --Sens_Func_Off,
            Sens_Res_Mode = "MAN",
            Sens_Aver_Stat = smua.FILTER_OFF,
            Sens_Aver_Tcon = smua.FILTER_REPEAT_AVG,
            --Sens_Res_Ocom = 0,
            Sens_Aver_Coun = 10,
            Sour_Func_Shap = "DC",
            Sour_Func_Mode = gDCVOLTS,
            Sour_Del = 0, Sour_Del_Auto = true,
            Sour_Curr_Trig_Sfac = 1,
            Sour_Volt_Trig_Sfac = 1,
            Sour_Curr_Trig_Sfac_Stat = false,
            Sour_Volt_Trig_Sfac_Stat = false,
            Sour_Curr_Ampl = 0,
            Sour_Volt_Ampl = 0,
            --Sour_Puls_Width = .00015,
            --Sour_Puls_Del = 0,
            Sour_Curr_Rang = 1.0e-4,
            Sour_Volt_Rang = 20,
            Sour_Curr_Rang_Auto = 1,
            Sour_Volt_Rang_Auto = 1,
            Sens_Curr_Prot = 1.0e-4,
            Sens_Volt_Prot = 20,
            Actual_Volt_Prot = 20,
            Actual_Curr_Prot = 1e-4,
            Sens_Curr_Rang = 1.0e-4,
            Sens_Volt_Rang = 20,
            Sens_Curr_Rang_Auto = 1,
            Sens_Volt_Rang_Auto = 1,
            Syst_Azer_Stat = smua.AUTOZERO_AUTO,
            Syst_Rsen = smua.SENSE_LOCAL,
            --Rout_Term,
            Calc1_Stat = false,
            Calc1_Math_Name = "POWER",
            Calc2_Feed = "VOLT",
            Calc2_Null_Offs = 0,
            Calc2_Null_Stat = false,
            Calc2_Lim1_Stat = false,
            Calc2_Lim1_Fail = "IN",
            Calc2_Lim1_Sour2 = 15,
            Calc2_Lim2_Stat = false,
            Calc2_Lim2_Upp = 1,
            Calc2_Lim2_Upp_Sour2 = 15,
            Calc2_Lim2_Low = -1,
            Calc2_Lim2_Low_Sour2 = 15,
            Calc2_Lim2_Pass_Sour2 = 15,
            Calc2_Lim3_Stat = false,
            Calc2_Lim3_Upp = 1,
            Calc2_Lim3_Upp_Sour2 = 15,
            Calc2_Lim3_Low = -1,
            Calc2_Lim3_Low_Sour2 = 15,
            Calc2_Lim3_Pass_Sour2 = 15,
            --[[
            Calc2_Lim4_Stat = false,
            Calc2_Lim4_Upp = 1,
            Calc2_Lim4_Upp_Sour2 = 15,
            Calc2_Lim4_Low = -1,
            Calc2_Lim4_Low_Sour2 = 15,
            Calc2_Lim4_Pass_Sour2 = 15,
            --]]
            Calc2_Lim5_Stat = false,
            Calc2_Lim5_Upp = 1,
            Calc2_Lim5_Upp_Sour2 = 15,
            Calc2_Lim5_Low = -1,
            Calc2_Lim5_Low_Sour2 = 15,
            Calc2_Lim5_Pass_Sour2 = 15,
            Calc2_Lim6_Stat = false,
            Calc2_Lim6_Upp = 1,
            Calc2_Lim6_Upp_Sour2 = 15,
            Calc2_Lim6_Low = -1,
            Calc2_Lim6_Low_Sour2 = 15,
            Calc2_Lim6_Pass_Sour2 = 15,
            Calc2_Lim7_Stat = false,
            Calc2_Lim7_Upp = 1,
            Calc2_Lim7_Upp_Sour2 = 15,
            Calc2_Lim7_Low = -1,
            Calc2_Lim7_Low_Sour2 = 15,
            Calc2_Lim7_Pass_Sour2 = 15,
            Calc2_Lim8_Stat = false,
            Calc2_Lim8_Upp = 1,
            Calc2_Lim8_Upp_Sour2 = 15,
            Calc2_Lim8_Low = -1,
            Calc2_Lim8_Low_Sour2 = 15,
            Calc2_Lim8_Pass_Sour2 = 15,
            Calc2_Lim9_Stat = false,
            Calc2_Lim9_Upp = 1,
            Calc2_Lim9_Upp_Sour2 = 15,
            Calc2_Lim9_Low = -1,
            Calc2_Lim9_Low_Sour2 = 15,
            Calc2_Lim9_Pass_Sour2 = 15,
            Calc2_Lim10_Stat = false,
            Calc2_Lim10_Upp = 1,
            Calc2_Lim10_Upp_Sour2 = 15,
            Calc2_Lim10_Low = -1,
            Calc2_Lim10_Low_Sour2 = 15,
            Calc2_Lim10_Pass_Sour2 = 15,
            Calc2_Lim11_Stat = false,
            Calc2_Lim11_Upp = 1,
            Calc2_Lim11_Upp_Sour2 = 15,
            Calc2_Lim11_Low = -1,
            Calc2_Lim11_Low_Sour2 = 15,
            Calc2_Lim11_Pass_Sour2 = 15,
            Calc2_Lim12_Stat = false,
            Calc2_Lim12_Upp = 1,
            Calc2_Lim12_Upp_Sour2 = 15,
            Calc2_Lim12_Low = -1,
            Calc2_Lim12_Low_Sour2 = 15,
            Calc2_Lim12_Pass_Sour2 = 15,
            Calc2_Clim_Pass_Sour2 = 15,
            Calc2_Clim_Fail_Sour2 = 15,
            Calc2_Clim_Pass_Sml = "NEXT",
            Calc2_Clim_Fail_Sml = "NEXT",
            Trig_Del = 0,
        }
        
        --[[
            gMemLoc holds 100 sourcememory locations, each location is a table which holds
            all the settings initialized in lsourceMemInit table
        --]]
        local gMemLoc = {}
        
        for lIndex = 1, 100 do
            gMemLoc[lIndex] = {}
        end
        
        ------------------------------------------------------------------------------
        -- General utility functions
        --[[
            These functions are used at various places in the script
        --]]
        -----------------------------------------------------------------------------
        
        --[[
            SetWithoutDelay executes the command (parameter of the function should be a command)
            without delay. The functions stores the gSource.delay,
            executes the command and sets back the delay
        --]]
        local SetWithoutDelay = function (lCommand)
            -- save the delay
            local lTempDelay = gAccessors.mGetSourceDelay()
            
            -- set delay to 0
            gAccessors.mSetSourceDelay(0)
            -- execute the command
            lCommand()
            -- restore original delay
            gAccessors.mSetSourceDelay(lTempDelay)
        end
        
        --[[
            ReArrangeList rearranges the list sweep table depending on the start point
        --]]
        local ReArrangeList = function (lStart, lListTable)
            local lCount = table.getn(lListTable)
        
            if lStart > lCount then
                gListSweep = lListTable
                return
            end
            gListSweep = {}
            for i = 1, lCount do
                gListSweep[i] = lListTable[lStart]
                lStart = lStart + 1
                if lStart > lCount then
                    lStart = 1
                end
            end
        end
        
        --[[
            UpdateVoltageStep updates the :SOURCE:VOLTAGE:STEP, :SOURCE:VOLTAGE:POINTS when ever
            SOURCE:VOLTAGE:START, STOP, SPAN and CENTER are updated
        --]]
        local UpdateVoltageStep = function ()
            gStateVariables.Sour_Volt_Step =
            gStateVariables.Sour_Volt_Span / (gStateVariables.Sour_Swe_Poin - 1)
        end
        
        --[[
            UpdateCurrentStep updates the :SOURCE:CURRENT:STEP, :SOURCE:CURRENT:POINTS when ever
            SOURCE:CURRENT:START, STOP, SPAN and CENTER are updated
        --]]
        local UpdateCurrentStep = function ()
            gStateVariables.Sour_Curr_Step =
            gStateVariables.Sour_Curr_Span / (gStateVariables.Sour_Swe_Poin - 1)
        end
        
        --[[
            ToBinary converts an ascii number to a binary string
        --]]
        local ToBinary = function (lValue)
            local binString = "#B"
            
            for i = 16, 1, -1  do
                if bit.test(lValue, i) then
                    binString = binString .. '1'
                else
                    binString = binString .. '0'
                end
            end
            return binString
        end
        
        ------------------------------------------------------------------------------
        -- Print functions
        --
        -- These functions are used to format and print data
        --
        -----------------------------------------------------------------------------
        
        local PrintDataBuffer = function (lStart, lStop, lBuffer, lDeltas)
            local lInsertComma = false
            local lUseCommas = gAccessors.mGetFormatData() == gAscii
            local lReferenceTime = lBuffer.mTime[1]
        
            for lIndex = lStart, lStop do
                if gStateVariables.Form_Elem_Sens1.VOLT then
                    if lInsertComma then
                        Print(",")
                    end
                    PrintNumber(lBuffer.mVoltage[lIndex])
                    lInsertComma = lUseCommas
                end
                if gStateVariables.Form_Elem_Sens1.CURR then
                    if lInsertComma then
                        Print(",")
                    end
                    PrintNumber(lBuffer.mCurrent[lIndex])
                    lInsertComma = lUseCommas
                end
                if gStateVariables.Form_Elem_Sens1.RES then
                    if lInsertComma then
                        Print(",")
                    end
                    PrintNumber(lBuffer.mResistance[lIndex])
                    lInsertComma = lUseCommas
                end
                if gStateVariables.Form_Elem_Sens1.TIME then
                    if lInsertComma then
                        Print(",")
                    end
                    if lDeltas then
                        PrintNumber(lBuffer.mTime[lIndex] - lReferenceTime)
                        if gStateVariables.Trac_Tst_Form == "DELT" then
                            lReferenceTime = lBuffer.mTime[lIndex]
                        end
                    else
                        PrintNumber(lBuffer.mTime[lIndex])
                    end
                    lInsertComma = lUseCommas
                end
                if gStateVariables.Form_Elem_Sens1.STAT then
                    if lInsertComma then
                        Print(",")
                    end
                    PrintNumber(lBuffer.mStatus[lIndex])
                    lInsertComma = lUseCommas
                end
            end
        end
        
        --[[
            PrintTraceBuffer formats the Trace Buffer data and prints out the elements
            in the format specified by FORM:ELEM command
        --]]
        local PrintTraceBuffer = function (lStart, lStop)
            PrintDataBuffer(lStart, lStop, gTraceBuffer, true)
        end
        
        --[[
            PrintSampleBuffer formats the Sample Buffer data and prints out the elements
            in the format specified by FORM:ELEM command
        --]]
        local PrintSampleBuffer = function (lStart, lStop)
            PrintDataBuffer(lStart, lStop, gSampleBuffer, false)
        end
        
        --[[
            PrintCalculateBuffer formats the Calculate1,calculate2 Buffer data and prints out the elements
            in the format specified by FORM:ELEM command
        --]]
        local PrintCalculateBuffer = function (lStart, lStop, lBuffer)
            local lInsertComma = false
            local lUseCommas = gAccessors.mGetFormatData() == gAscii
        
            for lIndex = lStart, lStop do
                if gStateVariables.Form_Elem_Calc.CALC then
                    if lInsertComma then
                        Print(",")
                    end
                    PrintNumber(lBuffer.mData[lIndex])
                    lInsertComma = lUseCommas
                end
                if gStateVariables.Form_Elem_Calc.TIME then
                    if lInsertComma then
                        Print(",")
                    end
                    PrintNumber(lBuffer.mTime[lIndex])
                    lInsertComma = lUseCommas
                end
                if gStateVariables.Form_Elem_Calc.STAT then
                    if lInsertComma then
                        Print(",")
                    end
                    PrintNumber(lBuffer.mStatus[lIndex])
                    lInsertComma = lUseCommas
                end
            end
        end
        
        --[[
            PrintImmediate formats the sample buffer data and prints out the elements
            in the format specified by FORM:ELEM command this function
            is used to print out the data while the sweep is running
        --]]
        local PrintImmediate = function (lIndex)
            local lUseCommas = gAccessors.mGetFormatData() == gAscii
            
            if gStateVariables.Form_Elem_Sens1.VOLT then
                if gInsertComma then
                    Print(",")
                end
                PrintNumber(gSampleBuffer.mVoltage[lIndex])
                gInsertComma = lUseCommas
            end
            if gStateVariables.Form_Elem_Sens1.CURR then
                if gInsertComma then
                    Print(",")
                end
                PrintNumber(gSampleBuffer.mCurrent[lIndex])
                gInsertComma = lUseCommas
            end
            if gStateVariables.Form_Elem_Sens1.RES then
                if gInsertComma then
                    Print(",")
                end
                PrintNumber(gSampleBuffer.mResistance[lIndex])
                gInsertComma = lUseCommas
            end
            if gStateVariables.Form_Elem_Sens1.TIME then
                if gInsertComma then
                    Print(",")
                end
                PrintNumber(gSampleBuffer.mTime[lIndex])
                gInsertComma = lUseCommas
            end
            if gStateVariables.Form_Elem_Sens1.STAT then
                if gInsertComma then
                    Print(",")
                end
                PrintNumber(gSampleBuffer.mStatus[lIndex])
                gInsertComma = lUseCommas
            end
        end
        
        --[[
            PrintSource2 prints Sour2(digio bit pattern)
            in the format specified by form:sour2 command
        --]]
        local PrintSource2 = function (lValue)
            if gStateVariables.Form_Sour2 == "ASC" then
                Print(tostring(lValue))
            elseif gStateVariables.Form_Sour2 == "BIN" then
                Print(ToBinary(lValue))
            elseif gStateVariables.Form_Sour2 == "HEX" then
                Print(string.format("#H%04X", lValue))
            elseif gStateVariables.Form_Sour2 == "OCT" then
                Print(string.format("#Q%06o", lValue))
            end
        end
        
        --[[
            PrintStatusRegister prints the status register bits
            in the format specified by form:sreg command
        --]]
        local PrintStatusRegister = function (lValue)
            if gStateVariables.Form_Sreg == "ASC" then
                Print(tostring(lValue))
            elseif gStateVariables.Form_Sreg == "BIN" then
                Print(ToBinary(lValue))
            elseif gStateVariables.Form_Sreg == "HEX" then
                Print(string.format("#H%04X", lValue))
            elseif gStateVariables.Form_Sreg == "OCT" then
                Print(string.format("#Q%06o", lValue))
            end
        end
        
        
        ------------------------------------------------------------------------------
        -- Buffer handler functions
        --[[
            These functions are used to save data in various buffers
        --]]
        ------------------------------------------------------------------------------
        
        --[[
            ClearBuffer clears a buffer by setting the buffer count to 0.
        --]]
        local ClearBuffer = function (lBuffer)
            lBuffer.mCount = 0
            if lBuffer == gTraceBuffer then
                -- clear Measurement Event Register Bit 9(8 on 2400), Buffer Available
                StatusModel.ClearCondition(measStatus, 9)
                -- clear Measurement Event Register Bit 10(9 on 2400), Buffer Full
                StatusModel.ClearCondition(measStatus, 10)
            elseif lBuffer == gCalculate2Buffer then
                gCalc2BufferIndex = 0
            elseif lBuffer == gCalculate1Buffer then
                gCalc1BufferIndex = 1
            end
        end
        
        --[[
            UpdateTraceBuffer updates the trace buffer when trace:feed:control is
            set to next
        --]]
        local UpdateTraceBuffer = function (itr)
            local i = gTraceBuffer.mCount + 1
        
            if gStateVariables.Trac_Feed == "SENS1" then
                gTraceBuffer.mVoltage[i] = gSampleBuffer.mVoltage[itr]
                gTraceBuffer.mCurrent[i] = gSampleBuffer.mCurrent[itr]
                gTraceBuffer.mResistance[i] = gSampleBuffer.mResistance[itr]
                gTraceBuffer.mTime[i] = gSampleBuffer.mTime[itr]
                gTraceBuffer.mStatus[i] = gSampleBuffer.mStatus[itr]
            elseif gStateVariables.Trac_Feed == "CALC1" then
                gTraceBuffer.mData[i] = gCalculate1Buffer.mData[itr]
                gTraceBuffer.mTime[i] = gCalculate1Buffer.mTime[itr]
                gTraceBuffer.mStatus[i] = gCalculate1Buffer.mStatus[itr]
            elseif gStateVariables.Trac_Feed == "CALC2" and (gCalculate2.mLimits or gCalculate2.mNullOffset) then
                gTraceBuffer.mData[i] = gCalculate2Buffer.mData[itr]
                gTraceBuffer.mTime[i] = gCalculate2Buffer.mTime[itr]
                gTraceBuffer.mStatus[i] = gCalculate2Buffer.mStatus[itr]
            end
            gTraceBuffer.mCount = i
            if i == 1 then
                -- Measurement Condition Register Bit 9(8 on 2400), Buffer Available
                StatusModel.SetCondition(measStatus, 9)
            end
            if gStateVariables.Trac_Cont == "NEXT" and i == gStateVariables.Trac_Poin then
                gStateVariables.Trac_Cont = "NEV"
                -- Measurement Condition Register Bit 10(9 on 2400), Buffer Full
                StatusModel.SetCondition(measStatus, 10)
            end
        end
        
        
        --[[
            UpdateSourceMemorySampleBuffer updates the Sample Buffer with data from source memory sweeps.
        --]]
        local UpdateSourceMemorySampleBuffer = function (lBufferIndex, lMemorySlot)
            -- when sourcing voltage
            if lMemorySlot.Sour_Func_Mode == gDCVOLTS then
                -- update voltage values
                if lMemorySlot.Sens_Func_Volt then
                    gSampleBuffer.mVoltage[lBufferIndex] = gSMVoltageBuffer[lBufferIndex]
                    -- stauts Bit 11, V-Meas; Bit 14, V-Sour
                    gStatusWord = gStatusWord + 18432
                else
                    gSampleBuffer.mVoltage[lBufferIndex] = gSMCurrentBuffer.sourcevalues[lBufferIndex]
                    -- stauts Bit 14, V-Sour
                    gStatusWord = gStatusWord + 16384
                end
        
                -- update current values
                if lMemorySlot.Sens_Func_Curr then
                    gSampleBuffer.mCurrent[lBufferIndex] = gSMCurrentBuffer[lBufferIndex]
                    -- stauts Bit 12, I-Meas
                    gStatusWord = gStatusWord + 4096
                elseif lMemorySlot.Sens_Func_Res then
                    gSampleBuffer.mCurrent[lBufferIndex] = gSMCurrentBuffer[lBufferIndex]
                else
                    gSampleBuffer.mCurrent[lBufferIndex] = gNan
                end
        
                -- update resistance values
                if lMemorySlot.Sens_Func_Res then
                    if gSampleBuffer.mCurrent[lBufferIndex] ~= 0 then
                        gSampleBuffer.mResistance[lBufferIndex] = gSampleBuffer.mVoltage[lBufferIndex]/gSampleBuffer.mCurrent[lBufferIndex]
                    else
                        gSampleBuffer.mResistance[lBufferIndex] = gNan
                    end
                    -- stauts Bit 13, R-Meas
                    gStatusWord = gStatusWord + 8192
                else
                    gSampleBuffer.mResistance[lBufferIndex] = gNan
                end
        
            -- when sourcing current
            else
                -- update current values
                if lMemorySlot.Sens_Func_Curr then
                    gSampleBuffer.mCurrent[lBufferIndex] = gSMCurrentBuffer[lBufferIndex]
                    -- stauts Bit 12, I-Meas;Bit 15, I-Sour
                    gStatusWord = gStatusWord + 36864
                else
                    gSampleBuffer.mCurrent[lBufferIndex] = gSMCurrentBuffer.sourcevalues[lBufferIndex]
                    -- stauts Bit 15, I-Sour
                    gStatusWord = gStatusWord + 32768
                end
        
                -- update voltage values
                if lMemorySlot.Sens_Func_Volt then
                    gSampleBuffer.mVoltage[lBufferIndex] = gSMVoltageBuffer[lBufferIndex]
                    -- stauts Bit 11, V-Meas
                    gStatusWord = gStatusWord + 2048
                elseif lMemorySlot.Sens_Func_Res then
                    gSampleBuffer.mVoltage[lBufferIndex] = gSMVoltageBuffer[lBufferIndex]
                else
                    gSampleBuffer.mVoltage[lBufferIndex] = gNan
                end
        
                -- update resistance values
                if lMemorySlot.Sens_Func_Res then
                    if gSampleBuffer.mCurrent[lBufferIndex] ~= 0 then
                        gSampleBuffer.mResistance[lBufferIndex] = gSampleBuffer.mVoltage[lBufferIndex]/gSampleBuffer.mCurrent[lBufferIndex]
                    else
                        gSampleBuffer.mResistance[lBufferIndex] = gNan
                    end
                    -- stauts Bit 13, R-Meas
                    gStatusWord = gStatusWord + 8192
                else
                    gSampleBuffer.mResistance[lBufferIndex] = gNan
                end
            end    
           
            if (lMemorySlot.Sens_Func_Volt and gSMVoltageBuffer[lBufferIndex] == gNan) 
            or (lMemorySlot.Sens_Func_Curr and gSMCurrentBuffer[lBufferIndex] == gNan)
            or (lMemorySlot.Sens_Func_Res and gSampleBuffer.mCurrent[lBufferIndex] == 0)then
                -- stauts Bit 0, OFLO
                gStatusWord = gStatusWord + 1
        
                -- Measurement Condition Register Bit 8(7 on 2400), Reading OverfLow
                StatusModel.SetCondition(measStatus, 8)                   
            end
        
            -- update timestamps
            -- When trace buffer is enabled system time auto reset has no effect it behaves
            -- as if auto reset is disabled
            if gStateVariables.Syst_Time_Res_Auto and gStateVariables.Trac_Cont ~= "NEXT" then
                gSampleBuffer.mTime[lBufferIndex] = gSMCurrentBuffer.timestamps[lBufferIndex]
            else
                gSampleBuffer.mTime[lBufferIndex] = gSMCurrentBuffer.basetimestamp - gSystemClockOffset + gSMCurrentBuffer.timestamps[lBufferIndex]
            end
        
            -- Update measurement status register bits
            -- Update other measurement related status word bits
            local lStatusValue = gSMCurrentBuffer.statuses[lBufferIndex]
        
            -- Measurement Condition Register Bit 7(6 on 2400), Reading Available
            StatusModel.SetCondition(measStatus, 7)
        
            -- Measurement Condition Register Bit 13(12 on 2400), Over Temperature
            if bit.test(lStatusValue, 2) then
                -- Measurement Event Register Bit 13(12 on 2400), Over Temperature
                StatusModel.SetCondition(measStatus, 13)
            end
        
            -- stauts Bit 3, Compliance
            if bit.test(lStatusValue, 7) then
                gStatusWord = gStatusWord + 8
                -- Measurement Condition Register Bit 15(14 on 2400), Compliance
                StatusModel.SetCondition(measStatus, 15)
            end
        
            -- stauts Bit 1, Filter
            if bit.test(lStatusValue, 8) then
                gStatusWord = gStatusWord + 2
            end
        
            -- stauts Bit 22, Remote Sense
            if bit.test(lStatusValue, 5) then
                gStatusWord = gStatusWord + 4194304
            end
        
            -- clear Measurement Condition Register Bit 7(6 on 2400), Reading Available
            StatusModel.ClearCondition(measStatus, 7)
        
            -- Update gSampleBuffer count
            if gArm.count ~= 0 then
                gSampleBuffer.mCount = lBufferIndex
            end
        end
        
        --[[
            UpdateSampleBuffer updates the Sample Buffer with data from regular sweeps.
        --]]
        local UpdateSampleBuffer = function (sampleItr)
            local lSenseFunc = gStateVariables.Sens_Func
        
            -- wait for the reading to be available in the buffer
            while not gMeasureCompleteTimer.wait(100e-3) do
                PriorityExecute()
                if gAbortExecuted then
                    --Return from ProcessData Abort command received
                    return
                end
            end
            -- when sourcing voltage
            if gStateVariables.Sour_Func_Mode == "VOLT" then
                -- update voltage values
                if lSenseFunc.VOLT then
                    gSampleBuffer.mVoltage[sampleItr] = gVoltageBuffer[sampleItr]
                    -- stauts Bit 11, V-Meas; Bit 14, V-Sour
                    gStatusWord = gStatusWord + 18432
                else
                    gSampleBuffer.mVoltage[sampleItr] = gCurrentBuffer.sourcevalues[sampleItr]
                    -- stauts Bit 14, V-Sour
                    gStatusWord = gStatusWord + 16384
                end
        
                -- update current values
                if lSenseFunc.CURR then
                    gSampleBuffer.mCurrent[sampleItr] = gCurrentBuffer[sampleItr]
                    -- stauts Bit 12, I-Meas
                    gStatusWord = gStatusWord + 4096
                elseif lSenseFunc.RES then
                    gSampleBuffer.mCurrent[sampleItr] = gCurrentBuffer[sampleItr]
                else
                    gSampleBuffer.mCurrent[sampleItr] = gNan
                end
        
                -- update resistance values
                if lSenseFunc.RES then
                    if gSampleBuffer.mCurrent[sampleItr] ~= 0 then
                        gSampleBuffer.mResistance[sampleItr] = gSampleBuffer.mVoltage[sampleItr]/gSampleBuffer.mCurrent[sampleItr]
                    else
                        gSampleBuffer.mResistance[sampleItr] = gNan
                    end
                    -- stauts Bit 13, R-Meas
                    gStatusWord = gStatusWord + 8192
                else
                    gSampleBuffer.mResistance[sampleItr] = gNan
                end
        
            -- when sourcing current
            else
                -- update current values
                if lSenseFunc.CURR then
                    gSampleBuffer.mCurrent[sampleItr] = gCurrentBuffer[sampleItr]
                    -- stauts Bit 12, I-Meas; Bit 15, I-Sour
                    gStatusWord = gStatusWord + 36864
                else
                    gSampleBuffer.mCurrent[sampleItr] = gCurrentBuffer.sourcevalues[sampleItr]
                    -- stauts Bit 15, I-Sour
                    gStatusWord = gStatusWord + 32768
                end
        
                -- update voltage values
                if lSenseFunc.VOLT then
                    gSampleBuffer.mVoltage[sampleItr] = gVoltageBuffer[sampleItr]
                    -- stauts Bit 11, V-Meas
                    gStatusWord = gStatusWord + 2048
                elseif lSenseFunc.RES then
                    gSampleBuffer.mVoltage[sampleItr] = gVoltageBuffer[sampleItr]
                else
                    gSampleBuffer.mVoltage[sampleItr] = gNan
                end
        
                -- update resistance values
                if lSenseFunc.RES then
                    if gSampleBuffer.mCurrent[sampleItr] ~= 0 then
                        gSampleBuffer.mResistance[sampleItr] = gSampleBuffer.mVoltage[sampleItr]/gSampleBuffer.mCurrent[sampleItr]
                    else
                        gSampleBuffer.mResistance[sampleItr] = gNan
                    end
                    -- stauts Bit 13, R-Meas
                    gStatusWord = gStatusWord + 8192
                else
                    gSampleBuffer.mResistance[sampleItr] = gNan
                end
            end
        
            -- If any of the sense functions are turned on look for overflow condition
            --if lSenseFunc.ANY then
                if (lSenseFunc.VOLT and gVoltageBuffer[sampleItr] == gNan) 
                or (lSenseFunc.CURR and gCurrentBuffer[sampleItr] == gNan)
                or (lSenseFunc.RES and gSampleBuffer.mCurrent[sampleItr] == 0) then
                    -- stauts Bit 0, OFLO
                    gStatusWord = gStatusWord + 1
                    -- Measurement Condition Register Bit 8(7 on 2400), Reading OverfLow
                    StatusModel.SetCondition(measStatus, 8)                   
                end
        
            -- update timestamps
            -- When trace buffer is enabled system time auto reset has no effect it behaves
            -- as if auto reset is disabled
            if gStateVariables.Syst_Time_Res_Auto and gStateVariables.Trac_Cont ~= "NEXT" then
                gSampleBuffer.mTime[sampleItr] = gCurrentBuffer.timestamps[sampleItr]
            else
                gSampleBuffer.mTime[sampleItr] = gCurrentBuffer.basetimestamp - gSystemClockOffset + gCurrentBuffer.timestamps[sampleItr]
            end
        
            -- Update measurement status register bits
            -- Update other measurement related status word bits
            local lStatusValue = gCurrentBuffer.statuses[sampleItr]
        
            -- Measurement Event Register Bit 7(6 on 2400), Reading Available
            StatusModel.SetEvent(measStatus, 7)
        
            -- Measurement Condition Register Bit 13(12 on 2400), Over Temperature
            if bit.test(lStatusValue, 2) then
                StatusModel.SetCondition(measStatus, 13)
            end
        
            if bit.test(lStatusValue, 7) then
                -- stauts Bit 3, Compliance
                gStatusWord = gStatusWord + 8
        
                -- Measurement Condition Register Bit 15(14 on 2400), Compliance
                StatusModel.SetCondition(measStatus, 15)
            end
        
            -- stauts Bit 1, Filter
            if bit.test(lStatusValue, 8) then
                gStatusWord = gStatusWord + 2
            end
        
            -- status Bit 22, Remote Sense
            if bit.test(lStatusValue, 5) then
                gStatusWord = gStatusWord + 4194304
            end
        
            -- Update gSampleBuffer count
            if gArm.count ~= 0 then
                gSampleBuffer.mCount = gSampleBuffer.mCount + 1
            end
        end
        
        --[[
            UpdateIntermediateSampleBuffer updates the gIntermediateSampleBuffer with data
            to be used by math equations
        --]]
        local UpdateIntermediateSampleBuffer = function(lBufferLocation)
            local lIndex = gIntermediateSampleBuffer.mCount + 1
        
            gIntermediateSampleBuffer.mCount = lIndex
            gIntermediateSampleBuffer.mVoltage[lIndex] = gSampleBuffer.mVoltage[lBufferLocation]
            gIntermediateSampleBuffer.mCurrent[lIndex] = gSampleBuffer.mCurrent[lBufferLocation]
            gIntermediateSampleBuffer.mResistance[lIndex] = gSampleBuffer.mResistance[lBufferLocation]
            gIntermediateSampleBuffer.mTime[lIndex] = gSampleBuffer.mTime[lBufferLocation]
            gIntermediateSampleBuffer.mStatus[lIndex] = gSampleBuffer.mStatus[lBufferLocation]
        end
        
        --[[
            UpdateCalc2Buffer updates the gCalculate2Buffer with the limit test or nulloffset data
            this function is called when running regular sweeps.
        --]]
        local UpdateCalc2Buffer = function (i)
        
            if gStateVariables.Calc2_Feed == "CURR" then
                if gSampleBuffer.mCurrent[i] == gNan then
                   gCalculate2Buffer.mData[i] = gNan
                else
                    if gStateVariables.Calc2_Null_Stat then
                      gCalculate2Buffer.mData[i] = gSampleBuffer.mCurrent[i] - gStateVariables.Calc2_Null_Offs
                    else
                      gCalculate2Buffer.mData[i] = gSampleBuffer.mCurrent[i]
                    end
                end
            elseif gStateVariables.Calc2_Feed == "VOLT" then
                if gSampleBuffer.mVoltage[i] == gNan then
                    gCalculate2Buffer.mData[i] = gNan
                else
                    if gStateVariables.Calc2_Null_Stat then
                        gCalculate2Buffer.mData[i] = gSampleBuffer.mVoltage[i] - gStateVariables.Calc2_Null_Offs
                    else
                        gCalculate2Buffer.mData[i] = gSampleBuffer.mVoltage[i]
                    end
                end
            elseif gStateVariables.Calc2_Feed == "RES" then
                if gSampleBuffer.mResistance[i] == gNan then
                    gCalculate2Buffer.mData[i] = gNan
                else
                    if gStateVariables.Calc2_Null_Stat then
                        gCalculate2Buffer.mData[i] = gSampleBuffer.mResistance[i] - gStateVariables.Calc2_Null_Offs
                    else
                        gCalculate2Buffer.mData[i] = gSampleBuffer.mResistance[i]
                    end
                end
            elseif gStateVariables.Calc2_Feed == "CALC1" then
                if gStateVariables.Calc2_Null_Stat then
                    gCalculate2Buffer.mData[i] = gCalculate1Buffer.mData[i] - gStateVariables.Calc2_Null_Offs
                else
                    gCalculate2Buffer.mData[i] = gCalculate1Buffer.mData[i]
                end
            end
        
            gCalculate2Buffer.mTime[i] = gSampleBuffer.mTime[i]
        
            if gArm.count ~= 0 then
                gCalculate2Buffer.mCount = gCalculate2Buffer.mCount + 1
            end
        end
        
        --[[
            UpdateSourceMemoryCalc2Buffer updates the gCalculate2Buffer with the limit test or nulloffset data
            this function is called when running sourcememroy sweeps.
        --]]
        local UpdateSourceMemoryCalc2Buffer = function (lMemorySlot, lBufferIndex)
            gCalc2BufferIndex = gCalc2BufferIndex + 1
            local i = gCalc2BufferIndex
            if lMemorySlot.Calc2_Feed == "CURR" then
                if gSampleBuffer.mCurrent[lBufferIndex] == gNan then
                    gCalculate2Buffer.mData[i] = gNan
                else
                    if lMemorySlot.Calc2_Null_Stat then
                        gCalculate2Buffer.mData[i] = gSampleBuffer.mCurrent[lBufferIndex] - lMemorySlot.Calc2_Null_Offs
                    else
                        gCalculate2Buffer.mData[i] = gSampleBuffer.mCurrent[lBufferIndex]
                    end
                end
            elseif lMemorySlot.Calc2_Feed == "VOLT" then
                if gSampleBuffer.mVoltage[lBufferIndex] == gNan then
                    gCalculate2Buffer.mData[i] = gNan
                else
                    if lMemorySlot.Calc2_Null_Stat then
                        gCalculate2Buffer.mData[i] = gSampleBuffer.mVoltage[lBufferIndex] - lMemorySlot.Calc2_Null_Offs
                    else
                        gCalculate2Buffer.mData[i] = gSampleBuffer.mVoltage[lBufferIndex]
                    end
                end
            elseif lMemorySlot.Calc2_Feed == "RES" then
            if gSampleBuffer.mResistance[lBufferIndex] == gNan then
                   gCalculate2Buffer.mData[i] = gNan
                else
                    if lMemorySlot.Calc2_Null_Stat then
                        gCalculate2Buffer.mData[i] = gSampleBuffer.mResistance[lBufferIndex] - lMemorySlot.Calc2_Null_Offs
                    else
                        gCalculate2Buffer.mData[i] = gSampleBuffer.mResistance[lBufferIndex]
                    end
                end
            elseif lMemorySlot.Calc2_Feed == "CALC1" then
                if lMemorySlot.Calc2_Null_Stat then
                    gCalculate2Buffer.mData[i] = gCalculate1Buffer.mData[gCalc1BufferIndex] - gStateVariables.Calc2_Null_Offs
                else
                    gCalculate2Buffer.mData[i] = gCalculate1Buffer.mData[gCalc1BufferIndex]
                end
            end
        
            gCalculate2Buffer.mTime[i] = gSampleBuffer.mTime[lBufferIndex]
        
            if gArm.count ~= 0 then
                gCalculate2Buffer.mCount = gCalculate2Buffer.mCount + 1
            end
        end
        
        
        ------------------------------------------------------------------------------
        -- Digio, Tlink handler functions
        --[[
            These functions handle various Digio and Tlink operations
            -- DIGIO Pin Assignment
            DIGIO 1 -> TLink1
            DIGIO 2 -> TLink2
            DIGIO 3 -> TLink3
            DIGIO 4 -> TLink4
            DIGIO 5 -> DigOut1
            DIGIO 6 -> DigOut2
            DIGIO 7 -> DigOut3
            DIGIO 8 -> DigOut4 (or EOT, /EOT, BUSY, /BUSY)
            DIGIO 9 -> SOT
            DIGIO 10 -> Not used
            DIGIO 11 -> Not used
            DIGIO 12 -> Not used
            DIGIO 13 -> Not used
            DIGIO 14 -> Not used
        --]]
        -----------------------------------------------------------------------------
        
        local gDigitalOut1Line = 5
        local gDigitalOut4Line = 8
        local gEndOfTest
        local gStartOfTest 
        
        if gDigioSupport then
            gEndOfTest = gTriggerLines[gDigitalOut4Line]
            gStartOfTest = gTriggerLines[9]
        end
        
        --[[
            UpdatePin4 updates Digoutput pin 4 EOT/BUSY pin
        --]]
        local UpdatePin4 = function ()
            if gStateVariables.Sour2_Ttl4_Mode == "EOT" then
                if gStateVariables.Sour2_Bsize == 3 then
                    gEndOfTest.mode = 0
                    if gStateVariables.Sour2_Ttl4_Bst then
                        digio.writebit(gDigitalOut4Line, 0)
                    else
                        digio.writebit(gDigitalOut4Line, 1)
                    end
                end
            else -- "BUSY"
                gEndOfTest.pulsewidth = 0
                if gStateVariables.Sour2_Ttl4_Bst then
                    gEndOfTest.mode = 8
                else
                    gEndOfTest.mode = 1
                end
            end
        end
        
        --[[
            UpdateDigOut updates Digital outputs
        --]]
        local UpdateDigOut
        
        if gDigioSupport then
            UpdateDigOut = function (lLevel)
                local lCount = gStateVariables.Sour2_Bsize
        
                if lCount == 4 then
                    if gStateVariables.Sour2_Ttl4_Mode == "EOT" then
                        gEndOfTest.mode = 0
                    else -- "BUSY"
                        -- only update first three Digital outputs DIGIO 5-7
                        lCount = 3
                    end
                end
                gStateVariables.Sour2_Ttl_Act = lLevel
                for lIndex = 1, lCount do
                    digio.writebit(gDigitalOut1Line - 1 + lIndex, bit.test(lLevel, lIndex) and 1 or 0)
                end
            end
        else
            UpdateDigOut = NullFunction
        end
        
        --[[
            CheckForTlinkConflict checks for conflicts in trigger link line configuration
            returns true if a conflict exist else returns false
        --]]
        local CheckForTlinkConflict = function ()
            local lTriggerLinkConflict = false
            
            if gStateVariables.Trig_Outp.SOUR or gStateVariables.Trig_Outp.DEL
                    or gStateVariables.Trig_Outp.SENS then
                if gStateVariables.Trig_Sour == "TLIN" then
                    if gStateVariables.Trig_Inp == "SOUR" or
                            gStateVariables.Trig_Inp == "SENS" or
                            gStateVariables.Trig_Inp == "DEL" then
                        if gStateVariables.Trig_Ilin == gStateVariables.Trig_Olin then
                            lTriggerLinkConflict = true
                        end
                    end
                elseif gStateVariables.Arm_Sour == "TLIN" then
                    if gStateVariables.Arm_Ilin == gStateVariables.Trig_Olin then
                        lTriggerLinkConflict = true
                    end
                end
            elseif gStateVariables.Arm_Outp.TEX or gStateVariables.Arm_Outp.TENT then
                if gStateVariables.Trig_Sour == "TLIN" then
                    if gStateVariables.Trig_Inp == "SOUR" or
                    gStateVariables.Trig_Inp == "SENS" or
                    gStateVariables.Trig_Inp == "DEL" then
                        if gStateVariables.Arm_Olin == gStateVariables.Trig_Ilin then
                            lTriggerLinkConflict = true
                        end
                    end
                elseif gStateVariables.Arm_Sour == "TLIN" then
                    if gStateVariables.Arm_Ilin == gStateVariables.Arm_Olin then
                        lTriggerLinkConflict = true
                    end
                end
            elseif gStateVariables.Trig_Sour == "TLIN" and
             (gStateVariables.Trig_Inp == "SOUR" or
             gStateVariables.Trig_Inp == "SENS" or
             gStateVariables.Trig_Inp == "DEL") and
             gStateVariables.Arm_Sour == "TLIN" then
                if gStateVariables.Arm_Ilin == gStateVariables.Trig_Ilin then
                    lTriggerLinkConflict = true
                end
            end
            return lTriggerLinkConflict
        end
        
        --[[
            UpdateEOT updates DIGIO - 4 to signal end of test
            Busy signal operation is directly handled by digio triggering in the sweeps
        --]]
        local UpdateEOT
        
        if gDigioSupport then
            UpdateEOT = function ()
                if gStateVariables.Sour2_Cle_Auto then
                    if gStateVariables.Sour2_Ttl4_Mode == "EOT" then
                        if gStateVariables.Sour2_Bsize == 3 then
                            gEndOfTest.pulsewidth = gStateVariables.Sour2_Cle_Del
                            if gStateVariables.Sour2_Ttl4_Bst then
                                gEndOfTest.mode = 8
                                gEndOfTest.assert()
                             else
                                gEndOfTest.mode = 1
                                gEndOfTest.assert()
                            end
                        end
                    end
                    delay(gStateVariables.Sour2_Cle_Del)
                    UpdateDigOut(gStateVariables.Sour2_Ttl_Lev)
                end
            end
        else
            UpdateEOT = NullFunction
        end
        
        --[[
            updates the Digio output pattern and Eot lines when in
            Grading mode End bining control
        --]]
        local UpdateGradingEndBinnig = function ()
            if gLimitCapture.mFirstFailureTest == 0 then
                -- Measurement Condition Register Bit 6(5 on 2400), Limits Pass
                StatusModel.SetCondition(measStatus, 6)
                UpdateDigOut(gStateVariables.Calc2_Clim_Pass_Sour2)
            else
                if gLimitCapture.mFirstFailureTest == "Comp" then
                    UpdateDigOut(gStateVariables.Calc2_Lim1_Sour2)
                else
                    if gLimitCapture.mFirstFailureLimit == "Upper" then
                        UpdateDigOut(gStateVariables.Calc2_Lim_Upp_Sour2[gLimitCapture.mFirstFailureTest])
                    elseif gLimitCapture.mFirstFailureLimit == "Lower" then
                        UpdateDigOut(gStateVariables.Calc2_Lim_Low_Sour2[gLimitCapture.mFirstFailureTest])
                    end
                end
            end
            UpdateEOT()
        end
        
        --[[
            updates the Digio output pattern and Eot lines when in
            Grading mode End bining control for sourcememory sweeps
        --]]
        local UpdateSourceMemorySweepGradingEndBinnig = function (lGradeMemorySlot)
            local lFailedMemorySlot = gMemLoc[gLimitCapture.mFailedMemoryLocation]
        
            -- Measurement Condition Register Bit 6(5 on 2400), Limits Pass
            StatusModel.SetCondition(measStatus, 6)
            -- Passed
            if gLimitCapture.mFirstFailureTest == 0 then
                UpdateDigOut(lGradeMemorySlot.Calc2_Clim_Pass_Sour2)
            else
                if gLimitCapture.mFirstFailureTest == "Comp" then
                    UpdateDigOut(lFailedMemorySlot.Calc2_Lim1_Sour2)
                else
                    if gLimitCapture.mFirstFailureLimit == "Upper" then
                        local digioPattern
                        if gLimitCapture.mFirstFailureTest == 2 then
                            digioPattern = lFailedMemorySlot.Calc2_Lim2_Upp_Sour2
                        elseif gLimitCapture.mFirstFailureTest == 3 then
                            digioPattern = lFailedMemorySlot.Calc2_Lim3_Upp_Sour2
                        elseif gLimitCapture.mFirstFailureTest == 5 then
                            digioPattern = lFailedMemorySlot.Calc2_Lim5_Upp_Sour2
                        elseif gLimitCapture.mFirstFailureTest == 6 then
                            digioPattern = lFailedMemorySlot.Calc2_Lim6_Upp_Sour2
                        elseif gLimitCapture.mFirstFailureTest == 7 then
                            digioPattern = lFailedMemorySlot.Calc2_Lim7_Upp_Sour2
                        elseif gLimitCapture.mFirstFailureTest == 8 then
                            digioPattern = lFailedMemorySlot.Calc2_Lim8_Upp_Sour2
                        elseif gLimitCapture.mFirstFailureTest == 9 then
                            digioPattern = lFailedMemorySlot.Calc2_Lim9_Upp_Sour2
                        elseif gLimitCapture.mFirstFailureTest == 10 then
                            digioPattern = lFailedMemorySlot.Calc2_Lim10_Upp_Sour2
                        elseif gLimitCapture.mFirstFailureTest == 11 then
                            digioPattern = lFailedMemorySlot.Calc2_Lim11_Upp_Sour2
                        elseif gLimitCapture.mFirstFailureTest == 12 then
                            digioPattern = lFailedMemorySlot.Calc2_Lim12_Upp_Sour2
                        end
                        UpdateDigOut(digioPattern)
                    elseif gLimitCapture.mFirstFailureLimit == "Lower" then
                        local digioPattern
                        if gLimitCapture.mFirstFailureTest == 2 then
                            digioPattern = lFailedMemorySlot.Calc2_Lim2_Low_Sour2
                        elseif gLimitCapture.mFirstFailureTest == 3 then
                            digioPattern = lFailedMemorySlot.Calc2_Lim3_Low_Sour2
                        elseif gLimitCapture.mFirstFailureTest == 5 then
                            digioPattern = lFailedMemorySlot.Calc2_Lim5_Low_Sour2
                        elseif gLimitCapture.mFirstFailureTest == 6 then
                            digioPattern = lFailedMemorySlot.Calc2_Lim6_Low_Sour2
                        elseif gLimitCapture.mFirstFailureTest == 7 then
                            digioPattern = lFailedMemorySlot.Calc2_Lim7_Low_Sour2
                        elseif gLimitCapture.mFirstFailureTest == 8 then
                            digioPattern = lFailedMemorySlot.Calc2_Lim8_Low_Sour2
                        elseif gLimitCapture.mFirstFailureTest == 9 then
                            digioPattern = lFailedMemorySlot.Calc2_Lim9_Low_Sour2
                        elseif gLimitCapture.mFirstFailureTest == 10 then
                            digioPattern = lFailedMemorySlot.Calc2_Lim10_Low_Sour2
                        elseif gLimitCapture.mFirstFailureTest == 11 then
                            digioPattern = lFailedMemorySlot.Calc2_Lim11_Low_Sour2
                        elseif gLimitCapture.mFirstFailureTest == 12 then
                            digioPattern = lFailedMemorySlot.Calc2_Lim12_Low_Sour2
                        end
                        UpdateDigOut(digioPattern)
                    end
                end
            end
            UpdateEOT()
        end
        
        --[[
            UpdateCalc2Source2 updates the CALC2:LIMX:SOUR2 output patterns when BSIZE is Changed
        --]]
        local UpdateCalc2Source2 = function ()
            local maxBsize = gStateVariables.Sour2_Bsize_MaxValue
            
            if gStateVariables.Calc2_Lim1_Sour2 > maxBsize then
                gStateVariables.Calc2_Lim1_Sour2 = maxBsize
            end
            if gStateVariables.Calc2_Clim_Pass_Sour2 > maxBsize then
                gStateVariables.Calc2_Clim_Pass_Sour2 = maxBsize
            end
            if gStateVariables.Calc2_Clim_Fail_Sour2 > maxBsize then
                gStateVariables.Calc2_Clim_Fail_Sour2 = maxBsize
            end
        
            for i = 2, 12 do
                if i ~= 4 then
                    if gStateVariables.Calc2_Lim_Upp_Sour2[i] > maxBsize then
                        gStateVariables.Calc2_Lim_Upp_Sour2[i] = maxBsize
                    end
                    if gStateVariables.Calc2_Lim_Low_Sour2[i] > maxBsize then
                        gStateVariables.Calc2_Lim_Low_Sour2[i] = maxBsize
                    end
                    if gStateVariables.Calc2_Lim_Pass_Sour2[i] > maxBsize then
                        gStateVariables.Calc2_Lim_Pass_Sour2[i] = maxBsize
                    end
                end
            end
        
            lMemScratch.Calc2_Lim1_Sour2 = gStateVariables.Calc2_Lim1_Sour2
            lMemScratch.Calc2_Lim2_Upp_Sour2 = gStateVariables.Calc2_Lim_Upp_Sour2[2]
            lMemScratch.Calc2_Lim2_Low_Sour2 = gStateVariables.Calc2_Lim_Low_Sour2[2]
            lMemScratch.Calc2_Lim2_Pass_Sour2 = gStateVariables.Calc2_Lim_Pass_Sour2[2]
            lMemScratch.Calc2_Lim3_Upp_Sour2 = gStateVariables.Calc2_Lim_Upp_Sour2[3]
            lMemScratch.Calc2_Lim3_Low_Sour2 = gStateVariables.Calc2_Lim_Low_Sour2[3]
            lMemScratch.Calc2_Lim3_Pass_Sour2 = gStateVariables.Calc2_Lim_Pass_Sour2[3]
            lMemScratch.Calc2_Lim5_Upp_Sour2 = gStateVariables.Calc2_Lim_Upp_Sour2[5]
            lMemScratch.Calc2_Lim5_Low_Sour2 = gStateVariables.Calc2_Lim_Low_Sour2[5]
            lMemScratch.Calc2_Lim5_Pass_Sour2 = gStateVariables.Calc2_Lim_Pass_Sour2[5]
            lMemScratch.Calc2_Lim6_Upp_Sour2 = gStateVariables.Calc2_Lim_Upp_Sour2[6]
            lMemScratch.Calc2_Lim6_Low_Sour2 = gStateVariables.Calc2_Lim_Low_Sour2[6]
            lMemScratch.Calc2_Lim6_Pass_Sour2 = gStateVariables.Calc2_Lim_Pass_Sour2[6]
            lMemScratch.Calc2_Lim7_Upp_Sour2 = gStateVariables.Calc2_Lim_Upp_Sour2[7]
            lMemScratch.Calc2_Lim7_Low_Sour2 = gStateVariables.Calc2_Lim_Low_Sour2[7]
            lMemScratch.Calc2_Lim7_Pass_Sour2 = gStateVariables.Calc2_Lim_Pass_Sour2[7]
            lMemScratch.Calc2_Lim8_Upp_Sour2 = gStateVariables.Calc2_Lim_Upp_Sour2[8]
            lMemScratch.Calc2_Lim8_Low_Sour2 = gStateVariables.Calc2_Lim_Low_Sour2[8]
            lMemScratch.Calc2_Lim8_Pass_Sour2 = gStateVariables.Calc2_Lim_Pass_Sour2[8]
            lMemScratch.Calc2_Lim9_Upp_Sour2 = gStateVariables.Calc2_Lim_Upp_Sour2[9]
            lMemScratch.Calc2_Lim9_Low_Sour2 = gStateVariables.Calc2_Lim_Low_Sour2[9]
            lMemScratch.Calc2_Lim9_Pass_Sour2 = gStateVariables.Calc2_Lim_Pass_Sour2[9]
            lMemScratch.Calc2_Lim10_Upp_Sour2 = gStateVariables.Calc2_Lim_Upp_Sour2[10]
            lMemScratch.Calc2_Lim10_Low_Sour2 = gStateVariables.Calc2_Lim_Low_Sour2[10]
            lMemScratch.Calc2_Lim10_Pass_Sour2 = gStateVariables.Calc2_Lim_Pass_Sour2[10]
            lMemScratch.Calc2_Lim11_Upp_Sour2 = gStateVariables.Calc2_Lim_Upp_Sour2[11]
            lMemScratch.Calc2_Lim11_Low_Sour2 = gStateVariables.Calc2_Lim_Low_Sour2[11]
            lMemScratch.Calc2_Lim11_Pass_Sour2 = gStateVariables.Calc2_Lim_Pass_Sour2[11]
            lMemScratch.Calc2_Lim12_Upp_Sour2 = gStateVariables.Calc2_Lim_Upp_Sour2[12]
            lMemScratch.Calc2_Lim12_Low_Sour2 = gStateVariables.Calc2_Lim_Low_Sour2[12]
            lMemScratch.Calc2_Lim12_Pass_Sour2 = gStateVariables.Calc2_Lim_Pass_Sour2[12]
            lMemScratch.Calc2_Clim_Pass_Sour2 = gStateVariables.Calc2_Clim_Pass_Sour2
            lMemScratch.Calc2_Clim_Fail_Sour2 = gStateVariables.Calc2_Clim_Fail_Sour2
        end
        
        ------------------------------------------------------------------------------
        -- Limit test support functions
        --[[
            These functions are used to perform limit testing
        --]]
        -----------------------------------------------------------------------------
        
        --[[
            TestSourceMemoryCalc2Limits performs Limit testing for sourcememory sweeps
            x is the limit being tested.
            This algorithm needs lowerLimit and upperLimit parameters
            as they cannot be indexed in source memory sweep as in regular sweeps.
            Also registers upper or lower limit failure
        --]]
        local TestSourceMemoryCalc2Limits = function (x, lowerLimit, upperLimit, lcalc2BufferIndex, lMemoryLocation)
            local lMemorySlot = gMemLoc[lMemoryLocation]
        
            gLimitCapture.mFailedLimit = 0
            if lMemorySlot.Calc2_Feed == "CALC1" then
                if lMemorySlot.Calc1_Stat then
                else
                    gStateVariables.Calc2_Lim_Result[x] = 0
                end
            else
                if gCalculate2Buffer.mData[lcalc2BufferIndex] > upperLimit then
                    gStateVariables.Calc2_Lim_Result[x] = 1
                    gLimitCapture.mFailedLimit = "Upper"
                    if gLimitCapture.mFirstFailureTest == 0 then
                        gLimitCapture.mFirstFailureTest = x
                        gLimitCapture.mFirstFailureLimit = "Upper"
                        gLimitCapture.mFailedMemoryLocation = lMemoryLocation
                    end
                elseif gCalculate2Buffer.mData[lcalc2BufferIndex] < lowerLimit then
                    gStateVariables.Calc2_Lim_Result[x] = 1
                    gLimitCapture.mFailedLimit = "Lower"
                    if gLimitCapture.mFirstFailureTest == 0 then
                        gLimitCapture.mFirstFailureTest = x
                        gLimitCapture.mFirstFailureLimit = "Lower"
                        gLimitCapture.mFailedMemoryLocation = lMemoryLocation
                    end
                else
                    gStateVariables.Calc2_Lim_Result[x] = 0
                    gLimitCapture.mFailedLimit = 0
                end
            end
        end
        
        --[[
            TestCalc2Limits Perform Limit Testing for regular sweeps.
             x is the limit being tested.
        --]]
        local TestCalc2Limits = function (x, i)
            gLimitCapture.mFailedLimit = 0
            if gCalculate2Buffer.mData[i] > gStateVariables.Calc2_Lim_Upp[x] then
                gStateVariables.Calc2_Lim_Result[x] = 1
                gLimitCapture.mFailedLimit = "Upper"
                if gLimitCapture.mFirstFailureTest == 0 then
                    gLimitCapture.mFirstFailureTest = x
                    gLimitCapture.mFirstFailureLimit = "Upper"
                end
            elseif gCalculate2Buffer.mData[i] < gStateVariables.Calc2_Lim_Low[x] then
                gStateVariables.Calc2_Lim_Result[x] = 1
                gLimitCapture.mFailedLimit = "Lower"
                if gLimitCapture.mFirstFailureTest == 0 then
                    gLimitCapture.mFirstFailureTest = x
                    gLimitCapture.mFirstFailureLimit = "Lower"
                end
            else
                gStateVariables.Calc2_Lim_Result[x] = 0
                gLimitCapture.mFailedLimit = 0
            end
        end
        ------------------------------------------------------------------------------
        -- Source Memory sweeps related functions
        --[[
            runs source memory sweeps, loads sourcememory locations, saves and recalls
            source memory locations, process data for limit testing.
        --]]
        -----------------------------------------------------------------------------
        
        local ProcessSourceMemoryCalc2Data = function (lcalc2BufferIndex, lMemoryLocation, lBufferIndex)
            local lMemorySlot = gMemLoc[lMemoryLocation]
            -- when 1 in sorting mode terminate the current test
            local lDutSorted = 0
            local lDutGraded = 0
            local lNextMemoryLocation = 0
        
            gProcessedAtleastOneLimit = true
            -- Reset all the results for the new test
            gStateVariables.Calc2_Lim1_Result = 0
            for x = 2, 12 do
                -- 4 is not used but it is cheaper to just set it to 0
                gStateVariables.Calc2_Lim_Result[x] = 0
            end
        
            -- Sorting mode
            if gStateVariables.Calc2_Clim_Mode == "SORT" then
                if lMemorySlot.Calc2_Lim1_Stat then
                    gLimitCapture.mFailedLimit = 0
                    if (bit.bitand(gSMCurrentBuffer.statuses[lBufferIndex], 64) == 64 and lMemorySlot.Calc2_Lim1_Fail == "IN") or
                            (bit.bitand(gSMCurrentBuffer.statuses[lBufferIndex], 64) ~= 64 and lMemorySlot.Calc2_Lim1_Fail == "OUT") then
                        gStateVariables.Calc2_Lim1_Result = 1
                        -- Measurement Condition Register Bit 1(0 on 2400), Limit1 Fail
                        StatusModel.SetCondition(measStatus, 1)
                        UpdateDigOut(lMemorySlot.Calc2_Lim1_Sour2)
                        UpdateEOT()
                        lDutSorted = 1
                        -- stauts Bit 8, Limit Results
                        gStatusWord = gStatusWord + 256
                        lNextMemoryLocation = lMemorySlot.Calc2_Clim_Fail_Sml
                    else
                        lDutSorted = 2
                    end
                end
                if lMemorySlot.Calc2_Lim2_Stat and lDutSorted ~= 1 then
                    TestSourceMemoryCalc2Limits(2, lMemorySlot.Calc2_Lim2_Low, lMemorySlot.Calc2_Lim2_Upp, lcalc2BufferIndex, lMemoryLocation, lBufferIndex)
                    if gStateVariables.Calc2_Lim_Result[2] == 0 then
                        UpdateDigOut(lMemorySlot.Calc2_Lim2_Pass_Sour2)
                        UpdateEOT()
                        lDutSorted = 1
                        -- stauts Bit 9, Limit Results
                        gStatusWord = gStatusWord + 512
                        lNextMemoryLocation = lMemorySlot.Calc2_Clim_Fail_Sml
                    end
                end
                if lMemorySlot.Calc2_Lim3_Stat and lDutSorted ~= 1 then
                    TestSourceMemoryCalc2Limits(3, lMemorySlot.Calc2_Lim3_Low, lMemorySlot.Calc2_Lim3_Upp, lcalc2BufferIndex, lMemoryLocation, lBufferIndex)
                    if gStateVariables.Calc2_Lim_Result[3] == 0 then
                        UpdateDigOut(lMemorySlot.Calc2_Lim3_Pass_Sour2)
                        UpdateEOT()
                        lDutSorted = 1
                        -- stauts Bit 8,9, Limit Results
                        gStatusWord = gStatusWord + 768
                        lNextMemoryLocation = lMemorySlot.Calc2_Clim_Fail_Sml
                    end
                end
                if lMemorySlot.Calc2_Lim5_Stat and lDutSorted ~= 1 then
                    TestSourceMemoryCalc2Limits(5, lMemorySlot.Calc2_Lim5_Low, lMemorySlot.Calc2_Lim5_Upp, lcalc2BufferIndex, lMemoryLocation, lBufferIndex)
                    if gStateVariables.Calc2_Lim_Result[5] == 0 then
                        UpdateDigOut(lMemorySlot.Calc2_Lim5_Pass_Sour2)
                        UpdateEOT()
                        lDutSorted = 1
                        -- stauts Bit 19, Limit Results
                        gStatusWord = gStatusWord + 524288
                        lNextMemoryLocation = lMemorySlot.Calc2_Clim_Fail_Sml
                    end
                end
                if lMemorySlot.Calc2_Lim6_Stat and lDutSorted ~= 1 then
                    TestSourceMemoryCalc2Limits(6, lMemorySlot.Calc2_Lim6_Low, lMemorySlot.Calc2_Lim6_Upp, lcalc2BufferIndex, lMemoryLocation, lBufferIndex)
                    if gStateVariables.Calc2_Lim_Result[6] == 0 then
                        UpdateDigOut(lMemorySlot.Calc2_Lim6_Pass_Sour2)
                        UpdateEOT()
                        lDutSorted = 1
                        -- stauts Bit 9,19, Limit Results
                        gStatusWord = gStatusWord + 524800
                        lNextMemoryLocation = lMemorySlot.Calc2_Clim_Fail_Sml
                    end
                end
                if lMemorySlot.Calc2_Lim7_Stat and lDutSorted ~= 1 then
                    TestSourceMemoryCalc2Limits(7, lMemorySlot.Calc2_Lim7_Low, lMemorySlot.Calc2_Lim7_Upp, lcalc2BufferIndex, lMemoryLocation, lBufferIndex)
                    if gStateVariables.Calc2_Lim_Result[7] == 0 then
                        UpdateDigOut(lMemorySlot.Calc2_Lim7_Pass_Sour2)
                        UpdateEOT()
                        lDutSorted = 1
                        -- stauts Bit 8,9,19, Limit Results
                        gStatusWord = gStatusWord + 525056
                        lNextMemoryLocation = lMemorySlot.Calc2_Clim_Fail_Sml
                    end
                end
                if lMemorySlot.Calc2_Lim8_Stat and lDutSorted ~= 1 then
                    TestSourceMemoryCalc2Limits(8, lMemorySlot.Calc2_Lim8_Low, lMemorySlot.Calc2_Lim8_Upp, lcalc2BufferIndex, lMemoryLocation, lBufferIndex)
                    if gStateVariables.Calc2_Lim_Result[8] == 0 then
                        UpdateDigOut(lMemorySlot.Calc2_Lim8_Pass_Sour2)
                        UpdateEOT()
                        lDutSorted = 1
                        -- stauts Bit 20, Limit Results
                        gStatusWord = gStatusWord + 1048576
                        lNextMemoryLocation = lMemorySlot.Calc2_Clim_Fail_Sml
                    end
                end
                if lMemorySlot.Calc2_Lim9_Stat and lDutSorted ~= 1 then
                    TestSourceMemoryCalc2Limits(9, lMemorySlot.Calc2_Lim9_Low, lMemorySlot.Calc2_Lim9_Upp, lcalc2BufferIndex, lMemoryLocation, lBufferIndex)
                    if gStateVariables.Calc2_Lim_Result[9] == 0 then
                        UpdateDigOut(lMemorySlot.Calc2_Lim9_Pass_Sour2)
                        UpdateEOT()
                        lDutSorted = 1
                        -- stauts Bit 8,20, Limit Results
                        gStatusWord = gStatusWord + 1048832
                        lNextMemoryLocation = lMemorySlot.Calc2_Clim_Fail_Sml
                    end
                end
                if lMemorySlot.Calc2_Lim10_Stat and lDutSorted ~= 1 then
                    TestSourceMemoryCalc2Limits(10, lMemorySlot.Calc2_Lim10_Low, lMemorySlot.Calc2_Lim10_Upp, lcalc2BufferIndex, lMemoryLocation, lBufferIndex)
                    if gStateVariables.Calc2_Lim_Result[10] == 0 then
                        UpdateDigOut(lMemorySlot.Calc2_Lim10_Pass_Sour2)
                        UpdateEOT()
                        lDutSorted = 1
                        -- stauts Bit 9,20, Limit Results
                        gStatusWord = gStatusWord + 1049088
                        lNextMemoryLocation = lMemorySlot.Calc2_Clim_Fail_Sml
                    end
                end
                if lMemorySlot.Calc2_Lim11_Stat and lDutSorted ~= 1 then
                    TestSourceMemoryCalc2Limits(11, lMemorySlot.Calc2_Lim11_Low, lMemorySlot.Calc2_Lim11_Upp, lcalc2BufferIndex, lMemoryLocation, lBufferIndex)
                    if gStateVariables.Calc2_Lim_Result[11] == 0 then
                        UpdateDigOut(lMemorySlot.Calc2_Lim11_Pass_Sour2)
                        UpdateEOT()
                        lDutSorted = 1
                        -- stauts Bit 8,9,20, Limit Results
                        gStatusWord = gStatusWord + 1049344
                        lNextMemoryLocation = lMemorySlot.Calc2_Clim_Fail_Sml
                    end
                end
                if lMemorySlot.Calc2_Lim12_Stat and lDutSorted ~= 1 then
                    TestSourceMemoryCalc2Limits(12, lMemorySlot.Calc2_Lim12_Low, lMemorySlot.Calc2_Lim12_Upp, lcalc2BufferIndex, lMemoryLocation, lBufferIndex)
                    if gStateVariables.Calc2_Lim_Result[12] == 0 then
                        UpdateDigOut(lMemorySlot.Calc2_Lim12_Pass_Sour2)
                        UpdateEOT()
                        lDutSorted = 1
                        -- stauts Bit 19,20, Limit Results
                        gStatusWord = gStatusWord + 1572864
                        lNextMemoryLocation = lMemorySlot.Calc2_Clim_Fail_Sml
                    end
                end
                -- Test failed or only Limit1 was enabled
                if lDutSorted ~= 1 then
                    if lDutSorted == 0 then
                        UpdateDigOut(lMemorySlot.Calc2_Clim_Fail_Sour2)
                        -- stauts Bit 8,9,19,20, Limit Results
                        gStatusWord = gStatusWord + 1573632
                        lNextMemoryLocation = lMemorySlot.Calc2_Clim_Fail_Sml
                    elseif lDutSorted == 2 then
                        UpdateDigOut(lMemorySlot.Calc2_Clim_Pass_Sour2)
                        lNextMemoryLocation = lMemorySlot.Calc2_Clim_Pass_Sml
                    end
                    UpdateEOT()
                elseif gStateVariables.Calc2_Lim1_Result == 0 then
                    -- Measurement Condition Register Bit 6(5 on 2400), Limits Pass
                    StatusModel.SetCondition(measStatus, 6)
                end
        
            -- Grading mode, Immediate binning
            elseif gStateVariables.Calc2_Clim_Mode == "GRAD" then
                if gStateVariables.Calc2_Clim_Bcon == "IMM" then
                    if lMemorySlot.Calc2_Lim1_Stat then
                        gLimitCapture.mFailedLimit = 0
                        if (bit.bitand(gSMCurrentBuffer.statuses[lBufferIndex], 64) == 64 and lMemorySlot.Calc2_Lim1_Fail == "IN") or
                                (bit.bitand(gSMCurrentBuffer.statuses[lBufferIndex], 64) ~= 64 and lMemorySlot.Calc2_Lim1_Fail == "OUT") then
                            gStateVariables.Calc2_Lim1_Result = 1
                            -- Measurement Condition Register Bit 1(0 on 2400), Limit1 Fail
                            StatusModel.SetCondition(measStatus, 1)
                            UpdateDigOut(lMemorySlot.Calc2_Lim1_Sour2)
                            UpdateEOT()
                            lDutGraded = 1
                            -- stauts Bit 8, Limit Results
                            gStatusWord = gStatusWord + 256
                            lNextMemoryLocation = lMemorySlot.Calc2_Clim_Fail_Sml
                        end
                    end
                    if lMemorySlot.Calc2_Lim2_Stat and lDutGraded ~= 1 then
                        TestSourceMemoryCalc2Limits(2, lMemorySlot.Calc2_Lim2_Low, lMemorySlot.Calc2_Lim2_Upp, lcalc2BufferIndex, lMemoryLocation, lBufferIndex)
                        if gStateVariables.Calc2_Lim_Result[2] == 1 then
                            if gLimitCapture.mFailedLimit == "Upper" then
                                -- Measurement Condition Register Bit 3(2 on 2400), High Limit2 Fail
                                StatusModel.SetCondition(measStatus, 3)
                                UpdateDigOut(lMemorySlot.Calc2_Lim2_Upp_Sour2)
                                -- stauts Bit 9,21, Limit Results
                                gStatusWord = gStatusWord + 2097664
                            elseif gLimitCapture.mFailedLimit == "Lower" then
                                -- Measurement Condition Register Bit 2(1 on 2400), Low Limit2 Fail
                                StatusModel.SetCondition(measStatus, 2)
                                UpdateDigOut(lMemorySlot.Calc2_Lim2_Low_Sour2)
                                -- stauts Bit 9, Limit Results
                                gStatusWord = gStatusWord + 512
                            end
                            UpdateEOT()
                            lNextMemoryLocation = lMemorySlot.Calc2_Clim_Fail_Sml
                            lDutGraded = 1
                        end
                    end
                    if lMemorySlot.Calc2_Lim3_Stat and lDutGraded ~= 1 then
                        TestSourceMemoryCalc2Limits(3, lMemorySlot.Calc2_Lim3_Low, lMemorySlot.Calc2_Lim3_Upp, lcalc2BufferIndex, lMemoryLocation, lBufferIndex)
                        if gStateVariables.Calc2_Lim_Result[3] == 1 then
                            if gLimitCapture.mFailedLimit == "Upper" then
                                -- Measurement Condition Register Bit 5(4 on 2400), High Limit3 Fail
                                StatusModel.SetCondition(measStatus, 5)
                                UpdateDigOut(lMemorySlot.Calc2_Lim3_Upp_Sour2)
                                -- stauts Bit 8,9,21, Limit Results
                                gStatusWord = gStatusWord + 2097920
                            elseif gLimitCapture.mFailedLimit == "Lower" then
                                -- Measurement Condition Register Bit 4(3 on 2400), Low Limit3 Fail
                                StatusModel.SetCondition(measStatus, 4)
                                UpdateDigOut(lMemorySlot.Calc2_Lim3_Low_Sour2)
                                -- stauts Bit 8, Limit Results
                                -- stauts Bit 9, Limit Results
                                gStatusWord = gStatusWord + 768
                            end
                            UpdateEOT()
                            lNextMemoryLocation = lMemorySlot.Calc2_Clim_Fail_Sml
                            lDutGraded = 1
                        end
                    end
                    if lMemorySlot.Calc2_Lim5_Stat and lDutGraded ~= 1 then
                        TestSourceMemoryCalc2Limits(5, lMemorySlot.Calc2_Lim5_Low, lMemorySlot.Calc2_Lim5_Upp, lcalc2BufferIndex, lMemoryLocation, lBufferIndex)
                        if gStateVariables.Calc2_Lim_Result[5] == 1 then
                            if gLimitCapture.mFailedLimit == "Upper" then
                                UpdateDigOut(lMemorySlot.Calc2_Lim5_Upp_Sour2)
                                -- stauts Bit 19,21, Limit Results
                                gStatusWord = gStatusWord + 2621440
                            elseif gLimitCapture.mFailedLimit == "Lower" then
                                UpdateDigOut(lMemorySlot.Calc2_Lim5_Low_Sour2)
                                -- stauts Bit 19, Limit Results
                                gStatusWord = gStatusWord + 524288
                            end
                            UpdateEOT()
                            lNextMemoryLocation = lMemorySlot.Calc2_Clim_Fail_Sml
                            lDutGraded = 1
                        end
                    end
                    if lMemorySlot.Calc2_Lim6_Stat and lDutGraded ~= 1 then
                        TestSourceMemoryCalc2Limits(6, lMemorySlot.Calc2_Lim6_Low, lMemorySlot.Calc2_Lim6_Upp, lcalc2BufferIndex, lMemoryLocation, lBufferIndex)
                        if gStateVariables.Calc2_Lim_Result[6] == 1 then
                            if gLimitCapture.mFailedLimit == "Upper" then
                                UpdateDigOut(lMemorySlot.Calc2_Lim6_Upp_Sour2)
                                -- stauts Bit 9,19,21, Limit Results
                                gStatusWord = gStatusWord + 2621952
                            elseif gLimitCapture.mFailedLimit == "Lower" then
                                UpdateDigOut(lMemorySlot.Calc2_Lim6_Low_Sour2)
                                -- stauts Bit 9, Limit Results
                                -- stauts Bit 19, Limit Results
                                gStatusWord = gStatusWord + 524800
                            end
                            UpdateEOT()
                            lNextMemoryLocation = lMemorySlot.Calc2_Clim_Fail_Sml
                            lDutGraded = 1
                        end
                    end
                    if lMemorySlot.Calc2_Lim7_Stat and lDutGraded ~= 1 then
                        TestSourceMemoryCalc2Limits(7, lMemorySlot.Calc2_Lim7_Low, lMemorySlot.Calc2_Lim7_Upp, lcalc2BufferIndex, lMemoryLocation, lBufferIndex)
                        if gStateVariables.Calc2_Lim_Result[7] == 1 then
                            if gLimitCapture.mFailedLimit == "Upper" then
                                UpdateDigOut(lMemorySlot.Calc2_Lim7_Upp_Sour2)
                                -- stauts Bit 8,9,19,21, Limit Results
                                gStatusWord = gStatusWord + 2622208
                            elseif gLimitCapture.mFailedLimit == "Lower" then
                                UpdateDigOut(lMemorySlot.Calc2_Lim7_Low_Sour2)
                                -- stauts Bit 8,9,19, Limit Results
                                gStatusWord = gStatusWord + 525056
                            end
                            UpdateEOT()
                            lNextMemoryLocation = lMemorySlot.Calc2_Clim_Fail_Sml
                            lDutGraded = 1
                        end
                    end
                    if lMemorySlot.Calc2_Lim8_Stat and lDutGraded ~= 1 then
                        TestSourceMemoryCalc2Limits(8, lMemorySlot.Calc2_Lim8_Low, lMemorySlot.Calc2_Lim8_Upp, lcalc2BufferIndex, lMemoryLocation, lBufferIndex)
                        if gStateVariables.Calc2_Lim_Result[8] == 1 then
                            if gLimitCapture.mFailedLimit == "Upper" then
                                UpdateDigOut(lMemorySlot.Calc2_Lim8_Upp_Sour2)
                                -- stauts Bit 20,21, Limit Results
                                gStatusWord = gStatusWord + 3145728
                            elseif gLimitCapture.mFailedLimit == "Lower" then
                                UpdateDigOut(lMemorySlot.Calc2_Lim8_Low_Sour2)
                                -- stauts Bit 20, Limit Results
                                gStatusWord = gStatusWord + 1048576
                            end
                            UpdateEOT()
                            lNextMemoryLocation = lMemorySlot.Calc2_Clim_Fail_Sml
                            lDutGraded = 1
                        end
                    end
                    if lMemorySlot.Calc2_Lim9_Stat and lDutGraded ~= 1 then
                        TestSourceMemoryCalc2Limits(9, lMemorySlot.Calc2_Lim9_Low, lMemorySlot.Calc2_Lim9_Upp, lcalc2BufferIndex, lMemoryLocation, lBufferIndex)
                        if gStateVariables.Calc2_Lim_Result[9] == 1 then
                            if gLimitCapture.mFailedLimit == "Upper" then
                                UpdateDigOut(lMemorySlot.Calc2_Lim9_Upp_Sour2)
                                -- stauts Bit 8,20,21, Limit Results
                                gStatusWord = gStatusWord + 3145984
                            elseif gLimitCapture.mFailedLimit == "Lower" then
                                UpdateDigOut(lMemorySlot.Calc2_Lim9_Low_Sour2)
                                -- stauts Bit 8,20, Limit Results
                                gStatusWord = gStatusWord + 1048832
                            end
                            UpdateEOT()
                            lNextMemoryLocation = lMemorySlot.Calc2_Clim_Fail_Sml
                            lDutGraded = 1
                        end
                    end
                    if lMemorySlot.Calc2_Lim10_Stat and lDutGraded ~= 1 then
                        TestSourceMemoryCalc2Limits(10, lMemorySlot.Calc2_Lim10_Low, lMemorySlot.Calc2_Lim10_Upp, lcalc2BufferIndex, lMemoryLocation, lBufferIndex)
                        if gStateVariables.Calc2_Lim_Result[10] == 1 then
                            if gLimitCapture.mFailedLimit == "Upper" then
                                UpdateDigOut(lMemorySlot.Calc2_Lim10_Upp_Sour2)
                                -- stauts Bit 9,20,21, Limit Results
                                gStatusWord = gStatusWord + 3146240
                            elseif gLimitCapture.mFailedLimit == "Lower" then
                                UpdateDigOut(lMemorySlot.Calc2_Lim10_Low_Sour2)
                                -- stauts Bit 9,20, Limit Results
                                gStatusWord = gStatusWord + 1049088
                            end
                            UpdateEOT()
                            lNextMemoryLocation = lMemorySlot.Calc2_Clim_Fail_Sml
                            lDutGraded = 1
                        end
                    end
                    if lMemorySlot.Calc2_Lim11_Stat and lDutGraded ~= 1 then
                        TestSourceMemoryCalc2Limits(11, lMemorySlot.Calc2_Lim11_Low, lMemorySlot.Calc2_Lim11_Upp, lcalc2BufferIndex, lMemoryLocation, lBufferIndex)
                        if gStateVariables.Calc2_Lim_Result[11] == 1 then
                            if gLimitCapture.mFailedLimit == "Upper" then
                                UpdateDigOut(lMemorySlot.Calc2_Lim11_Upp_Sour2)
                                -- stauts Bit 8,9,20,21, Limit Results
                                gStatusWord = gStatusWord + 3146496
                            elseif gLimitCapture.mFailedLimit == "Lower" then
                                UpdateDigOut(lMemorySlot.Calc2_Lim11_Low_Sour2)
                                -- stauts Bit 8,9,20, Limit Results
                                gStatusWord = gStatusWord +1049344
                            end
                            UpdateEOT()
                            lNextMemoryLocation = lMemorySlot.Calc2_Clim_Fail_Sml
                            lDutGraded = 1
                        end
                    end
                    if lMemorySlot.Calc2_Lim12_Stat and lDutGraded ~= 1 then
                        TestSourceMemoryCalc2Limits(12, lMemorySlot.Calc2_Lim12_Low, lMemorySlot.Calc2_Lim12_Upp, lcalc2BufferIndex, lMemoryLocation, lBufferIndex)
                        if gStateVariables.Calc2_Lim_Result[12] == 1 then
                            if gLimitCapture.mFailedLimit == "Upper" then
                                UpdateDigOut(lMemorySlot.Calc2_Lim12_Upp_Sour2)
                                -- stauts Bit 19,20,21, Limit Results
                                gStatusWord = gStatusWord + 3670016
                            elseif gLimitCapture.mFailedLimit == "Lower" then
                                UpdateDigOut(lMemorySlot.Calc2_Lim12_Low_Sour2)
                                -- stauts Bit 19,20, Limit Results
                                gStatusWord = gStatusWord + 1572864
                            end
                            UpdateEOT()
                            lNextMemoryLocation = lMemorySlot.Calc2_Clim_Fail_Sml
                            lDutGraded = 1
                        end
                    end
                    -- All test passed
                    if lDutGraded ~= 1 then
                        -- Measurement Condition Register Bit 6(5 on 2400), Limits Pass
                        StatusModel.SetCondition(measStatus, 6)
                        UpdateDigOut(lMemorySlot.Calc2_Clim_Pass_Sour2)
                        lNextMemoryLocation = lMemorySlot.Calc2_Clim_Pass_Sml
                        UpdateEOT()
                    end
        
                -- Grading mode, End binning
                elseif gStateVariables.Calc2_Clim_Bcon == "END" then
                    if lMemorySlot.Calc2_Lim1_Stat then
                        gLimitCapture.mFailedLimit = 0
                        if (bit.bitand(gSMCurrentBuffer.statuses[lBufferIndex], 64) == 64 and lMemorySlot.Calc2_Lim1_Fail == "IN") or
                                (bit.bitand(gSMCurrentBuffer.statuses[lBufferIndex], 64) ~= 64 and lMemorySlot.Calc2_Lim1_Fail == "OUT") then
                            gStateVariables.Calc2_Lim1_Result = 1
                            -- Measurement Condition Register Bit 1(0 on 2400), Limit1 Fail
                            StatusModel.SetCondition(measStatus, 1)
                            lDutGraded = 1
                            if gLimitCapture.mFirstFailureTest == 0 then
                                gLimitCapture.mFirstFailureLimit = "Comp"
                                gLimitCapture.mFirstFailureTest = "Comp"
                                gLimitCapture.mFailedMemoryLocation = lMemoryLocation
                            end
                            -- stauts Bit 8, Limit Results
                            gStatusWord = gStatusWord + 256
                        end
                    end
                    if lMemorySlot.Calc2_Lim2_Stat and lDutGraded ~= 1 then
                        TestSourceMemoryCalc2Limits(2, lMemorySlot.Calc2_Lim2_Low, lMemorySlot.Calc2_Lim2_Upp, lcalc2BufferIndex, lMemoryLocation, lBufferIndex)
                        if gStateVariables.Calc2_Lim_Result[2] == 1 then
                            lDutGraded = 1
                            if gLimitCapture.mFailedLimit == "Upper" then
                                -- Measurement Condition Register Bit 3(2 on 2400), High Limit2 Fail
                                StatusModel.SetCondition(measStatus, 3)
                                -- stauts Bit 9,21, Limit Results
                                gStatusWord = gStatusWord + 2097664
                            elseif gLimitCapture.mFailedLimit == "Lower" then
                                -- Measurement Condition Register Bit 2(1 on 2400), Low Limit2 Fail
                                StatusModel.SetCondition(measStatus, 2)
                                -- stauts Bit 9, Limit Results
                                gStatusWord = gStatusWord + 512
                            end
                            lNextMemoryLocation = lMemorySlot.Calc2_Clim_Fail_Sml
                        end
                     end
                    if lMemorySlot.Calc2_Lim3_Stat and lDutGraded ~= 1 then
                        TestSourceMemoryCalc2Limits(3, lMemorySlot.Calc2_Lim3_Low, lMemorySlot.Calc2_Lim3_Upp, lcalc2BufferIndex, lMemoryLocation, lBufferIndex)
                        if gStateVariables.Calc2_Lim_Result[3] == 1 then
                            lDutGraded = 1
                            if gLimitCapture.mFailedLimit == "Upper" then
                                -- Measurement Condition Register Bit 5(4 on 2400), High Limit3 Fail
                                StatusModel.SetCondition(measStatus, 5)
                                -- stauts Bit 8,9,21, Limit Results
                                gStatusWord = gStatusWord + 2097920
                            elseif gLimitCapture.mFailedLimit == "Lower" then
                                -- Measurement Condition Register Bit 4(3 on 2400), Low Limit3 Fail
                                StatusModel.SetCondition(measStatus, 4)
                                -- stauts Bit 8,9, Limit Results
                                gStatusWord = gStatusWord + 768
                            end
                            lNextMemoryLocation = lMemorySlot.Calc2_Clim_Fail_Sml
                        end
                    end
                    --if gStateVariables.Calc2_Lim_Stat[4] == 1 then
                        --TestSourceMemoryCalc2Limits(4) end
                    if lMemorySlot.Calc2_Lim5_Stat and lDutGraded ~= 1 then
                        TestSourceMemoryCalc2Limits(5, lMemorySlot.Calc2_Lim5_Low, lMemorySlot.Calc2_Lim5_Upp, lcalc2BufferIndex, lMemoryLocation, lBufferIndex)
                        if gStateVariables.Calc2_Lim_Result[5] == 1 then
                            lDutGraded = 1
                            if gLimitCapture.mFailedLimit == "Upper" then
                                -- stauts Bit 19,21, Limit Results
                                gStatusWord = gStatusWord + 2621440
                            elseif gLimitCapture.mFailedLimit == "Lower" then
                                -- stauts Bit 19, Limit Results
                                gStatusWord = gStatusWord + 524288
                            end
                            lNextMemoryLocation = lMemorySlot.Calc2_Clim_Fail_Sml
                        end
                    end
                    if lMemorySlot.Calc2_Lim6_Stat and lDutGraded ~= 1 then
                        TestSourceMemoryCalc2Limits(6, lMemorySlot.Calc2_Lim6_Low, lMemorySlot.Calc2_Lim6_Upp, lcalc2BufferIndex, lMemoryLocation, lBufferIndex)
                        if gStateVariables.Calc2_Lim_Result[6] == 1 then
                            lDutGraded = 1
                            if gLimitCapture.mFailedLimit == "Upper" then
                                -- stauts Bit 9,19,21, Limit Results
                                gStatusWord = gStatusWord + 2621952
                            elseif gLimitCapture.mFailedLimit == "Lower" then
                                -- stauts Bit 9,19, Limit Results
                                gStatusWord = gStatusWord + 524800
                            end
                            lNextMemoryLocation = lMemorySlot.Calc2_Clim_Fail_Sml
                        end
                    end
                    if lMemorySlot.Calc2_Lim7_Stat and lDutGraded ~= 1 then
                        TestSourceMemoryCalc2Limits(7, lMemorySlot.Calc2_Lim7_Low, lMemorySlot.Calc2_Lim7_Upp, lcalc2BufferIndex, lMemoryLocation, lBufferIndex)
                        if gStateVariables.Calc2_Lim_Result[7] == 1 then
                            lDutGraded = 1
                            if gLimitCapture.mFailedLimit == "Upper" then
                                -- stauts Bit 8,9,19,21, Limit Results
                                gStatusWord = gStatusWord + 2622208
                            elseif gLimitCapture.mFailedLimit == "Lower" then
                                -- stauts Bit 8,9,19, Limit Results
                                gStatusWord = gStatusWord + 525056
                            end
                            lNextMemoryLocation = lMemorySlot.Calc2_Clim_Fail_Sml
                        end
                    end
                    if lMemorySlot.Calc2_Lim8_Stat and lDutGraded ~= 1 then
                        TestSourceMemoryCalc2Limits(8, lMemorySlot.Calc2_Lim8_Low, lMemorySlot.Calc2_Lim8_Upp, lcalc2BufferIndex, lMemoryLocation, lBufferIndex)
                        if gStateVariables.Calc2_Lim_Result[8] == 1 then
                            lDutGraded = 1
                            if gLimitCapture.mFailedLimit == "Upper" then
                                -- stauts Bit 20,21, Limit Results
                                gStatusWord = gStatusWord + 3145728
                            elseif gLimitCapture.mFailedLimit == "Lower" then
                                -- stauts Bit 20, Limit Results
                                gStatusWord = gStatusWord + 1048576
                            end
                            lNextMemoryLocation = lMemorySlot.Calc2_Clim_Fail_Sml
                        end
                    end
                    if lMemorySlot.Calc2_Lim9_Stat and lDutGraded ~= 1 then
                        TestSourceMemoryCalc2Limits(9, lMemorySlot.Calc2_Lim9_Low, lMemorySlot.Calc2_Lim9_Upp, lcalc2BufferIndex, lMemoryLocation, lBufferIndex)
                        if gStateVariables.Calc2_Lim_Result[9] == 1 then
                            lDutGraded = 1
                            if gLimitCapture.mFailedLimit == "Upper" then
                                -- stauts Bit 8,20,21, Limit Results
                                gStatusWord = gStatusWord + 3145984
                            elseif gLimitCapture.mFailedLimit == "Lower" then
                                -- stauts Bit 8,20, Limit Results
                                gStatusWord = gStatusWord + 1048832
                            end
                            lNextMemoryLocation = lMemorySlot.Calc2_Clim_Fail_Sml
                        end
                    end
                    if lMemorySlot.Calc2_Lim10_Stat and lDutGraded ~= 1 then
                        TestSourceMemoryCalc2Limits(10, lMemorySlot.Calc2_Lim10_Low, lMemorySlot.Calc2_Lim10_Upp, lcalc2BufferIndex, lMemoryLocation, lBufferIndex)
                        if gStateVariables.Calc2_Lim_Result[10] == 1 then
                            lDutGraded = 1
                            if gLimitCapture.mFailedLimit == "Upper" then
                                -- stauts Bit 9,20,21, Limit Results
                                gStatusWord = gStatusWord + 3146240
                            elseif gLimitCapture.mFailedLimit == "Lower" then
                                -- stauts Bit 9,20, Limit Results
                                gStatusWord = gStatusWord + 1049088
                            end
                            lNextMemoryLocation = lMemorySlot.Calc2_Clim_Fail_Sml
                        end
                    end
                    if lMemorySlot.Calc2_Lim11_Stat and lDutGraded ~= 1 then
                        TestSourceMemoryCalc2Limits(11, lMemorySlot.Calc2_Lim11_Low, lMemorySlot.Calc2_Lim11_Upp, lcalc2BufferIndex, lMemoryLocation, lBufferIndex)
                        if gStateVariables.Calc2_Lim_Result[11] == 1 then
                            lDutGraded = 1
                            if gLimitCapture.mFailedLimit == "Upper" then
                                -- stauts Bit 8,9,20,21, Limit Results
                                gStatusWord = gStatusWord + 3146496
                            elseif gLimitCapture.mFailedLimit == "Lower" then
                                -- stauts Bit 8,9,20, Limit Results
                                gStatusWord = gStatusWord + 1049344
                            end
                            lNextMemoryLocation = lMemorySlot.Calc2_Clim_Fail_Sml
                        end
                    end
                    if lMemorySlot.Calc2_Lim12_Stat and lDutGraded ~= 1 then
                        TestSourceMemoryCalc2Limits(12, lMemorySlot.Calc2_Lim12_Low, lMemorySlot.Calc2_Lim12_Upp, lcalc2BufferIndex, lMemoryLocation, lBufferIndex)
                        if gStateVariables.Calc2_Lim_Result[12] == 1 then
                            lDutGraded = 1
                            if gLimitCapture.mFailedLimit == "Upper" then
                                -- stauts Bit 19,20,21, Limit Results
                                gStatusWord = gStatusWord + 3670016
                            elseif gLimitCapture.mFailedLimit == "Lower" then
                                -- stauts Bit 19,20, Limit Results
                                gStatusWord = gStatusWord + 1572864
                            end
                            lNextMemoryLocation = lMemorySlot.Calc2_Clim_Fail_Sml
                        end
                    end
                end
            end
        
            if lNextMemoryLocation == "NEXT" or lNextMemoryLocation == 0 then
                return 0
            else
                return lNextMemoryLocation
            end
        end
        
        --[[
            LoadSourceMemoryLocation loads the smu with memory location settings
            Used by RecallSourceMemoryLocation function
        --]]
        local LoadSourceMemoryLocation = function (lMemoryLocation)
            local lMemorySlot = gMemLoc[lMemoryLocation]
        
            gAccessors.mSetSourceOutput(0)
            -- recall the memory location
            gStateVariables.Sour_Del                    = lMemorySlot.Sour_Del
            gStateVariables.Sour_Del_Auto               = lMemorySlot.Sour_Del_Auto
            gStateVariables.Trig_Del                    = lMemorySlot.Trig_Del
            gStateVariables.Sour_Curr_Trig_Sfac         = lMemorySlot.Sour_Curr_Trig_Sfac
            gStateVariables.Sour_Volt_Trig_Sfac         = lMemorySlot.Sour_Volt_Trig_Sfac
            gStateVariables.Sour_Curr_Trig_Sfac_State   = lMemorySlot.Sour_Curr_Trig_Sfac_Stat
            gStateVariables.Sour_Volt_Trig_Sfac_State   = lMemorySlot.Sour_Volt_Trig_Sfac_Stat
            gStateVariables.Sens_Func_Conc              = lMemorySlot.Sens_Func_Conc
            gStateVariables.Sens_Func.VOLT              = lMemorySlot.Sens_Func_Volt
            gStateVariables.Sens_Func.CURR              = lMemorySlot.Sens_Func_Curr
            gStateVariables.Sens_Func.RES               = lMemorySlot.Sens_Func_Res
            gStateVariables.Sens_Func.ANY               = lMemorySlot.Sens_Func_Any
        
            gStateVariables.Calc1_Stat                  = lMemorySlot.Calc1_Stat
            gStateVariables.Calc2_Feed                  = lMemorySlot.Calc2_Feed
            gStateVariables.Calc2_Null_Offs             = lMemorySlot.Calc2_Null_Offs
            gStateVariables.Calc2_Null_Stat             = lMemorySlot.Calc2_Null_Stat
            gStateVariables.Calc2_Lim1_Fail             = lMemorySlot.Calc2_Lim1_Fail
            gStateVariables.Calc2_Lim1_Sour2            = lMemorySlot.Calc2_Lim1_Sour2
            gStateVariables.Calc2_Lim1_Stat             = lMemorySlot.Calc2_Lim1_Stat
        
            gStateVariables.Calc2_Lim_Upp[2]            = lMemorySlot.Calc2_Lim2_Upp
            gStateVariables.Calc2_Lim_Upp_Sour2[2]      = lMemorySlot.Calc2_Lim2_Upp_Sour2
            gStateVariables.Calc2_Lim_Low[2]            = lMemorySlot.Calc2_Lim2_Low
            gStateVariables.Calc2_Lim_Low_Sour2[2]      = lMemorySlot.Calc2_Lim2_Low_Sour2
            gStateVariables.Calc2_Lim_Pass_Sour2[2]     = lMemorySlot.Calc2_Lim2_Pass_Sour2
            gStateVariables.Calc2_Lim_Stat[2]           = lMemorySlot.Calc2_Lim2_Stat
        
            gStateVariables.Calc2_Lim_Upp[3]            = lMemorySlot.Calc2_Lim3_Upp
            gStateVariables.Calc2_Lim_Upp_Sour2[3]      = lMemorySlot.Calc2_Lim3_Upp_Sour2
            gStateVariables.Calc2_Lim_Low[3]            = lMemorySlot.Calc2_Lim3_Low
            gStateVariables.Calc2_Lim_Low_Sour2[3]      = lMemorySlot.Calc2_Lim3_Low_Sour2
            gStateVariables.Calc2_Lim_Pass_Sour2[3]     = lMemorySlot.Calc2_Lim3_Pass_Sour2
            gStateVariables.Calc2_Lim_Stat[3]           = lMemorySlot.Calc2_Lim3_Stat
        
            gStateVariables.Calc2_Lim_Upp[5]            = lMemorySlot.Calc2_Lim5_Upp
            gStateVariables.Calc2_Lim_Upp_Sour2[5]      = lMemorySlot.Calc2_Lim5_Upp_Sour2
            gStateVariables.Calc2_Lim_Low[5]            = lMemorySlot.Calc2_Lim5_Low
            gStateVariables.Calc2_Lim_Low_Sour2[5]      = lMemorySlot.Calc2_Lim5_Low_Sour2
            gStateVariables.Calc2_Lim_Pass_Sour2[5]     = lMemorySlot.Calc2_Lim5_Pass_Sour2
            gStateVariables.Calc2_Lim_Stat[5]           = lMemorySlot.Calc2_Lim5_Stat
        
            gStateVariables.Calc2_Lim_Upp[6]            = lMemorySlot.Calc2_Lim6_Upp
            gStateVariables.Calc2_Lim_Upp_Sour2[6]      = lMemorySlot.Calc2_Lim6_Upp_Sour2
            gStateVariables.Calc2_Lim_Low[6]            = lMemorySlot.Calc2_Lim6_Low
            gStateVariables.Calc2_Lim_Low_Sour2[6]      = lMemorySlot.Calc2_Lim6_Low_Sour2
            gStateVariables.Calc2_Lim_Pass_Sour2[6]     = lMemorySlot.Calc2_Lim6_Pass_Sour2
            gStateVariables.Calc2_Lim_Stat[6]           = lMemorySlot.Calc2_Lim6_Stat
        
            gStateVariables.Calc2_Lim_Upp[7]            = lMemorySlot.Calc2_Lim7_Upp
            gStateVariables.Calc2_Lim_Upp_Sour2[7]      = lMemorySlot.Calc2_Lim7_Upp_Sour2
            gStateVariables.Calc2_Lim_Low[7]            = lMemorySlot.Calc2_Lim7_Low
            gStateVariables.Calc2_Lim_Low_Sour2[7]      = lMemorySlot.Calc2_Lim7_Low_Sour2
            gStateVariables.Calc2_Lim_Pass_Sour2[7]     = lMemorySlot.Calc2_Lim7_Pass_Sour2
            gStateVariables.Calc2_Lim_Stat[7]           = lMemorySlot.Calc2_Lim7_Stat
        
            gStateVariables.Calc2_Lim_Upp[8]            = lMemorySlot.Calc2_Lim8_Upp
            gStateVariables.Calc2_Lim_Upp_Sour2[8]      = lMemorySlot.Calc2_Lim8_Upp_Sour2
            gStateVariables.Calc2_Lim_Low[8]            = lMemorySlot.Calc2_Lim8_Low
            gStateVariables.Calc2_Lim_Low_Sour2[8]      = lMemorySlot.Calc2_Lim8_Low_Sour2
            gStateVariables.Calc2_Lim_Pass_Sour2[8]     = lMemorySlot.Calc2_Lim8_Pass_Sour2
            gStateVariables.Calc2_Lim_Stat[8]           = lMemorySlot.Calc2_Lim8_Stat
        
            gStateVariables.Calc2_Lim_Upp[9]            = lMemorySlot.Calc2_Lim9_Upp
            gStateVariables.Calc2_Lim_Upp_Sour2[9]      = lMemorySlot.Calc2_Lim9_Upp_Sour2
            gStateVariables.Calc2_Lim_Low[9]            = lMemorySlot.Calc2_Lim9_Low
            gStateVariables.Calc2_Lim_Low_Sour2[9]      = lMemorySlot.Calc2_Lim9_Low_Sour2
            gStateVariables.Calc2_Lim_Pass_Sour2[9]     = lMemorySlot.Calc2_Lim9_Pass_Sour2
            gStateVariables.Calc2_Lim_Stat[9]           = lMemorySlot.Calc2_Lim9_Stat
        
            gStateVariables.Calc2_Lim_Upp[10]           = lMemorySlot.Calc2_Lim10_Upp
            gStateVariables.Calc2_Lim_Upp_Sour2[10]     = lMemorySlot.Calc2_Lim10_Upp_Sour2
            gStateVariables.Calc2_Lim_Low[10]           = lMemorySlot.Calc2_Lim10_Low
            gStateVariables.Calc2_Lim_Low_Sour2[10]     = lMemorySlot.Calc2_Lim10_Low_Sour2
            gStateVariables.Calc2_Lim_Pass_Sour2[10]    = lMemorySlot.Calc2_Lim10_Pass_Sour2
            gStateVariables.Calc2_Lim_Stat[10]          = lMemorySlot.Calc2_Lim10_Stat
        
            gStateVariables.Calc2_Lim_Upp[11]           = lMemorySlot.Calc2_Lim11_Upp
            gStateVariables.Calc2_Lim_Upp_Sour2[11]     = lMemorySlot.Calc2_Lim11_Upp_Sour2
            gStateVariables.Calc2_Lim_Low[11]           = lMemorySlot.Calc2_Lim11_Low
            gStateVariables.Calc2_Lim_Low_Sour2[11]     = lMemorySlot.Calc2_Lim11_Low_Sour2
            gStateVariables.Calc2_Lim_Pass_Sour2[11]    = lMemorySlot.Calc2_Lim11_Pass_Sour2
            gStateVariables.Calc2_Lim_Stat[11]          = lMemorySlot.Calc2_Lim11_Stat
        
            gStateVariables.Calc2_Lim_Upp[12]           = lMemorySlot.Calc2_Lim12_Upp
            gStateVariables.Calc2_Lim_Upp_Sour2[12]     = lMemorySlot.Calc2_Lim12_Upp_Sour2
            gStateVariables.Calc2_Lim_Low[12]           = lMemorySlot.Calc2_Lim12_Low
            gStateVariables.Calc2_Lim_Low_Sour2[12]     = lMemorySlot.Calc2_Lim12_Low_Sour2
            gStateVariables.Calc2_Lim_Pass_Sour2[12]    = lMemorySlot.Calc2_Lim12_Pass_Sour2
            gStateVariables.Calc2_Lim_Stat[12]          = lMemorySlot.Calc2_Lim12_Stat
        
            gStateVariables.Calc2_Clim_Pass_Sour2       = lMemorySlot.Calc2_Clim_Pass_Sour2
            gStateVariables.Calc2_Clim_Pass_Sml         = lMemorySlot.Calc2_Clim_Pass_Sml
            gStateVariables.Calc2_Clim_Fail_Sour2       = lMemorySlot.Calc2_Clim_Fail_Sour2
            gStateVariables.Calc2_Clim_Fail_Sml         = lMemorySlot.Calc2_Clim_Fail_Sml
        
            -- Autozero
            gAccessors.mSetMeasureAutoZero(lMemorySlot.Syst_Azer_Stat)
            -- Sense Mode
            gAccessors.mSetSense(lMemorySlot.Syst_Rsen)
        
            -- Source Function
            gAccessors.mSetSourceFunc(lMemorySlot.Sour_Func_Mode)
            if lMemorySlot.Sour_Func_Mode == gDCVOLTS then
                -- set soruce level
                smua_SetSrcLevV(lMemorySlot.Sour_Volt_Ampl)
            else -- smua.OUTPUT_DCAMPS
                -- set soruce level
                smua_SetSrcLevI(lMemorySlot.Sour_Curr_Ampl)
            end
        
            -- Voltage Limit
            smua_SetSrcLimV(lMemorySlot.Sens_Volt_Prot)
            gStateVariables.Sens_Volt_Prot = lMemorySlot.Actual_Volt_Prot
            -- Current Limit
            smua_SetSrcLimI(lMemorySlot.Sens_Curr_Prot)
            gStateVariables.Sens_Curr_Prot = lMemorySlot.Actual_Curr_Prot
            -- Source Voltage Range
            if lMemorySlot.Sour_Volt_Rang_Auto == 1 then
                gAccessors.mSetSourceAutoRangev(1)
            else
                if lMemorySlot.Sour_Volt_Rang then
                    smua_SetSrcRngV(lMemorySlot.Sour_Volt_Rang)
                end
            end
        
            -- Source Current Range
            if lMemorySlot.Sour_Curr_Rang_Auto == 1 then
                gAccessors.mSetSourceAutoRangei(1)
            else
                if lMemorySlot.Sour_Curr_Rang then
                    smua_SetSrcRngI(lMemorySlot.Sour_Curr_Rang)
                end
            end
        
            -- Voltage Measurement Range
            if lMemorySlot.Sens_Volt_Rang_Auto == 1 then
                gAccessors.mSetMeasureAutoRangev(1)
            else
                if lMemorySlot.Sens_Volt_Rang then
                    smua_SetMeasRngV(lMemorySlot.Sens_Volt_Rang)
                end
            end
        
            -- Current Measurement Range
            if lMemorySlot.Sens_Curr_Rang_Auto == 1 then
                gAccessors.mSetMeasureAutoRangei(1)
            else
                if lMemorySlot.Sens_Curr_Rang then
                    smua_SetMeasRngI(lMemorySlot.Sens_Curr_Rang)
                end
            end
        
            -- soure auto delay
            if lMemorySlot.Sour_Del_Auto then
                gAccessors.mSetSourceDelay(smua.DELAY_AUTO)
            end
        
            -- Measuremente NPLC
            gAccessors.mSetMeasureNplc(lMemorySlot.Sens_Nplc)
            -- Filter
            gAccessors.mSetFilterType(lMemorySlot.Sens_Aver_Tcon)
            gAccessors.mSetFilterCount(lMemorySlot.Sens_Aver_Coun)
            gAccessors.mSetFilterEnable(lMemorySlot.Sens_Aver_Stat)
        end
        
        --[[
            Setting change functions used in source memory sweeps
            the order with which these functions get executed is
            determined by the SourceMemorySweep function
        --]]
        
        -- UpdateSourceVoltageRange updates the voltage source range
        UpdateSourceVoltageRange = function (lMemorySlot)
            if lMemorySlot.Sour_Volt_Rang_Auto == 1 then
                gAccessors.mSetSourceAutoRangev(1)
            else
                local lLevel = smua_GetSrcLevV()
                local lRangeMax = lMemorySlot.Sour_Volt_Rang * 1.01
                if gMathAbs(lLevel) > lRangeMax then
                    if lLevel < 0 then
                        smua_SetSrcLevV(-lRangeMax)
                    else
                        smua_SetSrcLevV(lRangeMax)
                    end
                end
                smua_SetSrcRngV(lMemorySlot.Sour_Volt_Rang)
            end
        end
        
        -- UpdateVoltageProtectionLevel updates the voltage protection level
        UpdateVoltageProtectionLevel = function (lMemorySlot)
            if gMathAbs(gMathAbs(lMemorySlot.Sens_Volt_Prot)/smua_GetSrcLimV() - 1) >= gEpsilon then
                smua_SetSrcLimV(lMemorySlot.Sens_Volt_Prot)
            end
        end
        
        -- UpdateSourceVoltageLevel updates the voltage level
        UpdateSourceVoltageLevel = function (lMemorySlot, lTriggerPoint)
            local lAbsLevel
        
            if lMemorySlot.Sour_Volt_Trig_Sfac_Stat then
                -- only the first time
                if lTriggerPoint == 1 then
                    if gSampleBuffer.mCount > 0 and gSampleBuffer.mVoltage[1] and gSampleBuffer.mVoltage[1] ~= gNan then
                        lMemorySlot.Sour_Volt_Ampl = lMemorySlot.Sour_Volt_Trig_Sfac * gSampleBuffer.mVoltage[1]
                    else
                        lMemorySlot.Sour_Volt_Ampl = 0
                    end
                else
                    if gSampleBuffer.mCount > 0 and gSampleBuffer.mVoltage[gSampleBuffer.mCount] and gSampleBuffer.mVoltage[gSampleBuffer.mCount] ~= gNan then
                        lMemorySlot.Sour_Volt_Ampl = lMemorySlot.Sour_Volt_Trig_Sfac * gSampleBuffer.mVoltage[gSampleBuffer.mCount]
                    else
                        lMemorySlot.Sour_Volt_Ampl = 0
                    end
                end
            end
            lAbsLevel = gMathAbs(lMemorySlot.Sour_Volt_Ampl)
            if gMathAbs(lMemorySlot.Sour_Volt_Ampl - smua_GetSrcLevV()) >= gEpsilon * lAbsLevel then
                if lMemorySlot.Sour_Volt_Rang_Auto == 1 then
                    if lAbsLevel > gOperatingBoundaries.mMaximumVoltageRange then
                        lAbsLevel = gOperatingBoundaries.mMaximumVoltageRange
                        if lMemorySlot.Sour_Volt_Ampl >= 0 then
                            lMemorySlot.Sour_Volt_Ampl = lAbsLevel
                        else
                            lMemorySlot.Sour_Volt_Ampl = -lAbsLevel
                        end
                    end
                else
                    if smua_GetSrcRngV() * 1.01 <= lAbsLevel then
                        lAbsLevel = smua_GetSrcRngV() * 1.01
                        if lMemorySlot.Sour_Volt_Ampl >= 0 then
                            lMemorySlot.Sour_Volt_Ampl = lAbsLevel
                        else
                            lMemorySlot.Sour_Volt_Ampl = -lAbsLevel
                        end
                    end
                end
                if lAbsLevel > gSafeOperatingArea.mVoltage and gMathAbs(lMemorySlot.Sens_Curr_Prot)/gSafeOperatingArea.mCurrent -1 >= gEpsilon then
                    if lMemorySlot.Sour_Volt_Ampl >= 0 then
                        lMemorySlot.Sour_Volt_Ampl = gSafeOperatingArea.mVoltage
                    else
                        lMemorySlot.Sour_Volt_Ampl = -gSafeOperatingArea.mVoltage
                    end
                end
                smua_SetSrcLevV(lMemorySlot.Sour_Volt_Ampl)
            end
        end
        
        -- UpdateSourceCurrentRange updates the current source range
        UpdateSourceCurrentRange = function (lMemorySlot)
            if lMemorySlot.Sour_Curr_Rang_Auto == 1 then
                gAccessors.mSetSourceAutoRangei(1)
            else
                local lLevel = smua_GetSrcLevI()
                local lRangeMax = lMemorySlot.Sour_Curr_Rang * 1.01
                if gMathAbs(lLevel) > lRangeMax then
                    if lLevel < 0 then
                        smua_SetSrcLevI(-lRangeMax)
                    else
                        smua_SetSrcLevI(lRangeMax)
                    end
                end
                smua_SetSrcRngI(lMemorySlot.Sour_Curr_Rang)
            end
        end
        
        -- UpdateCurrentProtectionLevel updates the current protection level
        UpdateCurrentProtectionLevel = function (lMemorySlot)
            if gMathAbs(gMathAbs(lMemorySlot.Sens_Curr_Prot)/smua_GetSrcLimI() - 1) >= gEpsilon then
                smua_SetSrcLimI(lMemorySlot.Sens_Curr_Prot)
            end
        end
        
        -- UpdateSourceCurrentLevel updates the current level
        UpdateSourceCurrentLevel = function (lMemorySlot, lTriggerPoint)
            local lAbsLevel
        
            if lMemorySlot.Sour_Curr_Trig_Sfac_Stat then
                -- only the first time
                if lTriggerPoint == 1 then
                    if gSampleBuffer.mCount > 0 and gSampleBuffer.mCurrent[1] and gSampleBuffer.mCurrent[1] ~= gNan then
                        lMemorySlot.Sour_Curr_Ampl = lMemorySlot.Sour_Curr_Trig_Sfac * gSampleBuffer.mCurrent[1]
                    else
                        lMemorySlot.Sour_Curr_Ampl = 0
                    end
                else
                    if gSampleBuffer.mCount > 0 and gSampleBuffer.mCurrent[gSampleBuffer.mCount] and gSampleBuffer.mCurrent[gSampleBuffer.mCount] ~= gNan then
                        lMemorySlot.Sour_Curr_Ampl = lMemorySlot.Sour_Curr_Trig_Sfac * gSampleBuffer.mCurrent[gSampleBuffer.mCount]
                    else
                        lMemorySlot.Sour_Curr_Ampl = 0
                    end
                end
            end
            lAbsLevel = gMathAbs(lMemorySlot.Sour_Curr_Ampl)
            if gMathAbs(lMemorySlot.Sour_Curr_Ampl - smua_GetSrcLevI()) >= lAbsLevel * gEpsilon then
                if lMemorySlot.Sour_Curr_Rang_Auto == 1 then
                    if lAbsLevel > gOperatingBoundaries.mMaximumCurrentRange then
                        lAbsLevel = gOperatingBoundaries.mMaximumCurrentRange
                        if lMemorySlot.Sour_Curr_Ampl >= 0 then
                            lMemorySlot.Sour_Curr_Ampl = lAbsLevel
                        else
                            lMemorySlot.Sour_Curr_Ampl = -lAbsLevel
                        end
                    end
                else
                    if smua_GetSrcRngI() * 1.01 <= lAbsLevel then
                        lAbsLevel = smua_GetSrcRngI() * 1.01
                        if lMemorySlot.Sour_Curr_Ampl >= 0 then
                            lMemorySlot.Sour_Curr_Ampl = lAbsLevel
                        else
                            lMemorySlot.Sour_Curr_Ampl = -lAbsLevel
                        end
                    end
                end
                if lAbsLevel > gSafeOperatingArea.mCurrent 
                and gMathAbs(lMemorySlot.Sens_Volt_Prot)/gSafeOperatingArea.mVoltage - 1 >= gEpsilon then
                    if lMemorySlot.Sour_Curr_Ampl >= 0 then
                        lMemorySlot.Sour_Curr_Ampl = gSafeOperatingArea.mCurrent
                    else
                        lMemorySlot.Sour_Curr_Ampl = -gSafeOperatingArea.mCurrent
                    end
                end
                smua_SetSrcLevI(lMemorySlot.Sour_Curr_Ampl)
            end
        end
        
        local ProcessSourceMemoryData = function()
            -- clear status word
            gStatusWord = 0
            -- clear measurement status condition register
            measStatus.mCondition = 0
            gNextMemoryLocation = 0
            -- update smaple buffer
            UpdateSourceMemorySampleBuffer(gSampleBufferIndex, gMemorySlot)
        
        --[[
            -- if Read? was used then print the values
            if gPrintEnable == true then
                PrintImmediate(gSampleBufferIndex)
            end
        --]]
            -- update calc2 data
            gCalculate2.mNullOffset = gMemorySlot.Calc2_Null_Stat
            gCalculate2.mLimits = gMemorySlot.Calc2Limits
        
            if gMemorySlot.Calc1_Stat then
                -- status Bit5, Math
                gStatusWord = gStatusWord + 32
            end
        
            -- stauts Bit 6, Null
            if gCalculate2.mNullOffset then
                gStatusWord = gStatusWord + 64
            end
        
            if gCalculate2.mLimits then
                -- stauts Bit 7, Limits
                gStatusWord = gStatusWord + 128
            end
        
            -- Process Calc2 Limit tests and Null offset
            if gMemorySlot.Calc2_Feed ~= "CALC1" then
                if gCalculate2.mLimits or gCalculate2.mNullOffset then
                    -- Update calc2 buffer
                    UpdateSourceMemoryCalc2Buffer(gMemorySlot, gSampleBufferIndex)
        
                    -- perform limit tests
                    if gCalculate2.mLimits then
                        gNextMemoryLocation = ProcessSourceMemoryCalc2Data(gCalc2BufferIndex, gMemoryLocation, gSampleBufferIndex)
                    end
        
                    gCalculate2Buffer.mStatus[gCalc2BufferIndex] = gStatusWord
                    -- Update Trace buffer
                    if gStateVariables.Trac_Cont == "NEXT" then
                        if gStateVariables.Trac_Feed == "CALC2" then
                            UpdateTraceBuffer(gCalc2BufferIndex)
                        end
                    end
                end
            end
        
            -- Process Calc1 Math equations
            if gMemorySlot.Calc1_Stat then
                if not gMathVariables.mSameExpression then
                    gMathVariables.mDepth = gMathCatalog[gMemorySlot.Calc1_Math_Name].mExpression.mDepth
                    gMathVariables.mDataCount = 0
                    gMathVariables.mDataCount = gMathVariables.mDataCount + gMathVariables.mDepth
                    gIntermediateSampleBuffer.mCount = 0
                end
        
                UpdateIntermediateSampleBuffer(gSampleBufferIndex)
        
                if gIntermediateSampleBuffer.mCount == gMathVariables.mDataCount then
                    gCalculate1Buffer.mData[gCalc1BufferIndex] = gMathCatalog[gMemorySlot.Calc1_Math_Name].mExpression.Evaluate()
                    gCalculate1Buffer.mTime[gCalc1BufferIndex] = gSampleBuffer.mTime[gSampleBufferIndex]
        
                    -- stauts Bit 5, Math
                    gStatusWord = gStatusWord + 32
        
                    -- update calc2 data
                    if gMemorySlot.Calc2_Feed == "CALC1" then
                        if gCalculate2.mLimits or gCalculate2.mNullOffset then
                            UpdateSourceMemoryCalc2Buffer(gMemorySlot, gSampleBufferIndex)
        
                            if gCalculate2.mLimits then
                                gNextMemoryLocation = ProcessSourceMemoryCalc2Data(gCalc1BufferIndex, gMemoryLocation, gSampleBufferIndex)
                                -- stauts Bit 7, Limits
                                gStatusWord = gStatusWord + 128
                            end
        
                            gCalculate2Buffer.mStatus[gCalc2BufferIndex] = gStatusWord
        
                            -- Update trace buffer
                            if gStateVariables.Trac_Cont == "NEXT" then
                                if gStateVariables.Trac_Feed == "CALC2" then
                                    UpdateTraceBuffer(gCalc2BufferIndex)
                                end
                            end
                        else
                            gCalculate2Buffer.mStatus[gCalc2BufferIndex] = gStatusWord
                        end
                    end
        
                    gCalculate1Buffer.mStatus[gCalc1BufferIndex] = gStatusWord
        
                    -- Update trace buffer
                    if gStateVariables.Trac_Cont == "NEXT" then
                        if gStateVariables.Trac_Feed == "CALC1" then
                            UpdateTraceBuffer(gCalc1BufferIndex)
                        end
                    end
        
                    -- Reset the index and count to 0 when greater than 2500
                    if gCalc1BufferIndex >= 2500 then
                        gCalc1BufferIndex = 0
                        gCalculate1Buffer.mCount = 0
                    end
        
                    gCalc1BufferIndex = gCalc1BufferIndex + 1
                    gCalculate1Buffer.mCount = gCalculate1Buffer.mCount + 1
                    gMathVariables.mDataCount = gMathVariables.mDataCount + gMathVariables.mDepth
                end
        
                local lNextMemoryAddress
                if gNextMemoryLocation ~= 0 then
                    lNextMemoryAddress = gNextMemoryLocation
                else
                    lNextMemoryAddress = gMemoryLocation + 1
                    if lNextMemoryAddress > 100 then
                        lNextMemoryAddress = 1
                    end
                end
        
                if gMathVariables.mDepth > 1 then
                    if gMemLoc[lNextMemoryAddress].Calc1_Stat and
                    gMemLoc[lNextMemoryAddress].Calc1_Math_Name == gMemorySlot.Calc1_Math_Name then
                        gMathVariables.mSameExpression = true
                    else
                        gMathVariables.mSameExpression = false
                        if gMathVariables.mDataCount - gIntermediateSampleBuffer.mCount < gMathVariables.mDepth then
                            gErrorQueue.Add(801)
                        end
                    end
                else
                   gMathVariables.mSameExpression = false
                end
            end
        
            -- Update satus word
            gSampleBuffer.mStatus[gSampleBufferIndex] = gStatusWord
        
            -- if Read? was used then print the values
            if gPrintEnable == true then
                PrintImmediate(gSampleBufferIndex)
            end
        
            -- Update trace buffer
            if gStateVariables.Trac_Cont == "NEXT" then
                if gStateVariables.Trac_Feed == "SENS1" then
                    UpdateTraceBuffer(gSampleBufferIndex)
                end
            end
            
            -- update status model
            UpdateStatusModel()
        
            -- update next memory location address
            if gNextMemoryLocation ~= 0 then
                -- gMemoryLocation is incremented at the end so subtract 1
                gMemoryLocation = gNextMemoryLocation - 1
                -- We do not need to update gMemorySlot here because that will be done
                -- by the caller after this function returns.
            end
            if gCalc2BufferIndex >= 2500 then
                gCalc2BufferIndex = 0
            end
        
            -- Max number of readings stored in the sample buffer is 2500
            -- Reset the buffer pointer to 0 when greater than 2500
            if gSampleBufferIndex >= 2500 then
                gSampleBufferIndex = 0
            end
        
            -- Update next buffer location
            gSampleBufferIndex = gSampleBufferIndex + 1
        end
        
        --[[
            SourceMemorySweep simulates the trigger model for the source memory sweeps
            lStartLocation      -> Starting point of the sweep
            lSourceMemoryPoints -> Number of sweep points
            lArmCount           -> Arm count
            lTriggerCount       -> Trigger count
        --]]
        
        local gTriggerFunctions =
        {
            -- Arm Layer
            ["IMM"] =   function ()
                            return true
                        end,
            ["TLIN"] =  function ()
                            return gAbortExecuted or gTriggerLines[gStateVariables.Arm_Ilin].wait(100e-3)
                        end,
            ["MAN"] =   function ()
                            return gAbortExecuted or display.trigger.wait(100e-3)
                        end,
            ["BUS"] =   function ()
                            local lTrgExecuted = gTrgExecuted
                            gTrgExecuted = false
                            return gAbortExecuted or lTrgExecuted
                        end,
            ["TIM"] =   function ()
                            delay(gStateVariables.Arm_Tim)
                            return true
                        end,
            ["NST"] =   function ()
                            return gAbortExecuted or gStartOfTest.wait(100e-3)
                        end,
            -- Trigger Layer
            ["$TLIN"] =  function ()
                            return gAbortExecuted or gTriggerLines[gStateVariables.Trig_Ilin].wait(100e-3)
                        end,
        }
        gTriggerFunctions["PST"] = gTriggerFunctions["NST"]
        gTriggerFunctions["BST"] = gTriggerFunctions["NST"]
        local gTriggerSetup =
        {
            ["IMM"] =   function ()
                            return false
                        end,
            ["TLIN"] =  function ()
                            return true
                        end,
            ["NST"] =   function ()
                            gStartOfTest.mode = digio.TRIG_FALLING
                            return true
                        end,
            ["PST"] =   function ()
                            gStartOfTest.mode = digio.TRIG_RISING
                            return true
                        end,
            ["BST"] =   function ()
                            gStartOfTest.mode = digio.TRIG_EITHER
                            return true
                        end,
        }
        gTriggerFunctions["MAN"] = gTriggerFunctions["IMM"]
        gTriggerFunctions["BUS"] = gTriggerFunctions["IMM"]
        gTriggerFunctions["TIM"] = gTriggerFunctions["IMM"]
        
        
        local SourceMemorySweep = function (lStart, lSourceMemoryPoints, lArmCount, lTriggerCount)
            local lSweepPoints = lSourceMemoryPoints
            local lTrigger
            local lArmTrigger
            local lArmTriggerNext
            local lTriggerOutEnter
            local lTriggerOutExit
            local lTriggerOutSource
            local lTriggerOutDelay
            local lTriggerOutSense
            local lWaitForSource
            local lWaitForDelay
            local lWaitForSense
            local lBypass
            local lIteratedOverAllPoints = false
            local lFunctionChange = false
        
            gMemoryLocation = lStart
            gMemorySlot = gMemLoc[gMemoryLocation]
            -- Set up arm triggering
            lArmTriggerNext = gTriggerFunctions[gStateVariables.Arm_Sour]
            if gTriggerSetup[gStateVariables.Arm_Sour]() and gStateVariables.Arm_Dir == "SOUR" then
                -- In source direction, bypass the first time through if it is
                -- bypassable. (The setup function returns true if it is bypassable.)
                lArmTrigger = gTriggerFunctions["IMM"]
            else
                lArmTrigger = lArmTriggerNext
            end
        
            -- Set up triggering
            lWaitForSource = false
            lWaitForDelay = false
            lWaitForSense = false
            lBypass = false
            if gStateVariables.Trig_Sour == "TLIN" then
                lTrigger = gTriggerFunctions["$TLIN"]
                if gStateVariables.Trig_Inp == "SOUR" then
                    lWaitForSource = true
                elseif gStateVariables.Trig_Inp == "DEL" then
                    lWaitForDelay = true
                elseif gStateVariables.Trig_Inp == "SENS" then
                    lWaitForSense = true
                end
            else
                lTrigger = gTriggerFunctions["IMM"]
            end
            if gStateVariables.Arm_Outp.TENT then
                lTriggerOutEnter = gTriggerLines[gStateVariables.Arm_Olin].assert
            else
                lTriggerOutEnter = NullFunction
            end
            if gStateVariables.Arm_Outp.TEX then
                lTriggerOutExit = gTriggerLines[gStateVariables.Arm_Olin].assert
            else
                lTriggerOutExit = NullFunction
            end
            if gStateVariables.Trig_Outp.SOUR then
                lTriggerOutSource = gTriggerLines[gStateVariables.Trig_Olin].assert
            else
                lTriggerOutSource = NullFunction
            end
            if gStateVariables.Trig_Outp.DEL then
                lTriggerOutDelay = gTriggerLines[gStateVariables.Trig_Olin].assert
            else
                lTriggerOutDelay = NullFunction
            end
            if gStateVariables.Trig_Outp.SENS then
                lTriggerOutSense = gTriggerLines[gStateVariables.Trig_Olin].assert
            else
                lTriggerOutSense = NullFunction
            end
        
            -- Arm Layer
            while true do
                -- Operation Condition Register Bit 7(6 on 2400), Waiting for Arm
                StatusModel.SetCondition(operStatus, 7)
        
                -- Wait for arm trigger
                WaitForEvent(lArmTrigger)
                lArmTrigger = lArmTriggerNext
        
                -- Operation Condition Register Bit 7(6 on 2400), Waiting for Arm
                StatusModel.ClearCondition(operStatus, 7)
                
            -- Trigger Layer
                --TENTer(Entering trigger layer)
                lTriggerOutEnter()
                -- Check if an abort command was received. It will have been checked
                -- when waiting for triggers above.
                if gAbortExecuted then
                    return
                end
        
                if lWaitForSource and gStateVariables.Trig_Dir == "SOUR" then
                    lBypass = true
                end
                for lTriggerPoint = 1, lTriggerCount do
                    -- Source Event Detector
                    if lWaitForSource then
                        --check for source event detector bypass conditions and bypass the event detector once
                        if lBypass then
                            -- bypass the source event detector once
                            lBypass = false
                            PriorityExecute()
                        else
                            -- Set Operation Condition Register Bit 6(5 on 2400), Waiting for Trigger
                            StatusModel.SetCondition(operStatus, 6)
                            WaitForEvent(lTrigger)
                            -- Clear Operation Condition Register Bit 6(5 on 2400), Waiting for Trigger
                            StatusModel.ClearCondition(operStatus, 6)
                        end
                    else
                        PriorityExecute()
                    end
        
                    -- Check if an abort command was received
                    if gAbortExecuted then
                        return
                    end
                    
                     -- Trigger Delay
                    delay(gMemorySlot.Trig_Del)
                    
                    -- Set the source level to zero before the next point unless it is the last point
                    if gMemorySlot.Sour_Func_Mode ~= smua_GetSrcFunc() then
                        smua_SetSrcLevI(0)
                        smua_SetSrcLevV(0)
                        lFunctionChange = true
                    else
                        lFunctionChange = false
                    end
        
                    -- Measurement NPLC
                    if gMathAbs(gMemorySlot.Sens_Nplc/gAccessors.mGetMeasureNplc()- 1) >= gEpsilon then
                        gAccessors.mSetMeasureNplc(gMemorySlot.Sens_Nplc)
                    end
        
                    -- Autozero
                    gAccessors.mSetMeasureAutoZero(gMemorySlot.Syst_Azer_Stat)
                    -- Sense Mode 4W or 2W
                    gAccessors.mSetSense(gMemorySlot.Syst_Rsen)
                                
                    -- Algorithm for the order of setting limits, ranges
                    if gMemorySlot.Sour_Func_Mode == gDCAMPS then
                        if gMathAbs(smua_GetSrcLimV()/gMemorySlot.Sens_Volt_Prot) - 1 >= gEpsilon then
                            UpdateVoltageProtectionLevel(gMemorySlot)
                            UpdateSourceCurrentRange(gMemorySlot)   
                            if not lFunctionChange then 
                                UpdateSourceCurrentLevel(gMemorySlot, lTriggerPoint) 
                            end               
                        elseif gMathAbs(smua_GetSrcRngI()/gMemorySlot.Sour_Curr_Rang) - 1 >= gEpsilon
                        or gMemorySlot.Sour_Curr_Rang_Auto == 1 then
                            UpdateSourceCurrentRange(gMemorySlot)
                            if not lFunctionChange then
                                UpdateSourceCurrentLevel(gMemorySlot, lTriggerPoint)
                            end
                            UpdateVoltageProtectionLevel(gMemorySlot)
                        else
                            UpdateVoltageProtectionLevel(gMemorySlot)
                            UpdateSourceCurrentRange(gMemorySlot) 
                            if not lFunctionChange then             
                                UpdateSourceCurrentLevel(gMemorySlot, lTriggerPoint)
                            end
                        end
                    else -- smua.OUTPUT_DCVOLTS
                        if  gMathAbs(smua_GetSrcLimI()/gMemorySlot.Sens_Curr_Prot) - 1 >= gEpsilon then
                            UpdateCurrentProtectionLevel(gMemorySlot)
                            UpdateSourceVoltageRange(gMemorySlot)
                            if not lFunctionChange then
                                UpdateSourceVoltageLevel(gMemorySlot, lTriggerPoint)
                            end
                        elseif gMathAbs(smua_GetSrcRngV()/gMemorySlot.Sour_Volt_Rang) - 1 >= gEpsilon
                        or gMemorySlot.Sour_Volt_Rang_Auto == 1 then
                            UpdateSourceVoltageRange(gMemorySlot)
                            if not lFunctionChange then 
                                UpdateSourceVoltageLevel(gMemorySlot, lTriggerPoint)
                            end
                            UpdateCurrentProtectionLevel(gMemorySlot)
                        else
                            UpdateCurrentProtectionLevel(gMemorySlot)
                            UpdateSourceVoltageRange(gMemorySlot)
                            if not lFunctionChange then 
                                UpdateSourceVoltageLevel(gMemorySlot, lTriggerPoint)
                            end
                        end
                    end
                    
                    -- Voltage Measurement Range
                    if gMemorySlot.Sens_Volt_Rang_Auto == 1 then
                        gAccessors.mSetMeasureAutoRangev(1)
                    else
                        smua_SetMeasRngV(gMemorySlot.Sens_Volt_Rang)
                    end
        
                    -- Current Measurement Range
                    if gMemorySlot.Sens_Curr_Rang_Auto == 1 then
                        gAccessors.mSetMeasureAutoRangei(1)
                    else
                        smua_SetMeasRngI(gMemorySlot.Sens_Curr_Rang)
                    end
        
                    -- Measurement Filter            
                    gAccessors.mSetFilterType(gMemorySlot.Sens_Aver_Tcon)
                    gAccessors.mSetFilterCount(gMemorySlot.Sens_Aver_Coun)
                    gAccessors.mSetFilterEnable(gMemorySlot.Sens_Aver_Stat)
        
                    -- Check if an abort command was received
                    PriorityExecute()
                    if gAbortExecuted then
                        return
                    end
                    
                    -- Source Function, levels
                    if lFunctionChange then
                        gAccessors.mSetSourceFunc(gMemorySlot.Sour_Func_Mode)
                        -- Update the source levels
                        if gMemorySlot.Sour_Func_Mode == gDCAMPS then  
                            UpdateSourceCurrentLevel(gMemorySlot, lTriggerPoint)
                        else
                            UpdateSourceVoltageLevel(gMemorySlot, lTriggerPoint)
                        end
                    end
                    
                    -- Turn ON the output when off.
                    if gStateVariables.Sour_Cle_Auto_State then
                        gAccessors.mSetSourceOutput(1)
                    end
        
                    lTriggerOutSource()
        
                    -- Delay Event detector
                    if lWaitForDelay then
                        -- Set Operation Condition Register Bit 6(5 on 2400), Waiting for Trigger
                        StatusModel.SetCondition(operStatus, 6)
                        WaitForEvent(lTrigger)
                        -- Clear Operation Condition Register Bit 6(5 on 2400), Waiting for Trigger
                        StatusModel.ClearCondition(operStatus, 6)
                    else
                        PriorityExecute()
                    end
        
                    -- Check if an abort command was received
                    if gAbortExecuted then
                        return
                    end
        
                    -- Source Delay
                    if gMemorySlot.Sour_Del_Auto then
                        gAccessors.mSetSourceDelay(smua.DELAY_AUTO)
                    elseif gMemorySlot.Sour_Del > 0 then
                        delay(gMemorySlot.Sour_Del)
                    end
        
                    lTriggerOutDelay()
        
                    -- Measuer Event detector
                    if lWaitForSense then
                        -- Set Operation Condition Register Bit 6(5 on 2400), Waiting for Trigger
                        StatusModel.SetCondition(operStatus, 6)
                        WaitForEvent(lTrigger)
                        -- Clear Operation Condition Register Bit 6(5 on 2400), Waiting for Trigger
                        StatusModel.ClearCondition(operStatus, 6)
                    else
                        PriorityExecute()
                    end
        
                    -- Check if an abort command was received
                    if gAbortExecuted then
                        return
                    end
        
                    -- Perform Measurements            
                    if gMemorySlot.Sens_Func_Any then
                        -- Make real measurement                
                        gAccessors.mMeasureiv(gSMCurrentBuffer, gSMVoltageBuffer)
                    else
                        -- Make quick measurement just to capture buffer data such
                        -- as source value, timestamp, and status.
                        gAccessors.mSetMeasureAutoZero(smua.AUTOZERO_OFF)
                        gAccessors.mSetMeasureAutoRangei(0)
                        gAccessors.mSetMeasureNplc(0.001)
                        gAccessors.mMeasurei(gSMCurrentBuffer)               
                        gAccessors.mSetMeasureNplc(gMemorySlot.Sens_Nplc)
                        if gMemorySlot.Sens_Curr_Rang_Auto == 1 then
                            gAccessors.mSetMeasureAutoRangei(1)
                        end
                        gAccessors.mSetMeasureAutoZero(gMemorySlot.Syst_Azer_Stat)
                    end
        
                    lTriggerOutSense()
        
                    if gStateVariables.Sour_Cle_Auto_State then
                        gAccessors.mSetSourceOutput(0)
                    end
        
                    ProcessSourceMemoryData()
        
                    -- Track the points in the sweep
                    lSweepPoints = lSweepPoints - 1
                    -- wrap memory location to 1 after 100
                    if gMemoryLocation >= 100 then
                        gMemoryLocation = 0
                    end
                    -- wrap memory location to startlocation after sorce memory points
                    if lSweepPoints == 0 then
                        lIteratedOverAllPoints = true
                        gMemoryLocation = lStart - 1
                        lSweepPoints = lSourceMemoryPoints
                    end
                    -- Increment memory location
                    gMemoryLocation = gMemoryLocation + 1
                    gMemorySlot = gMemLoc[gMemoryLocation]
                end
        
                -- Update End binning control signal here
                if gCalculate2.mLimits and gStateVariables.Calc2_Clim_Mode == "GRAD" and
                gStateVariables.Calc2_Clim_Bcon == "END" and lIteratedOverAllPoints then
                    UpdateSourceMemorySweepGradingEndBinnig(gMemorySlot)
                    lIteratedOverAllPoints = false
                    gProcessedAtleastOneLimit = false
                end
        
                -- TEXit(Exiting trigger layer)
                lTriggerOutExit()
        
                if lArmCount ~= 0 then
                    lArmCount = lArmCount - 1
                    if lArmCount == 0 then
                        break
                    end
                end
            end
        end
        
        --[[
            InitiateSourceMemorySweep initiates the sourcememory sweeps and runs the simulated
            sourcememory sweep trigger model by calling SourceMemorySweep function
        --]]
        
        InitiateSourceMemorySweep = function (lStartLocation, lSourceMemoryPoints, lArmCount, lTriggerCount)
        
            ClearBuffer(gSampleBuffer)
            ClearBuffer(gCalculate2Buffer)
            ClearBuffer(gCalculate1Buffer)
        
            -- sample buffer Index
            gSampleBufferIndex = 1
            gMathVariables.mDataCount = 0
            gIntermediateSampleBuffer.mCount = 0
            gMathVariables.mSameExpression = false
            gSMCurrentBuffer.clear()
            gSMVoltageBuffer.clear()
            gLimitCapture.mFirstFailureLimit = 0
            gLimitCapture.mFirstFailureTest = 0
            gInsertComma = false
            gProcessedAtleastOneLimit = false
            
            -- Test if calc2 is enabled in any of the memory locations if yes then
            -- set the trigger stimulus for busy line when in busy mode
            if gStateVariables.Sour2_Ttl4_Mode == "BUSY" and
                    (gStateVariables.Arm_Sour == "NST" or gStateVariables.Arm_Sour == "PST" or
                    gStateVariables.Arm_Sour == "BST") then
                local lTestLocation = lStartLocation
                for i = 1, lSourceMemoryPoints do
                    if gMemLoc[lTestLocation].Calc2Limits then
                        gEndOfTest.stimulus = gStartOfTest.EVENT_ID
                        break
                    end
                    if lTestLocation == 100 then
                       lTestLocation = 0
                    end
                    lTestLocation = lTestLocation + 1
                end
            end
        
            -- Operation Condition Register Bit 4(3 on 2400), Sweeping
            StatusModel.SetCondition(operStatus, 4)
            -- Clear Operation Condition Register Bit 11(10 on 2400), In idle state
            StatusModel.ClearCondition(operStatus, 11)
        
            -- Run sourcememory sweep
            SourceMemorySweep(lStartLocation, lSourceMemoryPoints, lArmCount, lTriggerCount)
        
            -- Operation Condition Register Bit 11(10 on 2400), In idle state
            StatusModel.SetCondition(operStatus, 11)
            -- Clear Operation Condition Register Bit 4(3 on 2400), Sweeping
            StatusModel.ClearCondition(operStatus, 4)
        
            -- Check if an abort command was received
            PriorityExecute()
            if gAbortExecuted then
                return
            end
            
            --release the busy line
            if gStateVariables.Sour2_Ttl4_Mode == "BUSY" and
            (gStateVariables.Arm_Sour == "NST" or gStateVariables.Arm_Sour == "PST" or
            gStateVariables.Arm_Sour == "BST") then
                gEndOfTest.release()
                gEndOfTest.stimulus = 0
            end
        
            -- if system clock auto reset enable get the offset
            if gStateVariables.Syst_Time_Res_Auto and gStateVariables.Trac_Cont ~= "NEXT" then
               gSystemClockOffset = gSMCurrentBuffer.basetimestamp
            end
        end
        
        --[[
            RecallSourceMemoryLocation recalls the memory location settings
            MemLoc -> memory location to recall
        --]]
        local RecallSourceMemoryLocation = function (lMemoryLocation)
            for lKey, lValue in pairs(gMemLoc[lMemoryLocation]) do
                lMemScratch[lKey] = lValue
            end
            --loads the memory location
            LoadSourceMemoryLocation(lMemoryLocation)
        end
        
        --[[
            SaveSourceMemoryLocation saves the smu setup to the memory location
            MemLoc -> memory location to save
        --]]
        local SaveSourceMemoryLocation = function (lMemoryLocation)
            local lMemorySlot = gMemLoc[lMemoryLocation]
            
            for lKey, lValue in pairs(lMemScratch) do
                lMemorySlot[lKey] = lValue
            end
            if lMemorySlot.Calc2_Lim1_Stat or
                    lMemorySlot.Calc2_Lim2_Stat or
                    lMemorySlot.Calc2_Lim3_Stat or
                    lMemorySlot.Calc2_Lim5_Stat or
                    lMemorySlot.Calc2_Lim6_Stat or
                    lMemorySlot.Calc2_Lim7_Stat or
                    lMemorySlot.Calc2_Lim8_Stat or
                    lMemorySlot.Calc2_Lim9_Stat or
                    lMemorySlot.Calc2_Lim10_Stat or
                    lMemorySlot.Calc2_Lim11_Stat or
                    lMemorySlot.Calc2_Lim12_Stat then
                lMemorySlot.Calc2Limits = true
            else
                lMemorySlot.Calc2Limits = false
            end
        end
        
        
        ------------------------------------------------------------------------------
        -- 2600 trigger model sweeps related functions
        --[[
            Prepare the smu to run trigger model sweeps, process data for storing and
            limit testing.
        --]]
        ------------------------------------------------------------------------------
        
        --[[
            ProcessCalc2Data performs limit testing for trigger model sweeps
        --]]
        
        local ProcessCalc2Data = function (i)
            -- when 1 in sorting mode terminate the current test
            local lDutSorted = 0
            local lDutGraded = 0
        
            gProcessedAtleastOneLimit = true
            -- Reset all the results for the new test
            gStateVariables.Calc2_Lim1_Result = 0
            for x = 2, 12 do
                -- 4 is not used but it is cheaper to just set it to 0
                gStateVariables.Calc2_Lim_Result[x] = 0
            end
        
            -- Sorting mode
            if gStateVariables.Calc2_Clim_Mode == "SORT" then
                if gStateVariables.Calc2_Lim1_Stat then
                    -- perform compliance testing
                    gLimitCapture.mFailedLimit = 0
                    if (bit.bitand(gCurrentBuffer.statuses[i], 64) == 64 and gStateVariables.Calc2_Lim1_Fail == "IN") or
                            (bit.bitand(gCurrentBuffer.statuses[i], 64) ~= 64 and gStateVariables.Calc2_Lim1_Fail == "OUT") then
                        gStateVariables.Calc2_Lim1_Result = 1
                        -- Measurement Condition Register Bit 1(0 on 2400), Limit1 Fail
                        StatusModel.SetCondition(measStatus, 1)
                        UpdateDigOut(gStateVariables.Calc2_Lim1_Sour2)
                        UpdateEOT()
                        lDutSorted = 1
                        -- stauts Bit 8, Limit Results
                        gStatusWord = gStatusWord + 256
                    else
                        -- used if only limit 1 is enabled
                        lDutSorted = 2
                    end
                end
                if gStateVariables.Calc2_Lim_Stat[2] and lDutSorted ~= 1 then
                    TestCalc2Limits(2, i)
                    if gStateVariables.Calc2_Lim_Result[2] == 0 then
                        UpdateDigOut(gStateVariables.Calc2_Lim_Pass_Sour2[2])
                        UpdateEOT()
                        lDutSorted = 1
                        -- stauts Bit 9, Limit Results
                        gStatusWord = gStatusWord + 512
                    else
                        lDutSorted = 3
                    end
                end
                if gStateVariables.Calc2_Lim_Stat[3] and lDutSorted ~= 1 then
                    TestCalc2Limits(3, i)
                    if gStateVariables.Calc2_Lim_Result[3] == 0 then
                        UpdateDigOut(gStateVariables.Calc2_Lim_Pass_Sour2[3])
                        UpdateEOT()
                        lDutSorted = 1
                        -- stauts Bit 8,9, Limit Results
                        gStatusWord = gStatusWord + 768
                    else
                        lDutSorted = 3
                    end
                end
                if gStateVariables.Calc2_Lim_Stat[5] and lDutSorted ~= 1 then
                    TestCalc2Limits(5, i)
                    if gStateVariables.Calc2_Lim_Result[5] == 0 then
                        UpdateDigOut(gStateVariables.Calc2_Lim_Pass_Sour2[5])
                        UpdateEOT()
                        lDutSorted = 1
                        -- stauts Bit 19, Limit Results
                        gStatusWord = gStatusWord + 524288
                    else
                        lDutSorted = 3
                    end
                end
        
                if gStateVariables.Calc2_Lim_Stat[6] and lDutSorted ~= 1 then
                    TestCalc2Limits(6, i)
                    if gStateVariables.Calc2_Lim_Result[6] == 0 then
                        UpdateDigOut(gStateVariables.Calc2_Lim_Pass_Sour2[6])
                        UpdateEOT()
                        lDutSorted = 1
                        -- stauts Bit 9,19, Limit Results
                        gStatusWord = gStatusWord + 524800
                    else
                        lDutSorted = 3
                    end
                end
                if gStateVariables.Calc2_Lim_Stat[7] and lDutSorted ~= 1 then
                    TestCalc2Limits(7, i)
                    if gStateVariables.Calc2_Lim_Result[7] == 0 then
                        UpdateDigOut(gStateVariables.Calc2_Lim_Pass_Sour2[7])
                        UpdateEOT()
                        lDutSorted = 1
                        -- stauts Bit 8,9,19, Limit Results
                        gStatusWord = gStatusWord + 525056
                    else
                        lDutSorted = 3
                    end
                end
                if gStateVariables.Calc2_Lim_Stat[8] and lDutSorted ~= 1 then
                    TestCalc2Limits(8, i)
                    if gStateVariables.Calc2_Lim_Result[8] == 0 then
                        UpdateDigOut(gStateVariables.Calc2_Lim_Pass_Sour2[8])
                        UpdateEOT()
                        lDutSorted = 1
                        -- stauts Bit 20, Limit Results
                        gStatusWord = gStatusWord + 1048576
                    else
                        lDutSorted = 3
                    end
                end
                if gStateVariables.Calc2_Lim_Stat[9] and lDutSorted ~= 1 then
                    TestCalc2Limits(9, i)
                    if gStateVariables.Calc2_Lim_Result[9] == 0 then
                        UpdateDigOut(gStateVariables.Calc2_Lim_Pass_Sour2[9])
                        UpdateEOT()
                        lDutSorted = 1
                        -- stauts Bit 8,20, Limit Results
                        gStatusWord = gStatusWord + 1048832
                    else
                        lDutSorted = 3
                    end
                end
                if gStateVariables.Calc2_Lim_Stat[10] and lDutSorted ~= 1 then
                    TestCalc2Limits(10, i)
                    if gStateVariables.Calc2_Lim_Result[10] == 0 then
                        UpdateDigOut(gStateVariables.Calc2_Lim_Pass_Sour2[10])
                        UpdateEOT()
                        lDutSorted = 1
                        -- stauts Bit 9,20, Limit Results
                        gStatusWord = gStatusWord + 1049088
                    else
                        lDutSorted = 3
                    end
                end
                if gStateVariables.Calc2_Lim_Stat[11] and lDutSorted ~= 1 then
                    TestCalc2Limits(11, i)
                    if gStateVariables.Calc2_Lim_Result[11] == 0 then
                        UpdateDigOut(gStateVariables.Calc2_Lim_Pass_Sour2[11])
                        UpdateEOT()
                        lDutSorted = 1
                        -- stauts Bit 8,9,20, Limit Results
                        gStatusWord = gStatusWord + 1049344
                    else
                        lDutSorted = 3
                    end
                end
                if gStateVariables.Calc2_Lim_Stat[12] and lDutSorted ~= 1 then
                    TestCalc2Limits(12, i)
                    if gStateVariables.Calc2_Lim_Result[12] == 0 then
                        UpdateDigOut(gStateVariables.Calc2_Lim_Pass_Sour2[12])
                        UpdateEOT()
                        lDutSorted = 1
                        -- stauts Bit 19,20, Limit Results
                        gStatusWord = gStatusWord + 1572864
                    else
                        lDutSorted = 3
                    end
                end
                -- Test failed or only Limit 1 was enabled
                if lDutSorted ~= 1 then
                    if lDutSorted == 0 or lDutSorted == 3 then
                        UpdateDigOut(gStateVariables.Calc2_Clim_Fail_Sour2)
                        -- stauts Bit 8,9,19,20, Limit Results
                        gStatusWord = gStatusWord + 1573632
                    elseif lDutSorted == 2 then
                        UpdateDigOut(gStateVariables.Calc2_Clim_Pass_Sour2)           
                    end
                    UpdateEOT()
                elseif gStateVariables.Calc2_Lim1_Result == 0 then
                    -- Measurement Condition Register Bit 6(5 on 2400), Limits Pass
                    StatusModel.SetCondition(measStatus, 6)
                end
        
            -- Grading mode, Immediate binning
            elseif gStateVariables.Calc2_Clim_Mode == "GRAD" then
                if gStateVariables.Calc2_Clim_Bcon == "IMM" then
                    if gStateVariables.Calc2_Lim1_Stat then
                        -- perform compliance testing
                        gLimitCapture.mFailedLimit = 0
                        if (bit.bitand(gCurrentBuffer.statuses[i], 64) == 64 and gStateVariables.Calc2_Lim1_Fail == "IN") or
                                (bit.bitand(gCurrentBuffer.statuses[i], 64) ~= 64 and gStateVariables.Calc2_Lim1_Fail == "OUT") then
                            gStateVariables.Calc2_Lim1_Result = 1
                            -- Measurement Condition Register Bit 1(0 on 2400), Limit1 Fail
                            StatusModel.SetCondition(measStatus, 1)
                            UpdateDigOut(gStateVariables.Calc2_Lim1_Sour2)
                            UpdateEOT()
                            lDutGraded = 1
                            -- stauts Bit 8, Limit Results
                            gStatusWord = gStatusWord + 256
                        end
                    end
                    if gStateVariables.Calc2_Lim_Stat[2] and lDutGraded ~= 1 then
                        TestCalc2Limits(2, i)
                        if gStateVariables.Calc2_Lim_Result[2] == 1 then
                            if gLimitCapture.mFailedLimit == "Upper" then
                                -- Measurement Condition Register Bit 3(2 on 2400), High Limit2 Fail
                                StatusModel.SetCondition(measStatus, 3)
                                UpdateDigOut(gStateVariables.Calc2_Lim_Upp_Sour2[2])
                                -- stauts Bit 21, Limit Results
                                gStatusWord = gStatusWord + 2097664
                            elseif gLimitCapture.mFailedLimit == "Lower" then
                                -- Measurement Condition Register Bit 2(1 on 2400), Low Limit2 Fail
                                StatusModel.SetCondition(measStatus, 2)
                                UpdateDigOut(gStateVariables.Calc2_Lim_Low_Sour2[2])
                                -- stauts Bit 9, Limit Results
                                gStatusWord = gStatusWord + 512
                            end
                            UpdateEOT()
                            lDutGraded = 1
                        end
                    end
                    if gStateVariables.Calc2_Lim_Stat[3] and lDutGraded ~= 1 then
                        TestCalc2Limits(3, i)
                        if gStateVariables.Calc2_Lim_Result[3] == 1 then
                            if gLimitCapture.mFailedLimit == "Upper" then
                                -- Measurement Condition Register Bit 5(4 on 2400), High Limit3 Fail
                                StatusModel.SetCondition(measStatus, 5)
                                UpdateDigOut(gStateVariables.Calc2_Lim_Upp_Sour2[3])
                                -- stauts Bit 8,9,21, Limit Results
                                gStatusWord = gStatusWord + 2097920
                            elseif gLimitCapture.mFailedLimit == "Lower" then
                                -- Measurement Condition Register Bit 4(3 on 2400), Low Limit3 Fail
                                StatusModel.SetCondition(measStatus, 4)
                                UpdateDigOut(gStateVariables.Calc2_Lim_Low_Sour2[3])
                                -- stauts Bit 8,9, Limit Results
                                gStatusWord = gStatusWord + 768
                            end
                            UpdateEOT()
                            lDutGraded = 1
                        end
                    end
                    if gStateVariables.Calc2_Lim_Stat[5] and lDutGraded ~= 1 then
                        TestCalc2Limits(5, i)
                        if gStateVariables.Calc2_Lim_Result[5] == 1 then
                            if gLimitCapture.mFailedLimit == "Upper" then
                                UpdateDigOut(gStateVariables.Calc2_Lim_Upp_Sour2[5])
                                -- stauts Bit 19,21, Limit Results
                                gStatusWord = gStatusWord + 2621440
                            elseif gLimitCapture.mFailedLimit == "Lower" then
                                UpdateDigOut(gStateVariables.Calc2_Lim_Low_Sour2[5])
                                -- stauts Bit 19, Limit Results
                                gStatusWord = gStatusWord + 524288
                            end
                            UpdateEOT()
                            lDutGraded = 1
                        end
                    end
        
                    if gStateVariables.Calc2_Lim_Stat[6] and lDutGraded ~= 1 then
                        TestCalc2Limits(6, i)
                        if gStateVariables.Calc2_Lim_Result[6] == 1 then
                            if gLimitCapture.mFailedLimit == "Upper" then
                                UpdateDigOut(gStateVariables.Calc2_Lim_Upp_Sour2[6])
                                -- stauts Bit 9,19,21, Limit Results
                                gStatusWord = gStatusWord + 2621952
                            elseif gLimitCapture.mFailedLimit == "Lower" then
                                UpdateDigOut(gStateVariables.Calc2_Lim_Low_Sour2[6])
                                -- stauts Bit 9,19, Limit Results
                                gStatusWord = gStatusWord + 524800
                            end
                            UpdateEOT()
                            lDutGraded = 1
                        end
                    end
                    if gStateVariables.Calc2_Lim_Stat[7] and lDutGraded ~= 1 then
                        TestCalc2Limits(7, i)
                        if gStateVariables.Calc2_Lim_Result[7] == 1 then
                            if gLimitCapture.mFailedLimit == "Upper" then
                                UpdateDigOut(gStateVariables.Calc2_Lim_Upp_Sour2[7])
                                -- stauts Bit 8,9,19,21, Limit Results
                                gStatusWord = gStatusWord + 2622208
                            elseif gLimitCapture.mFailedLimit == "Lower" then
                                UpdateDigOut(gStateVariables.Calc2_Lim_Low_Sour2[7])
                                -- stauts Bit 8,9,19, Limit Results
                                gStatusWord = gStatusWord + 525056
                            end
                            UpdateEOT()
                            lDutGraded = 1
                        end
                    end
                    if gStateVariables.Calc2_Lim_Stat[8] and lDutGraded ~= 1 then
                        TestCalc2Limits(8, i)
                        if gStateVariables.Calc2_Lim_Result[8] == 1 then
                            if gLimitCapture.mFailedLimit == "Upper" then
                                UpdateDigOut(gStateVariables.Calc2_Lim_Upp_Sour2[8])
                                -- stauts Bit 20,21, Limit Results
                                gStatusWord = gStatusWord + 3145728
                            elseif gLimitCapture.mFailedLimit == "Lower" then
                                UpdateDigOut(gStateVariables.Calc2_Lim_Low_Sour2[8])
                                -- stauts Bit 20, Limit Results
                                gStatusWord = gStatusWord + 1048576
                            end
                            UpdateEOT()
                            lDutGraded = 1
                        end
                    end
                    if gStateVariables.Calc2_Lim_Stat[9] and lDutGraded ~= 1 then
                        TestCalc2Limits(9, i)
                        if gStateVariables.Calc2_Lim_Result[9] == 1 then
                            if gLimitCapture.mFailedLimit == "Upper" then
                                UpdateDigOut(gStateVariables.Calc2_Lim_Upp_Sour2[9])
                                -- stauts Bit 8,20,21, Limit Results
                                gStatusWord = gStatusWord + 3145984
                            elseif gLimitCapture.mFailedLimit == "Lower" then
                                UpdateDigOut(gStateVariables.Calc2_Lim_Low_Sour2[9])
                                -- stauts Bit 8,20, Limit Results
                                gStatusWord = gStatusWord + 1048832
                            end
                            UpdateEOT()
                            lDutGraded = 1
                        end
                    end
                    if gStateVariables.Calc2_Lim_Stat[10] and lDutGraded ~= 1 then
                        TestCalc2Limits(10, i)
                        if gStateVariables.Calc2_Lim_Result[10] == 1 then
                            if gLimitCapture.mFailedLimit == "Upper" then
                                UpdateDigOut(gStateVariables.Calc2_Lim_Upp_Sour2[10])
                                -- stauts Bit 9,20,21, Limit Results
                                gStatusWord = gStatusWord + 3146240
                            elseif gLimitCapture.mFailedLimit == "Lower" then
                                UpdateDigOut(gStateVariables.Calc2_Lim_Low_Sour2[10])
                                -- stauts Bit 9,20, Limit Results
                                gStatusWord = gStatusWord + 1049088
                            end
                            UpdateEOT()
                            lDutGraded = 1
                        end
                    end
                    if gStateVariables.Calc2_Lim_Stat[11] and lDutGraded ~= 1 then
                        TestCalc2Limits(11, i)
                        if gStateVariables.Calc2_Lim_Result[11] == 1 then
                            if gLimitCapture.mFailedLimit == "Upper" then
                                UpdateDigOut(gStateVariables.Calc2_Lim_Upp_Sour2[11])
                                -- stauts Bit 8,9,20,21, Limit Results
                                gStatusWord = gStatusWord + 3146496
                            elseif gLimitCapture.mFailedLimit == "Lower" then
                                UpdateDigOut(gStateVariables.Calc2_Lim_Low_Sour2[11])
                                -- stauts Bit 8,9,20, Limit Results
                                gStatusWord = gStatusWord + 1049344
                            end
                            UpdateEOT()
                            lDutGraded = 1
                        end
                    end
                    if gStateVariables.Calc2_Lim_Stat[12] and lDutGraded ~= 1 then
                        TestCalc2Limits(12, i)
                        if gStateVariables.Calc2_Lim_Result[12] == 1 then
                            if gLimitCapture.mFailedLimit == "Upper" then
                                UpdateDigOut(gStateVariables.Calc2_Lim_Upp_Sour2[12])
                                -- stauts Bit 19,20,21, Limit Results
                                gStatusWord = gStatusWord + 3670016
                            elseif gLimitCapture.mFailedLimit == "Lower" then
                                UpdateDigOut(gStateVariables.Calc2_Lim_Low_Sour2[12])
                                -- stauts Bit 19,20, Limit Results
                                gStatusWord = gStatusWord + 1572864
        
                            end
                            UpdateEOT()
                            lDutGraded = 1
                        end
                    end
                    -- All tests passed
                    if lDutGraded ~= 1 then
                        -- Measurement Condition Register Bit 6(5 on 2400), Limits Pass
                        StatusModel.SetCondition(measStatus, 6)
                        UpdateDigOut(gStateVariables.Calc2_Clim_Pass_Sour2)
                        UpdateEOT()
                    end
        
                -- Grading mode, End binning
                elseif gStateVariables.Calc2_Clim_Bcon == "END" then
                    if gStateVariables.Calc2_Lim1_Stat then
                        -- perform compliance testing
                        gLimitCapture.mFailedLimit = 0
                        if (bit.bitand(gCurrentBuffer.statuses[i], 64) == 64 and gStateVariables.Calc2_Lim1_Fail == "IN") or
                                (bit.bitand(gCurrentBuffer.statuses[i], 64) ~= 64 and gStateVariables.Calc2_Lim1_Fail == "OUT") then
                            gStateVariables.Calc2_Lim1_Result = 1
                            -- Measurement Condition Register Bit 1(0 on 2400), Limit1 Fail
                            StatusModel.SetCondition(measStatus, 1)
                            lDutGraded = 1
                            if gLimitCapture.mFirstFailureTest == 0 then
                                gLimitCapture.mFirstFailureLimit = "Comp"
                                gLimitCapture.mFirstFailureTest = "Comp"
                            end
                            -- stauts Bit 8, Limit Results
                            gStatusWord = gStatusWord + 256
                        end
                    end
                    if gStateVariables.Calc2_Lim_Stat[2] and lDutGraded ~= 1 then
                        TestCalc2Limits(2, i)
                        if gStateVariables.Calc2_Lim_Result[2] == 1 then
                            if gLimitCapture.mFailedLimit == "Upper" then
                                -- Measurement Condition Register Bit 3(2 on 2400), High Limit2 Fail
                                StatusModel.SetCondition(measStatus, 3)
                                -- stauts Bit 9,21, Limit Results
                                gStatusWord = gStatusWord + 2097664
                            elseif gLimitCapture.mFailedLimit == "Lower" then
                                -- Measurement Condition Register Bit 2(1 on 2400), Low Limit2 Fail
                                StatusModel.SetCondition(measStatus, 2)
                                -- stauts Bit 9, Limit Results
                                gStatusWord = gStatusWord + 512
                            end
                            lDutGraded = 1
                        end
                    end
                    if gStateVariables.Calc2_Lim_Stat[3] and lDutGraded ~= 1 then
                        TestCalc2Limits(3, i)
                        if gStateVariables.Calc2_Lim_Result[3] == 1 then
                            if gLimitCapture.mFailedLimit == "Upper" then
                                -- Measurement Condition Register Bit 5(4 on 2400), High Limit3 Fail
                                StatusModel.SetCondition(measStatus, 5)
                                -- stauts Bit 8,9,21, Limit Results
                                gStatusWord = gStatusWord + 2097920
                            elseif gLimitCapture.mFailedLimit == "Lower" then
                                -- Measurement Condition Register Bit 4(3 on 2400), Low Limit3 Fail
                                StatusModel.SetCondition(measStatus, 4)
                                -- stauts Bit 8,9, Limit Results
                                gStatusWord = gStatusWord + 768
                            end
                            lDutGraded = 1
                        end
                    end
                    --if gStateVariables.Calc2_Lim_Stat[4] == 1 then
                        --TestCalc2Limits(4) end
                    if gStateVariables.Calc2_Lim_Stat[5] and lDutGraded ~= 1 then
                        TestCalc2Limits(5, i)
                        if gStateVariables.Calc2_Lim_Result[5] == 1 then
                            if gLimitCapture.mFailedLimit == "Upper" then
                                -- stauts Bit 19,21, Limit Results
                                gStatusWord = gStatusWord + 2621440
                            elseif gLimitCapture.mFailedLimit == "Lower" then
                                -- stauts Bit 19, Limit Results
                                gStatusWord = gStatusWord + 524288
                            end
                            lDutGraded = 1
                        end
                    end
                    if gStateVariables.Calc2_Lim_Stat[6] and lDutGraded ~= 1 then
                        TestCalc2Limits(6, i)
                        if gStateVariables.Calc2_Lim_Result[6] == 1 then
                            if gLimitCapture.mFailedLimit == "Upper" then
                                -- stauts Bit 9,19,21, Limit Results
                                gStatusWord = gStatusWord + 2621952
                            elseif gLimitCapture.mFailedLimit == "Lower" then
                                -- stauts Bit 9,19, Limit Results
                                gStatusWord = gStatusWord + 524800
                            end
                            lDutGraded = 1
                        end
                    end
                    if gStateVariables.Calc2_Lim_Stat[7] and lDutGraded ~= 1 then
                        TestCalc2Limits(7, i)
                        if gStateVariables.Calc2_Lim_Result[7] == 1 then
                            if gLimitCapture.mFailedLimit == "Upper" then
                                -- stauts Bit 8,9,19,21, Limit Results
                                gStatusWord = gStatusWord + 2622208
                            elseif gLimitCapture.mFailedLimit == "Lower" then
                                -- stauts Bit 8,9,19, Limit Results
                                gStatusWord = gStatusWord + 525056
                            end
                            lDutGraded = 1
                        end
                    end
                    if gStateVariables.Calc2_Lim_Stat[8] and lDutGraded ~= 1 then
                        TestCalc2Limits(8, i)
                        if gStateVariables.Calc2_Lim_Result[8] == 1 then
                            if gLimitCapture.mFailedLimit == "Upper" then
                                -- stauts Bit 20,21, Limit Results
                                gStatusWord = gStatusWord + 3145728
                            elseif gLimitCapture.mFailedLimit == "Lower" then
                                -- stauts Bit 20, Limit Results
                                gStatusWord = gStatusWord + 1048576
                            end
                            lDutGraded = 1
                        end
                    end
                    if gStateVariables.Calc2_Lim_Stat[9] and lDutGraded ~= 1 then
                        TestCalc2Limits(9, i)
                        if gStateVariables.Calc2_Lim_Result[9] == 1 then
                            if gLimitCapture.mFailedLimit == "Upper" then
                                -- stauts Bit 8,20,21, Limit Results
                                gStatusWord = gStatusWord + 3145984
                            elseif gLimitCapture.mFailedLimit == "Lower" then
                                -- stauts Bit 8,20, Limit Results
                                gStatusWord = gStatusWord + 1048832
                            end
                            lDutGraded = 1
                        end
                    end
                    if gStateVariables.Calc2_Lim_Stat[10] and lDutGraded ~= 1 then
                        TestCalc2Limits(10, i)
                        if gStateVariables.Calc2_Lim_Result[10] == 1 then
                            if gLimitCapture.mFailedLimit == "Upper" then
                                -- stauts Bit 9,20,21, Limit Results
                                gStatusWord = gStatusWord + 3146240
                            elseif gLimitCapture.mFailedLimit == "Lower" then
                                -- stauts Bit 9,20, Limit Results
                                gStatusWord = gStatusWord + 1049088
                            end
                            lDutGraded = 1
                        end
                    end
                    if gStateVariables.Calc2_Lim_Stat[11] and lDutGraded ~= 1 then
                        TestCalc2Limits(11, i)
                        if gStateVariables.Calc2_Lim_Result[11] == 1 then
                            if gLimitCapture.mFailedLimit == "Upper" then
                                -- stauts Bit 8,9,20,21, Limit Results
                                gStatusWord = gStatusWord + 3146496
                            elseif gLimitCapture.mFailedLimit == "Lower" then
                                -- stauts Bit 8,9,20, Limit Results
                                gStatusWord = gStatusWord + 1049344
                            end
                            lDutGraded = 1
                        end
                    end
                    if gStateVariables.Calc2_Lim_Stat[12] and lDutGraded ~= 1 then
                        TestCalc2Limits(12, i)
                        if gStateVariables.Calc2_Lim_Result[12] == 1 then
                            if gLimitCapture.mFailedLimit == "Upper" then
                                -- stauts Bit 19,20,21, Limit Results
                                gStatusWord = gStatusWord + 3670016
                            elseif gLimitCapture.mFailedLimit == "Lower" then
                                -- stauts Bit 19,20, Limit Results
                                gStatusWord = gStatusWord + 1572864
                            end
                            lDutGraded = 1
                        end
                    end
                end
            end
        end
        
        --[[
            Process Data processes the measurements for storing and limit testing.
        --]]
        
        local ProcessData = function ()
            local lSweepPoint = 1
            local lTriggerCount = gTrigger.count
            local lSweepPoints = gSweepPoints
            local lStaticStatusBits
            local lSweepStatus = status.operation.sweeping
            local lIteratedOverAllPoints = false
        
            gLimitCapture.mFirstFailureLimit = 0
            gLimitCapture.mFirstFailureTest = 0
            gInsertComma = false
            gMeasureCompleteTimer.clear()
            gProcessedAtleastOneLimit = false
        
            lStaticStatusBits = 0
            if gStateVariables.Calc1_Stat then
                -- status bit 5, Math
                lStaticStatusBits = lStaticStatusBits + 32
            end
            if gCalculate2.mNullOffset then
                -- stauts bit 6, Null
                lStaticStatusBits = lStaticStatusBits + 64
            end
            if gCalculate2.mLimits then
                -- stauts bit 7, Limits
                lStaticStatusBits = lStaticStatusBits + 128
            end
        
            while bit.test(lSweepStatus.condition, 2) do
                for i = 1, lTriggerCount do
                    -- trigger.generator[1] is used as the software trigger
                    gTriggerGenerator.assert()
        
                    UpdateStatusModel()
                    PriorityExecute()
                    if gAbortExecuted then
                        return
                    end
        
                    -- reset gStatusWord for the next set of readings
                    gStatusWord = lStaticStatusBits
        
                    -- clear measurement status condition register
                    measStatus.mCondition = 0
        
                    -- update sample buffer
                    UpdateSampleBuffer(lSweepPoint)
                    if gAbortExecuted then
                        return
                    end
        
                    -- Process Calc2 Limit tests and Null offset
                    if gStateVariables.Calc2_Feed ~= "CALC1" then
                        -- update calc2 buffer
                        if gCalculate2.mLimits or gCalculate2.mNullOffset then
                            UpdateCalc2Buffer(lSweepPoint)
        
                            -- perform limit tests
                            if gCalculate2.mLimits then
                                ProcessCalc2Data(lSweepPoint)
                            end
        
                            gCalculate2Buffer.mStatus[lSweepPoint] = gStatusWord
                            -- Update trace buffer
                            if gStateVariables.Trac_Cont == "NEXT" then
                                if gStateVariables.Trac_Feed == "CALC2" then
                                    UpdateTraceBuffer(lSweepPoint)
                                end
                            end
                        end
                    end
        
                    -- Process Calc1 equations
                    if gStateVariables.Calc1_Stat then
                        UpdateIntermediateSampleBuffer(lSweepPoint)
                        if gIntermediateSampleBuffer.mCount == gMathVariables.mDataCount then
                            gCalculate1Buffer.mData[gCalc1BufferIndex] = gStateVariables.Calc1_Selected.mExpression.Evaluate()
                            gCalculate1Buffer.mTime[gCalc1BufferIndex] = gSampleBuffer.mTime[lSweepPoint]
        
                            -- Process Calc2 Limit tests and Null offset
                            if gStateVariables.Calc2_Feed == "CALC1" then
                                -- update calc2 buffer
                                if gCalculate2.mLimits or gCalculate2.mNullOffset then
                                    UpdateCalc2Buffer(gCalc1BufferIndex)
        
                                    -- perform limit tests
                                    if gCalculate2.mLimits then
                                        ProcessCalc2Data(gCalc1BufferIndex)
                                    end
        
                                    gCalculate2Buffer.mStatus[gCalc1BufferIndex] = gStatusWord
        
                                    -- Update Trace buffer
                                    if gStateVariables.Trac_Cont == "NEXT" then
                                        if gStateVariables.Trac_Feed == "CALC2" then
                                            UpdateTraceBuffer(gCalc1BufferIndex)
                                        end
                                    end
                                else
                                    gCalculate2Buffer.mStatus[gCalc1BufferIndex] = gStatusWord
                                end
                            end
        
                            gCalculate1Buffer.mStatus[gCalc1BufferIndex] = gStatusWord
        
                            -- Update Trace buffer
                            if gStateVariables.Trac_Cont == "NEXT" then
                                if gStateVariables.Trac_Feed == "CALC1" then
                                    UpdateTraceBuffer(gCalc1BufferIndex)
                                end
                            end
        
                            -- Reset the index and count to 0 when greater than 2500
                            if gCalc1BufferIndex >= 2500 then
                                gCalc1BufferIndex = 0
                                gCalculate1Buffer.mCount = 0
                            end
        
                            gCalc1BufferIndex = gCalc1BufferIndex + 1
                            gCalculate1Buffer.mCount = gCalculate1Buffer.mCount + 1
                            -- Update the Data count for next sample set
                            gMathVariables.mDataCount = gMathVariables.mDataCount + gMathVariables.mDepth
                        end
                    end
        
                    -- Update satus word
                    gSampleBuffer.mStatus[lSweepPoint] = gStatusWord
        
                    -- if Read? was used then print as the buffer is filled
                    if gPrintEnable == true then
                        PrintImmediate(lSweepPoint)
                    end
        
                    -- Update trace buffer data
                    -- patch this code and unpatch the others for speed
                    if gStateVariables.Trac_Cont == "NEXT" then
                        if gStateVariables.Trac_Feed == "SENS1" then
                           UpdateTraceBuffer(lSweepPoint)
                        end
                    end
        
                    -- Reset lSweepPoint to 0 when it exceeds 2500
                    if lSweepPoint >= 2500 then
                        lSweepPoint = 0
                    end
        
                    -- Increment the iterator for buffers
                    lSweepPoint = lSweepPoint + 1
        
                    -- Check if an abort command was received
                    PriorityExecute()
                    if gAbortExecuted then
                        return
                    end
        
                    -- Track the sweep points to update EOT signal
                    lSweepPoints = lSweepPoints - 1
                    if lSweepPoints <= 0 then
                        lSweepPoints = gSweepPoints
                        lIteratedOverAllPoints = true
                    end
                end
        
                -- Check if *TRG is received
                if gStateVariables.Arm_Sour == "BUS" then
                    PriorityExecute()
                end
        
                -- Update Digio and EOT when in End type binning
                if lIteratedOverAllPoints and gCalculate2.mLimits and
                        gStateVariables.Calc2_Clim_Mode == "GRAD" and
                        gStateVariables.Calc2_Clim_Bcon == "END" then
                    UpdateGradingEndBinnig()
                    lIteratedOverAllPoints = false
                    gProcessedAtleastOneLimit = false
                end
            end
        
            if gStateVariables.Calc1_Stat then
                if gMathVariables.mDataCount - gIntermediateSampleBuffer.mCount < gMathVariables.mDepth then
                    gErrorQueue.Add(801)
                end
            end
        
            if gStateVariables.Sour2_Ttl4_Mode == "BUSY" and
                    (gStateVariables.Arm_Sour == "NST" or gStateVariables.Arm_Sour == "PST" or
                    gStateVariables.Arm_Sour == "BST") then
                gEndOfTest.release()
                gEndOfTest.stimulus = 0
            end
        end
        
        
        --[[
            SetupDCSweep sets up the smua to run DC sweeps
            trigger.generator[1] is used as a software trigger to control the sweeps if no source trigger input is specified
            Timer 5 is used to implement the 2400 delay block
            smua.trigger.SOURCE_COMPLETE_EVENT_ID -> trigger.timer[5].stimulus -> smua.trigger.measure.stimulus
                       + (Tlink input if enabled)    + (Tlink input if enabled)
        --]]
        
        local SetupDCSweep = function (sourFunc)
            gAccessors.mSetSourceDelay(0)
            -- clear any set event detectors in the trigger layer
            if gStateVariables.Sour_Del == 0 then
                -- if source delay is set to zero set the timer delay to 1us
                gSourceDelayTimer.delay = 1e-6
            elseif gStateVariables.Sour_Del_Auto then
                -- if source auto delay is on then
                -- set timer delay to 1e-6 and
                -- set source delay to auto
                gSourceDelayTimer.delay = 1e-6
                gAccessors.mSetSourceDelay(smua.DELAY_AUTO)
            else
                gSourceDelayTimer.delay = gStateVariables.Sour_Del
            end
        
            -- Set Source, Delay, Measure Event detectors stimulus
            -- Timer3 is used as trigger delay timer
            if gStateVariables.Trig_Sour == "IMM" then
                if gStateVariables.Trig_Del == 0 then
                    gAccessors.mTriggerSourceStimulus(gTriggerGenerator.EVENT_ID)
                else
                    gTrigDelayTimer.delay = gStateVariables.Trig_Del
                    gBlender2.stimulus[2] = gTriggerGenerator.EVENT_ID
                    gAccessors.mTriggerSourceStimulus(gTrigDelayTimer.EVENT_ID)
                end
                gSourceDelayTimer.stimulus = gTrigger.SOURCE_COMPLETE_EVENT_ID
                gAccessors.mTriggerMeasureStimulus(gSourceDelayTimer.EVENT_ID)
            else -- "TLIN"
                -- Source Event detector input
                if gStateVariables.Trig_Inp == "SOUR" then
                    if gStateVariables.Trig_Del == 0 then
                        gAccessors.mTriggerSourceStimulus(gTriggerLines[gStateVariables.Trig_Ilin].EVENT_ID)
                    else
                        gTrigDelayTimer.delay = gStateVariables.Trig_Del
                        gBlender2.stimulus[2] = gTriggerLines[gStateVariables.Trig_Ilin].EVENT_ID
                        gAccessors.mTriggerSourceStimulus(gTrigDelayTimer.EVENT_ID)
                    end
                else
                    if gStateVariables.Trig_Del == 0 then
                        gAccessors.mTriggerSourceStimulus(gTriggerGenerator.EVENT_ID)
                    else
                        gTrigDelayTimer.delay = gStateVariables.Trig_Del
                        gBlender2.stimulus[2] = gTriggerGenerator.EVENT_ID
                        gAccessors.mTriggerSourceStimulus(gTrigDelayTimer.EVENT_ID)
                    end
                end
        
                -- Delay Event detector input
                if gStateVariables.Trig_Inp == "DEL" then
                    gBlender3.stimulus[1] = gTrigger.SOURCE_COMPLETE_EVENT_ID
                    gBlender3.stimulus[2] = gTriggerLines[gStateVariables.Trig_Ilin].EVENT_ID
                    gSourceDelayTimer.stimulus = gBlender3.EVENT_ID
                else
                    gSourceDelayTimer.stimulus = gTrigger.SOURCE_COMPLETE_EVENT_ID
                end
        
                -- Measure Event detector input
                if gStateVariables.Trig_Inp == "SENS" then
                    gBlender3.stimulus[1] = gSourceDelayTimer.EVENT_ID
                    gBlender3.stimulus[2] = gTriggerLines[gStateVariables.Trig_Ilin].EVENT_ID
                    gAccessors.mTriggerMeasureStimulus(gBlender3.EVENT_ID)
                else
                    gAccessors.mTriggerMeasureStimulus(gSourceDelayTimer.EVENT_ID)
                end
            end
        
            if sourFunc == "VOLT" then
                if gAccessors.mGetSourceFunc() ~= gDCVOLTS then
                    SetWithoutDelay(function () gAccessors.mSetSourceFunc(gDCVOLTS) end)
                end
                if gStateVariables.Sour_Volt_Mode == "FIX" then
                    local lLevel = gStateVariables.Sour_Volt_Trig_Ampl
                    
                    if gMathAbs(lLevel - gAccessors.mGetSourceLevelv()) >= gEpsilon * gMathAbs(lLevel) then
                        if gAccessors.mGetSourceRangev() * 1.01 < gMathAbs(lLevel) and gAccessors.mGetSourceAutoRangev() ~= 1 then
                            gAccessors.mSetSourceRangev(lLevel)
                        end
                        gAccessors.mTriggerSourceLinearv(lLevel, lLevel, 1)
                        gAccessors.mTriggerSourceAction(smua.ENABLE)
                        -- Check for range compliance condition depending on autorange
                        if gAccessors.mGetMeasureAutoRangei() == 0 then
                            gAccessors.mSetSourceLimiti(gAccessors.mGetMeasureRangei())
                        else
                            if gMathAbs(lLevel)/gSafeOperatingArea.mVoltage - 1 >= gEpsilon then                    
                                gAccessors.mSetSourceLimiti(gSafeOperatingArea.mCurrent)
                            elseif gAccessors.mGetSourceRangev()/gSafeOperatingArea.mVoltage - 1 <= gEpsilon then 
                                gAccessors.mSetSourceLimiti(gStateVariables.Sens_Curr_Prot)
                            end
                        end      
                        lMemScratch.Sens_Curr_Prot = gAccessors.mGetSourceLimiti()  
                    else
                        gAccessors.mTriggerSourceAction(smua.DISABLE)  
                        -- Check for range compliance condition depending on autorange             
                        if gAccessors.mGetMeasureAutoRangei() == 0 then
                            gAccessors.mSetSourceLimiti(gAccessors.mGetMeasureRangei())
                        else
                            if gMathAbs(gAccessors.mGetSourceLevelv())/gSafeOperatingArea.mVoltage - 1 >= gEpsilon then                    
                                gAccessors.mSetSourceLimiti(gSafeOperatingArea.mCurrent)
                            elseif gAccessors.mGetSourceRangev()/gSafeOperatingArea.mVoltage - 1 <= gEpsilon then 
                                gAccessors.mSetSourceLimiti(gStateVariables.Sens_Curr_Prot)
                            end
                        end      
                        lMemScratch.Sens_Curr_Prot = gAccessors.mGetSourceLimiti()                 
                    end
                else
                    gAccessors.mTriggerSourceAction(smua.ENABLE)
                end
            else -- "CURR"
                if gAccessors.mGetSourceFunc() ~= gDCAMPS then
                    SetWithoutDelay(function () gAccessors.mSetSourceFunc(gDCAMPS) end)
                end
                if gStateVariables.Sour_Curr_Mode == "FIX" then
                    local lLevel = gStateVariables.Sour_Curr_Trig_Ampl
        
                    if gMathAbs(lLevel - gAccessors.mGetSourceLeveli()) >= gEpsilon * gMathAbs(lLevel) then
                        if gAccessors.mGetSourceRangei() * 1.01 < gMathAbs(lLevel) and gAccessors.mGetSourceAutoRangei()~= 1 then
                            gAccessors.mSetSourceRangei(lLevel)
                        end
                        gAccessors.mTriggerSourceLineari(lLevel, lLevel, 1)
                        gAccessors.mTriggerSourceAction(smua.ENABLE)
                        -- Check for range compliance condition depending on autorange
                        if gAccessors.mGetMeasureAutoRangev() == 0 then
                            gAccessors.mSetSourceLimitv(gAccessors.mGetMeasureRangev())
                        else
                            if gMathAbs(lLevel)/gSafeOperatingArea.mCurrent - 1 >= gEpsilon then                    
                                gAccessors.mSetSourceLimitv(gSafeOperatingArea.mVoltage)
                            elseif gAccessors.mGetSourceRangei()/gSafeOperatingArea.mCurrent - 1 <= gEpsilon then 
                                gAccessors.mSetSourceLimitv(gStateVariables.Sens_Volt_Prot)
                            end
                        end      
                        lMemScratch.Sens_Volt_Prot = gAccessors.mGetSourceLimitv()
                    else
                        gAccessors.mTriggerSourceAction(smua.DISABLE)
                        -- Check for range compliance condition depending on autorange
                        if gAccessors.mGetMeasureAutoRangev() == 0 then
                            gAccessors.mSetSourceLimitv(gAccessors.mGetMeasureRangev())
                        else
                            if gMathAbs(gAccessors.mGetSourceLeveli())/gSafeOperatingArea.mCurrent - 1 >= gEpsilon then                    
                                gAccessors.mSetSourceLimitv(gSafeOperatingArea.mVoltage)
                            elseif gAccessors.mGetSourceRangei()/gSafeOperatingArea.mCurrent - 1 <= gEpsilon then 
                                gAccessors.mSetSourceLimitv(gStateVariables.Sens_Volt_Prot)
                            end
                        end      
                        lMemScratch.Sens_Volt_Prot = gAccessors.mGetSourceLimitv()
                    end
                else
                    gAccessors.mTriggerSourceAction(smua.ENABLE)
                end
            end
        end
        
        --[[
            TriggerSmu configures the Arm Event Detector, Source Event Detectors
            Arm and Trig Output triggers and Arm Input triggers
            triggers the Smu to perform sweep actions
        --]]
        local TriggerSmu = function ()
            if gDigioSupport then
                gStartOfTest.mode = digio.TRIG_FALLING
            end
        
            -- set Arm Event detector stimulus (pins 1-4 of Digio act as tlink pins 1-4)
            -- Pin 9 of the Digio is used as the SOT pin
            -- Timer4 is used as ARM trigger timer
            if gStateVariables.Arm_Sour == "IMM" then
                gArm.stimulus = 0
            elseif gStateVariables.Arm_Sour == "TIM" then
                gArmTimer.stimulus = gTrigger.SWEEP_COMPLETE_EVENT_ID
                gArmTimer.delay = gStateVariables.Arm_Tim
                gArm.stimulus = gArmTimer.EVENT_ID
            elseif gStateVariables.Arm_Sour == "TLIN" then
                gArm.stimulus = gTriggerLines[gStateVariables.Arm_Ilin].EVENT_ID
            elseif gStateVariables.Arm_Sour == "BUS" then
                gArm.stimulus = trigger.generator[2].EVENT_ID
            elseif gStateVariables.Arm_Sour == "NST" then
                gStartOfTest.mode = digio.TRIG_FALLING
                gArm.stimulus = gStartOfTest.EVENT_ID
            elseif gStateVariables.Arm_Sour == "PST" then
                gStartOfTest.mode = digio.TRIG_RISING
                gArm.stimulus = gStartOfTest.EVENT_ID
            elseif gStateVariables.Arm_Sour == "BST" then
                gStartOfTest.mode = digio.TRIG_EITHER
                gArm.stimulus = gStartOfTest.EVENT_ID
            elseif gStateVariables.Arm_Sour == "MAN" then
                gArm.stimulus = display.trigger.EVENT_ID
            end
        
            -- Configure Output triggers trigger.blender[4], trigger.blender[5], trigger.blender[6] are used
            if gStateVariables.Trig_Olin == gStateVariables.Arm_Olin then
                -- Arm Exit output trigger
                if gStateVariables.Arm_Outp.TEX then
                    gTrigOutArm.stimulus[1] = gTrigger.SWEEP_COMPLETE_EVENT_ID
                else
                    gTrigOutArm.stimulus[1] = 0
                end
        
                -- Arm Entry output trigger
                if gStateVariables.Arm_Outp.TENT then
                    gTrigOutArm.stimulus[2] = gTrigger.ARMED_EVENT_ID
                else
                    gTrigOutArm.stimulus[2] = 0
                end
        
                -- Source Event output trigger
                if gStateVariables.Trig_Outp.SOUR then
                    gTrigOutTrig.stimulus[1] = gTrigger.SOURCE_COMPLETE_EVENT_ID
                else
                    gTrigOutTrig.stimulus[1] = 0
                end
        
                -- Delay Event output trigger
                if gStateVariables.Trig_Outp.DEL then
                    gTrigOutTrig.stimulus[2] = gSourceDelayTimer.EVENT_ID
                else
                    gTrigOutTrig.stimulus[2] = 0
                end
        
                -- Measure Event output trigger
                if gStateVariables.Trig_Outp.SENS then
                    gTrigOutTrig.stimulus[3] = gTrigger.MEASURE_COMPLETE_EVENT_ID
                else
                    gTrigOutTrig.stimulus[3] = 0
                end
                gTrigOutBoth.stimulus[1] = gTrigOutArm.EVENT_ID
                gTrigOutBoth.stimulus[2] = gTrigOutTrig.EVENT_ID
                gTriggerLines[gStateVariables.Trig_Olin].stimulus = gTrigOutBoth.EVENT_ID
            else
                -- Arm Exit output trigger
                if gStateVariables.Arm_Outp.TEX then
                    gTrigOutArm.stimulus[1] = gTrigger.SWEEP_COMPLETE_EVENT_ID
                    gTriggerLines[gStateVariables.Arm_Olin].stimulus = gTrigOutArm.EVENT_ID
                else
                    gTrigOutArm.stimulus[1] = 0
                end
        
                -- Arm Entry output trigger
                if gStateVariables.Arm_Outp.TENT then
                    gTrigOutArm.stimulus[2] = gTrigger.ARMED_EVENT_ID
                    gTriggerLines[gStateVariables.Arm_Olin].stimulus = gTrigOutArm.EVENT_ID
                else
                    gTrigOutArm.stimulus[2] = 0
                end
        
                -- Source Event output trigger
                if gStateVariables.Trig_Outp.SOUR then
                    gTrigOutTrig.stimulus[1] = gTrigger.SOURCE_COMPLETE_EVENT_ID
                    gTriggerLines[gStateVariables.Trig_Olin].stimulus = gTrigOutTrig.EVENT_ID
                else
                    gTrigOutTrig.stimulus[1] = 0
                end
        
                -- Delay Event output trigger
                if gStateVariables.Trig_Outp.DEL then
                    gTrigOutTrig.stimulus[2] = gSourceDelayTimer.EVENT_ID
                    gTriggerLines[gStateVariables.Trig_Olin].stimulus = gTrigOutTrig.EVENT_ID
                else
                    gTrigOutTrig.stimulus[2] = 0
                end
        
                -- Measure Event output trigger
                if gStateVariables.Trig_Outp.SENS then
                    gTrigOutTrig.stimulus[3] = gTrigger.MEASURE_COMPLETE_EVENT_ID
                    gTriggerLines[gStateVariables.Trig_Olin].stimulus = gTrigOutTrig.EVENT_ID
                else
                    gTrigOutTrig.stimulus[3] = 0
                end
            end
            if gAccessors.mGetSourceOutput() == 0 then
                SetWithoutDelay(SmuOn)
            end
        
            -- Operation Condition Register Bit 4(3 on 2400), Sweeping
            StatusModel.SetCondition(operStatus, 4)
            -- Clear Operation Condition Register Bit 11(10 on 2400), In idle state
            StatusModel.ClearCondition(operStatus, 11)
        
            gTrigger.initiate()
        
            --check for Arm bypass conditions and bypass the event detector once
            if gStateVariables.Arm_Sour == "TIM" then
                -- bypass the arm event detector once
                gArm.set()    
            elseif gStateVariables.Arm_Dir == "SOUR" then
                if gStateVariables.Arm_Sour == "TLIN" or gStateVariables.Arm_Sour == "NST" or
                gStateVariables.Arm_Sour == "PST" or gStateVariables.Arm_Sour == "BST" then
                    -- bypass the arm event detector once
                    gArm.set()
                end
            end
            --check for source event detector bypass conditions and bypass the event detector once
            if gStateVariables.Trig_Dir == "SOUR" then
                if gStateVariables.Trig_Sour == "TLIN" then
                    -- bypass the source event detector once
                    gTrigger.source.set()
                end
            end
            
            ProcessData()
            waitcomplete()
        
            -- if output auto off enabled turn off the output
            if gStateVariables.Sour_Cle_Auto_State then
                gAccessors.mSetSourceOutput(0)
            end
        
            -- Operation Condition Register Bit 11(10 on 2400), In idle state
            StatusModel.SetCondition(operStatus, 11)
            -- Clear Operation Condition Register Bit 4(3 on 2400), Sweeping
            StatusModel.ClearCondition(operStatus, 4)
        
            -- if system clock auto reset enable get the offset
            if gStateVariables.Syst_Time_Res_Auto and gStateVariables.Trac_Cont ~= "NEXT" then
               gSystemClockOffset = gCurrentBuffer.basetimestamp
            end
            
            --restore the autorange settings and nplc values at the end of the sweep if all measurements are turned off
            if not gStateVariables.Sens_Func.ANY then
                gAccessors.mSetMeasureNplc(gSmuState.mNPLC)
                gAccessors.mSetMeasureAutoZero(gSmuState.mAzero)
            end
            gAccessors.mSetMeasureAutoRangei(gSmuState.mSenseAutoRangeI)
            gAccessors.mSetMeasureAutoRangev(gSmuState.mSenseAutoRangeV)
            if gSmuState.mAutoRangeI == 1 then
                if gAccessors.mGetSourceLeveli()/gOperatingBoundaries.mMaximumCurrentRange - 1 >= gEpsilon then
                    gAccessors.mSetSourceLeveli(gOperatingBoundaries.mMaximumCurrentRange)
                    lMemScratch.Sour_Curr_Ampl = gOperatingBoundaries.mMaximumCurrentRang
                end
                gAccessors.mSetSourceAutoRangei(gSmuState.mAutoRangeI)
                lMemScratch.Sour_Curr_Rang_Auto = 1
            end
        
            if gSmuState.mAutoRangeV == 1 then
                if gAccessors.mGetSourceLevelv()/gOperatingBoundaries.mMaximumVoltageRange -1 >= gEpsilon then
                    gAccessors.mSetSourceLevelv(gOperatingBoundaries.mMaximumVoltageRange)
                    lMemScratch.Sour_Volt_Ampl  = gOperatingBoundaries.mMaximumVoltageRange
                end
                gAccessors.mSetSourceAutoRangev(gSmuState.mAutoRangeV)
                lMemScratch.Sour_Volt_Rang_Auto = 1
            end
        end
        
        --[[
            Initiate Runs the voltage and current sweeps
            Source memory sweeps are handled in a seprate function
        --]]
        local Initiate = function ()
            gAccessors.mSetSourceCapMaxv(0)
            gAccessors.mSetSourceCapMaxi(0) 
            
            if gStateVariables.Sour2_Ttl_Lev ~= gStateVariables.Sour2_Ttl_Act
            and gStateVariables.Calc2_Clim_Cle_Auto then
                UpdateDigOut(gStateVariables.Sour2_Ttl_Lev)
            end
        
            gAbortExecuted = false
            if CheckForTlinkConflict() then
                gErrorQueue.Add(-221)
                return
            end
        
            -- in 2600 when trigger count is set to 0 then the smu stays in the trigger layer forever
            -- so change the trigger count to 1
            if gTrigger.count == 0 then
                gTrigger.count = 1
            end
        
            if gStateVariables.Sour_Func_Mode == "MEM" then
                --Source Memory sweeps
                InitiateSourceMemorySweep(gStateVariables.Sour_Mem_Start, gStateVariables.Sour_Mem_Poin, gArm.count, gTrigger.count)
            else
                -- Check if the calculate subsystem is enabled
                --[[
                    configureSense sets up the trigger model to take measurements.
                    If at least on of the measurement functions is turned on both
                    current and voltage measurements are taken. If all the measurement
                    functions are turned off only current measurements are taken
                    at a very low NPLC. This is done to measure source values and
                    timestamps.
                --]]
                gSmuState.mSenseAutoRangeI = gAccessors.mGetMeasureAutoRangei()
                gSmuState.mSenseAutoRangeV = gAccessors.mGetMeasureAutoRangev()
                gSmuState.mAutoRangeI = gAccessors.mGetSourceAutoRangei()
                gSmuState.mAutoRangeV = gAccessors.mGetSourceAutoRangev()
                gSmuState.mNPLC = gAccessors.mGetMeasureNplc()
                gSmuState.mAzero = gAccessors.mGetMeasureAutoZero()
                gCurrentBuffer.clear()
                gVoltageBuffer.clear()
                if gStateVariables.Sens_Func.ANY then
                    gAccessors.mTriggerMeasureiv(gCurrentBuffer, gVoltageBuffer)
                else
                    gAccessors.mSetMeasureAutoRangei(0)
                    gAccessors.mSetMeasureAutoZero(smua.AUTOZERO_OFF)
                    gAccessors.mSetMeasureNplc(0.001)
                    gAccessors.mTriggerMeasurei(gCurrentBuffer)
                end
                
                gSampleBuffer.mCount = 0
        
                if gStateVariables.Calc1_Stat then
                    --gMathVariables.mDepth = gMathCatalog[gMathCatalog[gStateVariables.Calc1_Selected_Index]].mDepth
                    gMathVariables.mDepth = gStateVariables.Calc1_Selected.mExpression.mDepth
                    gMathVariables.mDataCount = gMathVariables.mDepth
                    ClearBuffer(gCalculate1Buffer)
                    gIntermediateSampleBuffer.mCount = 0
                end
        
                -- Check if the calculate2 subsystem is enabled
                gCalculate2.mNullOffset = gStateVariables.Calc2_Null_Stat
                if gStateVariables.Calc2_Lim1_Stat then
                     gCalculate2.mLimits = true
                else
                    gCalculate2.mLimits = false
                    for i = 2, 12 do
                        -- Limit state 4 is not used but it is cheaper to just check
                        -- it with the rest.
                        if gStateVariables.Calc2_Lim_Stat[i] then
                            gCalculate2.mLimits = true
                            -- Set the digio 4 stimulus to SOT
                            if gStateVariables.Sour2_Ttl4_Mode == "BUSY" and
                                    (gStateVariables.Arm_Sour == "NST" or gStateVariables.Arm_Sour == "PST" or
                                    gStateVariables.Arm_Sour == "BST") then
                                --gEndOfTest.stimulus = gStartOfTest.EVENT_ID
                                gTriggerLines[8].stimulus = gTriggerLines[9].EVENT_ID
                                -- Note: The aliases are not used here because that puts the
                                --       upvalue count for this function over the limit.
                            end
                            break
                        end
                    end
                end
        
                if gCalculate2.mLimits or gCalculate2.mNullOffset then
                    ClearBuffer(gCalculate2Buffer)
                end
                if gStateVariables.Sour_Func_Mode == "VOLT" then
                    --Voltage Sweeps
                    if gAccessors.mGetSourceFunc() ~= gDCVOLTS then
                        gAccessors.mSetSourceFunc(gDCVOLTS)
                    end
                    SetupDCSweep("VOLT")
                    --Voltage List DC
                    --Voltage Fixed DC
                    if gStateVariables.Sour_Volt_Mode == "FIX" then
                        gSweepPoints = 1
                        TriggerSmu()
                    elseif gStateVariables.Sour_Volt_Mode == "LIST" then
                        local lTempListMaxVoltage = gStateVariables.Sour_List_Volt_Max
                        
                        if gMathAbs(lTempListMaxVoltage) > gSafeOperatingArea.mVoltage 
                        and gAccessors.mGetSourceLimiti()/gSafeOperatingArea.mCurrent - 1 >= gEpsilon then
                            if gAccessors.mGetMeasureAutoRangei() == 0 then
                                gAccessors.mSetSourceLimiti(gAccessors.mGetMeasureRangei())
                            else
                                gAccessors.mSetSourceLimiti(gSafeOperatingArea.mCurrent)
                            end      
                            lMemScratch.Sens_Curr_Prot = gAccessors.mGetSourceLimiti()
                        end          
        
                        gSweepPoints = table.getn(gStateVariables.Sour_List_Volt_Values)
        
                        if gAccessors.mGetSourceLimiti()/gSafeOperatingArea.mCurrent - 1 >= gEpsilon
                        and gMathAbs(lTempListMaxVoltage) > gSafeOperatingArea.mVoltage then
                            gAccessors.mSetSourceCapMaxv(gSafeOperatingArea.mVoltage)
                        end
        
                        if gStateVariables.Sour_Swe_Rang == "BEST" then
                            if gAccessors.mGetSourceCapMaxv() == 0 then
                                if gMathAbs(lTempListMaxVoltage)/(gAccessors.mGetSourceRangev() * 1.01) - 1 >= gEpsilon  then
                                   if gMathAbs(lTempListMaxVoltage) < gOperatingBoundaries.mMaximumVoltageRange then
                                       gAccessors.mSetSourceRangev(lTempListMaxVoltage)
                                       lMemScratch.Sour_Volt_Rang = gAccessors.mGetSourceRangev()
                                   else
                                       gAccessors.mSetSourceRangev(gOperatingBoundaries.mMaximumVoltageRange)
                                       lMemScratch.Sour_Volt_Rang = gAccessors.mGetSourceRangev()
                                   end
                                else
                                    if gAccessors.mGetSourceAutoRangev()== 1 then
                                        gAccessors.mSetSourceAutoRangev(0)
                                    end
                                end
                            else
                                if gAccessors.mGetSourceRangev()/gSafeOperatingArea.mVoltage - 1 >= gEpsilon then
                                    if  gMathAbs(gAccessors.mGetSourceLevelv())/gSafeOperatingArea.mVoltage - 1 >= gEpsilon then
                                        gAccessors.mSetSourceLevelv(gSafeOperatingArea.mVoltage)
                                        lMemScratch.Sour_Volt_Ampl = gSafeOperatingArea.mVoltage
                                    end
                                end
                                gAccessors.mSetSourceRangev(gSafeOperatingArea.mVoltage)
                                lMemScratch.Sour_Volt_Rang = gAccessors.mGetSourceRangev()
                            end
                        elseif gStateVariables.Sour_Swe_Rang == "FIX" then
                            if gAccessors.mGetSourceCapMaxv() == 0 then
                                gAccessors.mSetSourceCapMaxv(gAccessors.mGetSourceRangev())
                            end
                        elseif gStateVariables.Sour_Swe_Rang == "AUTO" then
                            if gAccessors.mGetSourceCapMaxv() == 0 then
                                if gMathAbs(lTempListMaxVoltage) > gOperatingBoundaries.mMaximumVoltageRange then
                                   gAccessors.mSetSourceCapMaxv(gOperatingBoundaries.mMaximumVoltageRange)
                                end
                            end
                            if gMathAbs(gAccessors.mGetSourceLevelv())/gSafeOperatingArea.mVoltage - 1 >= gEpsilon 
                            and gAccessors.mGetSourceLimiti()/gSafeOperatingArea.mCurrent - 1 >= gEpsilon then
                                gAccessors.mSetSourceLevelv(gSafeOperatingArea.mVoltage)
                                lMemScratch.Sour_Volt_Ampl = gSafeOperatingArea.mVoltage
                            end
                            gAccessors.mSetSourceAutoRangev(1)
                            lMemScratch.Sour_Volt_Rang_Auto = 1
                        end
        
                        if gStateVariables.Sour_List_Volt_Start == 1 then
                            gAccessors.mTriggerSourceListv(gStateVariables.Sour_List_Volt_Values)
                        else
                            ReArrangeList(gStateVariables.Sour_List_Volt_Start, gStateVariables.Sour_List_Volt_Values)
                            gAccessors.mTriggerSourceListv(gListSweep)
                        end
        
                        TriggerSmu()
        
                    else -- "SWE"
                        local lTempStartVoltage = gStateVariables.Sour_Volt_Start
                        local lTempStopVoltage = gStateVariables.Sour_Volt_Stop                
                        local lSweepMaxValue
                        
                        if gMathAbs(lTempStopVoltage) > gMathAbs(lTempStartVoltage) then
                            lSweepMaxValue = gMathAbs(lTempStopVoltage)
                        else
                            lSweepMaxValue = gMathAbs(lTempStartVoltage)
                        end
                        
                        if gMathAbs(lSweepMaxValue) > gSafeOperatingArea.mVoltage 
                        and gAccessors.mGetSourceLimiti()/gSafeOperatingArea.mCurrent - 1 >= gEpsilon then
                            if gAccessors.mGetMeasureAutoRangei() == 0 then
                                gAccessors.mSetSourceLimiti(gAccessors.mGetMeasureRangei())
                            else
                                gAccessors.mSetSourceLimiti(gSafeOperatingArea.mCurrent)
                            end    
                            lMemScratch.Sens_Curr_Prot = gAccessors.mGetSourceLimiti()
                        end  
        
                        gSweepPoints = gStateVariables.Sour_Swe_Poin
                        if gAccessors.mGetSourceAutoRangev() == 1 then
                            if gMathAbs(lTempStopVoltage) > gOperatingBoundaries.mMaximumVoltageRange then
                                lTempStopVoltage = gOperatingBoundaries.mMaximumVoltageRange
                                if lTempStopVoltage < 0 then
                                    lTempStopVoltage = -gStateVariables.Sour_Volt_Stop
                                end
                            elseif gMathAbs(lTempStartVoltage) > gOperatingBoundaries.mMaximumVoltageRange then
                                lTempStartVoltage = gOperatingBoundaries.mMaximumVoltageRange
                                if lTempStartVoltage < 0 then
                                    lTempStartVoltage = -lTempStartVoltage
                                end
                            end
                        end
                        if gAccessors.mGetSourceLimiti()/gSafeOperatingArea.mCurrent - 1 >= gEpsilon
                        and ((gMathAbs(lTempStopVoltage) > gSafeOperatingArea.mVoltage)
                        or  (gMathAbs(lTempStartVoltage) > gSafeOperatingArea.mVoltage)) then
                            gAccessors.mSetSourceCapMaxv(gSafeOperatingArea.mVoltage)
                        end
        
                        -- Best will set the range to accomodate all the list values
                        --[[ Fixed  The source remains on the range that it is presently
                             on when the sweep is started. For sweep points that exceed the
                             source range capability, the source will output the maximum level for
                             that range.
                        --]]
                        -- Auto will set the corresponding function range to auto
        
                        if gStateVariables.Sour_Swe_Rang == "BEST" then
                            if gAccessors.mGetSourceCapMaxv() == 0 then
                                if gMathAbs(lTempStopVoltage)/gAccessors.mGetSourceRangev() - 1 >= gEpsilon
                                or  gMathAbs(lTempStartVoltage)/gAccessors.mGetSourceRangev() - 1 >= gEpsilon then
                                    if gMathAbs(lTempStopVoltage) > gMathAbs(lTempStartVoltage) then
                                        if gMathAbs(lTempStopVoltage) < gOperatingBoundaries.mMaximumVoltageRange then
                                           gAccessors.mSetSourceRangev(lTempStopVoltage)
                                           lMemScratch.Sour_Volt_Rang = gAccessors.mGetSourceRangev()
                                        else
                                           gAccessors.mSetSourceRangev(gOperatingBoundaries.mMaximumVoltageRange)
                                           lMemScratch.Sour_Volt_Rang = gAccessors.mGetSourceRangev()
                                        end
                                    else
                                        if gMathAbs(lTempStartVoltage) < gOperatingBoundaries.mMaximumVoltageRange then
                                           gAccessors.mSetSourceRangev(lTempStartVoltage)
                                           lMemScratch.Sour_Volt_Rang = gAccessors.mGetSourceRangev()
                                        else
                                           gAccessors.mSetSourceRangev(gOperatingBoundaries.mMaximumVoltageRange)
                                           lMemScratch.Sour_Volt_Rang = gAccessors.mGetSourceRangev()
                                        end
                                    end
                                end
                            else
                                if gAccessors.mGetSourceRangev()/gSafeOperatingArea.mVoltage - 1 >= gEpsilon then
                                    if  gMathAbs(gAccessors.mGetSourceLevelv())/gSafeOperatingArea.mVoltage - 1 >= gEpsilon then
                                        gAccessors.mSetSourceLevelv(gSafeOperatingArea.mVoltage)
                                        lMemScratch.Sour_Volt_Ampl = gSafeOperatingArea.mVoltage
                                    end
                                end
                                gAccessors.mSetSourceRangev(gSafeOperatingArea.mVoltage)
                                lMemScratch.Sour_Volt_Rang = gAccessors.mGetSourceRangev()
                            end
                        elseif gStateVariables.Sour_Swe_Rang == "FIX" then                    
                            if gAccessors.mGetSourceCapMaxv() == 0 then
                                gAccessors.mSetSourceCapMaxv(gAccessors.mGetSourceRangev())
                            end
                        elseif gStateVariables.Sour_Swe_Rang == "AUTO" then
                            if gMathAbs(lTempStartVoltage)  > gOperatingBoundaries.mMaximumVoltageRange
                            or gMathAbs(lTempStopVoltage)  > gOperatingBoundaries.mMaximumVoltageRange then
                                gAccessors.mSetSourceCapMaxv(gOperatingBoundaries.mMaximumVoltageRange)
                            end
                            if (gMathAbs(lTempStopVoltage) > gSafeOperatingArea.mVoltage or gMathAbs(lTempStartVoltage) > gSafeOperatingArea.mVoltage)
                            and gAccessors.mGetSourceLimiti()/gSafeOperatingArea.mCurrent - 1 >= gEpsilon then
                                gAccessors.mSetSourceCapMaxv(gSafeOperatingArea.mVoltage)
                            end
                            if gMathAbs(gAccessors.mGetSourceLevelv())/gSafeOperatingArea.mVoltage - 1 >= gEpsilon
                            and gAccessors.mGetSourceLimiti()/gSafeOperatingArea.mCurrent - 1 >= gEpsilon then
                                gAccessors.mSetSourceLevelv(gSafeOperatingArea.mVoltage)
                                lMemScratch.Sour_Volt_Ampl = gSafeOperatingArea.mVoltage
                            end
                            gAccessors.mSetSourceAutoRangev(1)
                            lMemScratch.Sour_Volt_Rang_Auto = 1
                        end
        
                        --Voltage Linear sweep DC
                        if gStateVariables.Sour_Swe_Spac == "LIN" then
                            if gStateVariables.Sour_Swe_Dir == "UP" then
                                gAccessors.mTriggerSourceLinearv(lTempStartVoltage,
                                lTempStopVoltage, gStateVariables.Sour_Swe_Poin)
                            else
                                gAccessors.mTriggerSourceLinearv(lTempStopVoltage,
                                lTempStartVoltage, gStateVariables.Sour_Swe_Poin)                        
                            end
                            TriggerSmu()
        
                        --Voltage Log sweep DC
                        elseif gStateVariables.Sour_Swe_Spac == "LOG" then
                            if lTempStopVoltage * lTempStartVoltage <= 0 then
                                gErrorQueue.Add(900)
                                return
                            end
        
                            if gStateVariables.Sour_Swe_Dir == "UP" then
                                gAccessors.mTriggerSourceLogv(lTempStartVoltage,
                                lTempStopVoltage, gStateVariables.Sour_Swe_Poin)
                            else                       
                                gAccessors.mTriggerSourceLogv(lTempStopVoltage,
                                lTempStartVoltage, gStateVariables.Sour_Swe_Poin)
                            end
                            TriggerSmu()
                        end
                    end
                    gStateVariables.Sour_Volt_Trig_Ampl = gAccessors.mGetSourceLevelv()
                    lMemScratch.Sour_Volt_Ampl = gStateVariables.Sour_Volt_Trig_Ampl
                else -- "CURR"
                    --Current Sweeps
                    if gAccessors.mGetSourceFunc() ~= gDCAMPS then
                        gAccessors.mSetSourceFunc(gDCAMPS)
                    end
                    SetupDCSweep("CURR")
                    --Current Fixed mode
                    if gStateVariables.Sour_Curr_Mode == "FIX" then
                        gSweepPoints = 1
                        TriggerSmu()
                    elseif gStateVariables.Sour_Curr_Mode == "LIST" then
                        local lTempListMaxCurrent = gStateVariables.Sour_List_Curr_Max
                        
                        if gMathAbs(lTempListMaxCurrent) > gSafeOperatingArea.mCurrent 
                        and gAccessors.mGetSourceLimitv()/gSafeOperatingArea.mVoltage - 1 >= gEpsilon then
                            if gAccessors.mGetMeasureAutoRangev() == 0 then
                                gAccessors.mSetSourceLimitv(gAccessors.mGetMeasureRangev())
                            else
                                gAccessors.mSetSourceLimitv(gSafeOperatingArea.mVoltage)
                            end      
                            lMemScratch.Sens_Volt_Prot = gAccessors.mGetSourceLimitv()
                        end     
        
                        gSweepPoints = table.getn(gStateVariables.Sour_List_Curr_Values)
                        if gAccessors.mGetSourceLimitv()/gSafeOperatingArea.mVoltage - 1 >= gEpsilon
                        and gMathAbs(lTempListMaxCurrent) > gSafeOperatingArea.mCurrent then
                            gAccessors.mSetSourceCapMaxi(gSafeOperatingArea.mCurrent)
                        end
                        if gStateVariables.Sour_Swe_Rang == "BEST" then
                            if gAccessors.mGetSourceCapMaxi() == 0 then
                                if gMathAbs(lTempListMaxCurrent)/(gAccessors.mGetSourceRangei() * 1.01) - 1 >= gEpsilon  then
                                    if lTempListMaxCurrent < gOperatingBoundaries.mMaximumCurrentRange then
                                        gAccessors.mSetSourceRangei(lTempListMaxCurrent)
                                        lMemScratch.Sour_Curr_Rang = gAccessors.mGetSourceRangei()
                                    else
                                        gAccessors.mSetSourceRangei(gOperatingBoundaries.mMaximumCurrentRange)
                                        lMemScratch.Sour_Curr_Rang = gAccessors.mGetSourceRangei()
                                    end
                                else
                                    if gAccessors.mGetSourceAutoRangei() == 1 then
                                        gAccessors.mSetSourceAutoRangei(0)
                                    end
                                end
                            else
                               if gAccessors.mGetSourceRangei()/gSafeOperatingArea.mCurrent - 1 >= gEpsilon then
                                    if  gMathAbs(gAccessors.mGetSourceLeveli())/gSafeOperatingArea.mCurrent - 1 >= gEpsilon then
                                        gAccessors.mSetSourceLeveli(gSafeOperatingArea.mCurrent)
                                        lMemScratch.Sour_Curr_Ampl = gSafeOperatingArea.mCurrent
                                    end
                               end
                               gAccessors.mSetSourceRangei(gSafeOperatingArea.mCurrent)
                               lMemScratch.Sour_Curr_Rang = gAccessors.mGetSourceRangei()
                            end
                        elseif  gStateVariables.Sour_Swe_Rang == "FIX" then
                            if gAccessors.mGetSourceCapMaxi() == 0 then
                                gAccessors.mSetSourceCapMaxi(gAccessors.mGetSourceRangei())
                            end
        
                        elseif gStateVariables.Sour_Swe_Rang == "AUTO" then
                            if gAccessors.mGetSourceCapMaxi() == 0 then
                                if gMathAbs(lTempListMaxCurrent) > gOperatingBoundaries.mMaximumCurrentRange then
                                    gAccessors.mSetSourceCapMaxi(gOperatingBoundaries.mMaximumCurrentRange)
                                end
                            end
                            if gMathAbs(lTempListMaxCurrent) > gSafeOperatingArea.mCurrent 
                            and gAccessors.mGetSourceLimitv()/gSafeOperatingArea.mVoltage - 1 >= gEpsilon then
                                gAccessors.mSetSourceCapMaxi(gSafeOperatingArea.mCurrent)
                            end
                            if gMathAbs(gAccessors.mGetSourceLeveli())/gSafeOperatingArea.mCurrent - 1 >= gEpsilon 
                            and gAccessors.mGetSourceLimitv()/gSafeOperatingArea.mVoltage - 1 >= gEpsilon then
                                gAccessors.mSetSourceLeveli(gSafeOperatingArea.mCurrent)
                                lMemScratch.Sour_Curr_Ampl = gSafeOperatingArea.mCurrent
                            end
                            gAccessors.mSetSourceAutoRangei(1)
                            lMemScratch.Sour_Curr_Rang_Auto = 1
                        end
        
                        if gStateVariables.Sour_List_Curr_Start == 1 then
                            gAccessors.mTriggerSourceListi(gStateVariables.Sour_List_Curr_Values)
                        else
                            ReArrangeList(gStateVariables.Sour_List_Curr_Start, gStateVariables.Sour_List_Curr_Values)
                            gAccessors.mTriggerSourceListi(gListSweep)
                        end
        
                        TriggerSmu()
        
                    else -- "SWE"
                        local lTempStartCurrent = gStateVariables.Sour_Curr_Start
                        local lTempStopCurrent = gStateVariables.Sour_Curr_Stop
                        local lSweepMaxValue
                        
                        if gMathAbs(lTempStopCurrent) > gMathAbs(lTempStartCurrent) then
                            lSweepMaxValue = gMathAbs(lTempStopCurrent)
                        else
                            lSweepMaxValue = gMathAbs(lTempStartCurrent)
                        end
                        
                        if gMathAbs(lSweepMaxValue) > gSafeOperatingArea.mCurrent 
                        and gAccessors.mGetSourceLimitv()/gSafeOperatingArea.mVoltage - 1 >= gEpsilon then
                            if gAccessors.mGetMeasureAutoRangev() == 0 then
                                gAccessors.mSetSourceLimitv(gAccessors.mGetMeasureRangev())
                            else
                                gAccessors.mSetSourceLimitv(gSafeOperatingArea.mVoltage)
                            end      
                            lMemScratch.Sens_Volt_Prot = gAccessors.mGetSourceLimitv()
                        end   
        
                        gSweepPoints = gStateVariables.Sour_Swe_Poin
                        if gAccessors.mGetSourceAutoRangei()== 1 then
                            if gMathAbs(lTempStopCurrent) >  gOperatingBoundaries.mMaximumCurrentRange then
                                lTempStopCurrent = gOperatingBoundaries.mMaximumCurrentRange
                                if lTempStopCurrent < 0 then
                                    lTempStopCurrent = -gStateVariables.Sour_Curr_Stop
                                end
                            elseif gMathAbs(lTempStartCurrent) > gOperatingBoundaries.mMaximumCurrentRange then
                                lTempStartCurrent = gOperatingBoundaries.mMaximumCurrentRange
                                if lTempStartCurrent < 0 then
                                    lTempStartCurrent = -lTempStartCurrent
                                end
                            end
                        end
                        if gAccessors.mGetSourceLimitv()/gSafeOperatingArea.mVoltage - 1 >= gEpsilon
                        and ((gMathAbs(lTempStopCurrent) > gSafeOperatingArea.mCurrent)
                        or  (gMathAbs(lTempStartCurrent) > gSafeOperatingArea.mCurrent)) then
                            gAccessors.mSetSourceCapMaxi(gSafeOperatingArea.mCurrent)
                        end
        
                        -- Best will set the range to accomodate all the list values
                        --[[ Fixed  The source remains on the range that it is presently
                             on when the sweep is started. For sweep points that exceed the
                             source range capability, the source will output the maximum level for
                             that range.
                        --]]
                        -- Auto will set the corresponding function range to auto
        
                        if gStateVariables.Sour_Swe_Rang == "BEST" then
                            if gAccessors.mGetSourceCapMaxi() == 0 then
                                if gMathAbs(lTempStopCurrent)/gAccessors.mGetSourceRangei() - 1 >= gEpsilon
                                or  gMathAbs(lTempStartCurrent)/gAccessors.mGetSourceRangei() - 1 >= gEpsilon then
                                    if gMathAbs(lTempStopCurrent) >  gMathAbs(lTempStartCurrent) then
                                        if gMathAbs(lTempStopCurrent) < gOperatingBoundaries.mMaximumCurrentRange then
                                            gAccessors.mSetSourceRangei(lTempStopCurrent)
                                            lMemScratch.Sour_Curr_Rang = gAccessors.mGetSourceRangei()
                                        else
                                            gAccessors.mSetSourceRangei(gOperatingBoundaries.mMaximumCurrentRange)
                                            lMemScratch.Sour_Curr_Rang = gAccessors.mGetSourceRangei()
                                        end
                                    else
                                        if gMathAbs(lTempStartCurrent) < gOperatingBoundaries.mMaximumCurrentRange then
                                           gAccessors.mSetSourceRangei(lTempStartCurrent)
                                           lMemScratch.Sour_Curr_Rang = gAccessors.mGetSourceRangei()
                                        else
                                           gAccessors.mSetSourceRangei(gOperatingBoundaries.mMaximumCurrentRange)
                                           lMemScratch.Sour_Curr_Rang = gAccessors.mGetSourceRangei()
                                        end
                                    end
                                end
                            else
                                if gAccessors.mGetSourceRangei()/gSafeOperatingArea.mCurrent - 1 >= gEpsilon then
                                    if  gMathAbs(gAccessors.mGetSourceLeveli())/gSafeOperatingArea.mCurrent - 1 >= gEpsilon then
                                        gAccessors.mSetSourceLeveli(gSafeOperatingArea.mCurrent)
                                        lMemScratch.Sour_Curr_Ampl = gSafeOperatingArea.mCurrent
                                    end
                                end
                               gAccessors.mSetSourceRangei(gSafeOperatingArea.mCurrent)
                            end
                        elseif  gStateVariables.Sour_Swe_Rang == "FIX" then
                            if gAccessors.mGetSourceCapMaxi() == 0 then
                                gAccessors.mSetSourceCapMaxi(gAccessors.mGetSourceRangei())
                            end
                        elseif gStateVariables.Sour_Swe_Rang == "AUTO" then
                            if gMathAbs(lTempStopCurrent) > gOperatingBoundaries.mMaximumCurrentRange
                            or gMathAbs(lTempStartCurrent) > gOperatingBoundaries.mMaximumCurrentRange then
                                gAccessors.mSetSourceCapMaxi(gOperatingBoundaries.mMaximumCurrentRange)
                            end
                            if (gMathAbs(lTempStopCurrent) > gSafeOperatingArea.mCurrent or gMathAbs(lTempStartCurrent) > gSafeOperatingArea.mCurrent)
                            and gAccessors.mGetSourceLimitv()/gSafeOperatingArea.mVoltage - 1 >= gEpsilon then
                                gAccessors.mSetSourceCapMaxi(gSafeOperatingArea.mCurrent)
                            end
                            if gMathAbs(gAccessors.mGetSourceLeveli())/gSafeOperatingArea.mCurrent - 1 >= gEpsilon 
                            and gAccessors.mGetSourceLimitv()/gSafeOperatingArea.mVoltage - 1 >= gEpsilon then
                                gAccessors.mSetSourceLeveli(gSafeOperatingArea.mCurrent)
                                lMemScratch.Sour_Curr_Ampl = gSafeOperatingArea.mCurrent
                            end
                            gAccessors.mSetSourceAutoRangei(1)
                            lMemScratch.Sour_Curr_Rang_Auto = 1
                        end
        
                        --Current Linear sweep DC
                        if gStateVariables.Sour_Swe_Spac == "LIN" then
                            if gStateVariables.Sour_Swe_Dir == "UP" then
                                gAccessors.mTriggerSourceLineari(lTempStartCurrent,
                                lTempStopCurrent, gStateVariables.Sour_Swe_Poin)
                            else
                                gAccessors.mTriggerSourceLineari(lTempStopCurrent,
                                lTempStartCurrent, gStateVariables.Sour_Swe_Poin)                        
                            end
                            TriggerSmu()
        
                        --Current Log sweep DC
                        elseif gStateVariables.Sour_Swe_Spac == "LOG" then
                            if lTempStopCurrent * lTempStartCurrent <= 0 then
                                gErrorQueue.Add(900)
                                return
                            end
                            if gStateVariables.Sour_Swe_Dir == "UP" then
                                gAccessors.mTriggerSourceLogi(lTempStartCurrent,
                                lTempStopCurrent, gStateVariables.Sour_Swe_Poin)
                            else
                                gAccessors.mTriggerSourceLogi(lTempStopCurrent,
                                lTempStartCurrent, gStateVariables.Sour_Swe_Poin)                        
                            end
                            TriggerSmu()
                        end
                    end
                    gStateVariables.Sour_Curr_Trig_Ampl = gAccessors.mGetSourceLeveli()
                    lMemScratch.Sour_Curr_Ampl = gStateVariables.Sour_Curr_Trig_Ampl
                end
            end
        
            if errorqueue.count > 0 then
                gErrorQueue.Add(900)
            end
        end
        
        --============================================================================
        --
        -- SCPI Command Definitions
        --
        -- This section is where the command tables are populated and command
        -- implemenation function are defined.
        --
        --============================================================================
        
        -- *IDN?
        gCurrentRoot = gCommandTree["*IDN"]
        gCurrentRoot.mQuery.mExecute = function ()
            Print("KEITHLEY INSTRUMENTS INC.,MODEL 2400,"..localnode.serialno..","..g2400FwRev)
        end
        
        -- *RST
        -- Restore GPIB defaults.
        gCurrentRoot = gCommandTree["*RST"]
        gCurrentRoot.mCommand.mExecute = function ()
            smua.abort()
            gAbortExecuted = true
            reset()
            ResetDefaults()
        end
        
        -- *SAV
        -- Save the present setup as the user-saved setup.
        gCurrentRoot = gCommandTree["*SAV"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mInteger
        gCurrentRoot.mCommand.mExecute = function ()--lParameters)
            --local lSetup = lParameters[1]
            --[[
            if lSetup >= 0 and lSetup <= 4 then
                setup.save(lSetup + 1)
            else
                gErrorQueue.Add(-222)
            end
            --]]
        end
        
        --Recall setup.
        gCurrentRoot = gCommandTree["*RCL"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mInteger
        gCurrentRoot.mCommand.mExecute = function ()--lParameters)
            --local lSetup = lParameters[1]
        end
        -- *CLS
        -- Clear all status model registers.
        gCurrentRoot = gCommandTree["*CLS"]
        gCurrentRoot.mCommand.mExecute = function ()
            StatusModel.mStatus         = 0
            gRemoteCommStatus.condition = 0
            measStatus.mEvent           = 0
            quesStatus.mEvent           = 0
            operStatus.mEvent           = 0
            standardStatus.mEvent       = 0
            gErrorQueue.Clear()
            UpdateStatusModel()
        end
        
        -- *OPC
        gCurrentRoot = gCommandTree["*OPC"]
        gCurrentRoot.mCommand.mExecute = function ()
            opc()
            -- Update status model
            UpdateStatusModel()
        end
        
        -- *OPC?
        gCurrentRoot.mQuery.mExecute = function ()
            waitcomplete()
            Print("1")
        end
        
        -- *OPT?
        gCurrentRoot = gCommandTree["*OPT"]
        gCurrentRoot.mQuery.mExecute = function ()
            Print("0")
        end
        
        -- *TST?
        gCurrentRoot = gCommandTree["*TST"]
        gCurrentRoot.mQuery.mExecute = function ()
            Print("0")
        end
        
        -- *WAI
        gCurrentRoot = gCommandTree["*WAI"]
        gCurrentRoot.mCommand.mExecute = NullFunction
        
        -- DCL
        gSpecialCommands[gRemoteComm.types.DCL].mCommand.mExecute = function ()
            smua.abort()
            gAbortExecuted = true
            gRemoteComm.output = gOrigin
        end
        
        -- LLO
        gSpecialCommands[gRemoteComm.types.SETLOCKOUT].mCommand.mExecute = function ()
            display.locallockout = display.LOCK
        end
        
        gSpecialCommands[gRemoteComm.types.RESETLOCKOUT].mCommand.mExecute = function ()
            display.locallockout = display.UNLOCK
        end
        
        gCurrentRoot = gCommandTree["DIAGNOSTIC"]["EXIT"]
        gCurrentRoot.mCommand.mExecute = function ()
            gRemoteComm.intercept = gRemoteComm.DISABLE
            gEngineMode = false
            -- override status register
            gRemoteCommStatus.override = 0
            exit()
        end
        gCurrentRoot = gCommandTree["DIAGNOSTIC"]["ECHO"]
        gCurrentRoot.mCommand.mParameters = {}
        for lIndex = 1, 99 do
            gCurrentRoot.mCommand.mParameters[lIndex] =
                {
                    mParse = gParserTable.ParseParameterAny,
                    mOptional = true,
                }
        end
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lIndex = 1
            while lParameters[lIndex] do
                Print("[")
                Print(lParameters[lIndex])
                Print("]")
                gRemoteComm.terminateunit()
                lIndex = lIndex + 1
            end
        end
        
        gCurrentRoot = gCommandTree["DIAGNOSTIC"]["VERSION"]
        gCurrentRoot.mQuery.mExecute = function ()
            local lVersion = "$Change: 76212 $"
            local lIndex1, lIndex2 = string.find(lVersion, "%d+")
            lVersion = string.sub(lVersion, lIndex1, lIndex2)
            Print(lVersion)
        end
        
        gCurrentRoot = gCommandTree["DIAGNOSTIC"]["MODEL"]
        gCurrentRoot.mQuery.mExecute = function ()
            Print(localnode.model)
        end
        
        gCurrentRoot = gCommandTree["DIAGNOSTIC"]["FWREV"]
        gCurrentRoot.mQuery.mExecute = function ()
            Print(localnode.revision)
        end
        
        gCurrentRoot = gCommandTree["DIAGNOSTIC"]["DISPLAY"]["ERRORS"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mBoolean
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            if lParameters[1] then
                gDisplayErrors = true
            else
                gDisplayErrors = false
            end
        end
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gResponseValues[gDisplayErrors])
        end
        
        -----------------------------------------------------------------------
        -- DISPLAY subsystem commands
        -----------------------------------------------------------------------
        
        -- DISPlay:WINDow1:DATA?
        gCurrentRoot = gCommandTree["DISPLAY"]["WINDOW1"]["DATA"]
        gCurrentRoot.mQuery.mExecute = function ()
            local lText = display.gettext(false, 1)
        
            lText = string.gsub(lText, [["]], [[""]])
            Print([["]])
            Print(lText)
            Print([["]])
        end
        
        -- DISPlay:WINDow2:DATA?
        gCurrentRoot = gCommandTree["DISPLAY"]["WINDOW2"]["DATA"]
        gCurrentRoot.mQuery.mExecute = function ()
            local lText = display.gettext(false, 2)
        
            lText = string.gsub(lText, [["]], [[""]])
            Print([["]])
            Print(lText)
            Print([["]])
        end
        
        -- DISPlay:WINDow1:TEXT:DATA <a>
        gCurrentRoot = gCommandTree["DISPLAY"]["WINDOW1"]["TEXT"]["DATA"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mDisplayData
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lText = lParameters[1]
            local displayState = display.screen
        
            if string.len(lText) <= 20 then
                gStateVariables.Disp_Wind1_Text_Data = lParameters[1]
                display.setcursor(1, 1)
                display.settext(string.rep(" ", 20))
                display.setcursor(1, 1)
                display.settext(lParameters[1])
                display.screen = displayState
            else
                gErrorQueue.Add(-223)
            end
        end
        -- DISPlay:WINDow1:TEXT:DATA?
        gCurrentRoot.mQuery.mExecute = function ()
            local lText = gStateVariables.Disp_Wind1_Text_Data
        
            lText = string.gsub(lText, [["]], [[""]])
            Print([["]])
            Print(lText)
            Print([["]])
        end
        
        -- DISPlay:WINDow2:TEXT:DATA <a>
        gCurrentRoot = gCommandTree["DISPLAY"]["WINDOW2"]["TEXT"]["DATA"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mDisplayData
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lText = lParameters[1]
            local displayState = display.screen
        
            if string.len(lText) <= 32 then
                gStateVariables.Disp_Wind2_Text_Data = lParameters[1]
                display.setcursor(2, 1)
                display.settext(string.rep(" ", 32))
                display.setcursor(2, 1)
                display.settext(lParameters[1])
                display.screen = displayState
            else
                gErrorQueue.Add(-223)
            end
        end
        -- DISPlay:WINDow2:TEXT:DATA?
        gCurrentRoot.mQuery.mExecute = function ()
            local lText = gStateVariables.Disp_Wind2_Text_Data
        
            lText = string.gsub(lText, [["]], [[""]])
            Print([["]])
            Print(lText)
            Print([["]])
        end
        
        -- DISPlay:ENABle <b>
        gCurrentRoot = gCommandTree["DISPLAY"]["ENABLE"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mBoolean
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            -- Accepts the Command but no effect on 2600B
            gStateVariables.Disp_Enab = lParameters[1]
            --if lParameters[1] then
            --    display.screen = display.SMUA
            --else
            --    display.screen = display.USER
            --end
        end
        -- DISPlay:ENABle?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gResponseValues[gStateVariables.Disp_Enab])
        end
        
        -- DISPlay:CNDisplay
        gCurrentRoot = gCommandTree["DISPLAY"]["CNDISPLAY"]
        gCurrentRoot.mCommand.mExecute = function ()
            display.screen = display.SMUA
        end
        
        -- DISPlay:WINDow1:TEXT:STATe <b>
        gCurrentRoot = gCommandTree["DISPLAY"]["WINDOW1"]["TEXT"]["STATE"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mBoolean
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            if lParameters[1] then
                gStateVariables.Disp_State = display.USER
                display.screen = display.USER
            else
                gStateVariables.Disp_State = display.SMUA
                display.screen = display.SMUA
            end
        end
        --DISPlay:WINDow1:TEXT:STATe?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gResponseValues[display.screen == display.USER])
        end
        
        -- DISPlay:WINDow2:TEXT:STATe <b>
        gCurrentRoot = gCommandTree["DISPLAY"]["WINDOW2"]["TEXT"]["STATE"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mBoolean
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            if lParameters[1] then
                gStateVariables.Disp_State = display.USER
                display.screen = display.USER
            else
                gStateVariables.Disp_State = display.SMUA
                display.screen = display.SMUA
            end
        end
        -- DISPlay:WINDow2:TEXT:STATe?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gResponseValues[display.screen == display.USER])
        end
        
        -- DISPlay:DIGits <n>(4-7)
        gCurrentRoot = gCommandTree["DISPLAY"]["DIGITS"]
        gCurrentRoot.mCommand.mParameters =
        {
            {
                mParse = gParserTable.ParseParameterChoice,
                mData =
                {
                    gParserTable.mParseDigits,
                    gParserTable.mParseInteger,
                }
            }
        }
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            -- 2600B does not have 3.5 digits resolution option so when 3.5 digits
            -- or minimum is requested 2600B sets the resolution to 4.5
            local lDigits = lParameters[1]
            if lDigits == 4 or lDigits == 5 then
                display.smua.digits = display.DIGITS_4_5
            elseif lDigits == 6 then
                display.smua.digits = display.DIGITS_5_5
            elseif lDigits == 7 then
                display.smua.digits = display.DIGITS_6_5
            else
                gErrorQueue.Add(-222)
            end
        end
        -- DISPlay:DIGits?
        gCurrentRoot.mQuery.mParameters = {gParserTable.mParseDigits}
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(tostring(lParameters[1] or math.ceil(display.smua.digits)))
        end
        
        -- DISPlay:WINDow1:ATTRibutes?
        gCurrentRoot = gCommandTree["DISPLAY"]["WINDOW1"]["ATTRIBUTES"]
        gCurrentRoot.mQuery.mExecute = function ()
            Print('"00000000000000000000"')
        end
        
        -- DISPlay:WINDow2:ATTRibutes?
        gCurrentRoot = gCommandTree["DISPLAY"]["WINDOW2"]["ATTRIBUTES"]
        gCurrentRoot.mQuery.mExecute = function ()
            Print('"00000000000000000000000000000000"')
        end
        
        -----------------------------------------------------------------------
        -- FORMAT subsystem commands
        -----------------------------------------------------------------------
        
        -- FORMat[:DATA] <type>[, <length>]
        gCurrentRoot = gCommandTree["FORMAT"]["DATA"]
        gCurrentRoot.mCommand.mParameters =
        {
            gParserTable.mParseFormat,
            {mParse = gParserTable.ParseParameterNRf, mOptional = true},
        }
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            lFormat = lParameters[1]
            lSize = lParameters[2]
        
            if lSize and lSize ~= 32 and lSize ~= 64 then
                gErrorQueue.Add(-224)
            else
                if lFormat == "ASC" then
                    format.data = gAscii
                    gStateVariables.Form_Data_Type = lFormat
                elseif lFormat == "SRE" then
                    format.data = format.SREAL
                    gStateVariables.Form_Data_Type = lFormat
                elseif lFormat == "REAL" and lSize == 64 then
                    format.data = format.REAL64
                    gStateVariables.Form_Data_Type = "REAL,64"
                else
                    format.data = format.REAL32
                    gStateVariables.Form_Data_Type = "REAL,32"
                end
            end
        end
        -- FORMat[:DATA]?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gStateVariables.Form_Data_Type)
        end
        
        -- FORMat:BORDer <name>
        gCurrentRoot = gCommandTree["FORMAT"]["BORDER"]
        gCurrentRoot.mCommand.mParameters =
        {
            {
                mParse = gParserTable.ParseParameterName,
                mNames =
                {
                    ["NORMAL"]      = format.NORMAL,
                    ["NORM"]        = format.NORMAL,
                    ["SWAPPED"]     = format.SWAPPED,
                    ["SWAP"]        = format.SWAPPED,
                }
            }
        }
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            format.byteorder = lParameters[1]
        end
        -- FORMat:BORDer?
        gCurrentRoot.mQuery.mExecute = function ()
            if format.byteorder == 0 then
                Print("NORM")
            elseif format.byteorder == 1 then
                Print("SWAP")
            end
        end
        
        -- FORMat:ELEMents[:SENSe[1]] <item list>
        gCurrentRoot = gCommandTree["FORMAT"]["ELEMENTS"]["SENSE1"]
        gCurrentRoot.mCommand.mParameters =
        {
            gParserTable.mParseElement,
        }
        for lIndex = 2, 99 do
            gCurrentRoot.mCommand.mParameters[lIndex] = gParserTable.mParseElementOptional
        end
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            gStateVariables.Form_Elem_Sens1.VOLT = false
            gStateVariables.Form_Elem_Sens1.CURR = false
            gStateVariables.Form_Elem_Sens1.RES  = false
            gStateVariables.Form_Elem_Sens1.TIME = false
            gStateVariables.Form_Elem_Sens1.STAT = false
        
            for lIndex, lValue in ipairs(lParameters) do
                gStateVariables.Form_Elem_Sens1[lValue] = true
            end
        end
        -- FORMat:ELEMents[:SENSe[1]]?
        gCurrentRoot.mQuery.mExecute = function ()
            local lSeparate = ""
        
            if gStateVariables.Form_Elem_Sens1.VOLT then
                Print("VOLT")
                lSeparate = ","
            end
            if gStateVariables.Form_Elem_Sens1.CURR then
                Print(lSeparate)
                Print("CURR")
                lSeparate = ","
            end
            if gStateVariables.Form_Elem_Sens1.RES then
                Print(lSeparate)
                Print("RES")
                lSeparate = ","
            end
            if gStateVariables.Form_Elem_Sens1.TIME then
                Print(lSeparate)
                Print("TIME")
                lSeparate = ","
            end
            if gStateVariables.Form_Elem_Sens1.STAT then
                Print(lSeparate)
                Print("STAT")
            end
        end
        
        -- FORMat:SREGister <name>
        gCurrentRoot = gCommandTree["FORMAT"]["SREGISTER"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mDataFormat
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            gStateVariables.Form_Sreg = lParameters[1]
        end
        -- FORMat:SREGister?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gStateVariables.Form_Sreg)
        end
        
        -- FORMat:ELEMents:CALCulate <item list>
        gCurrentRoot = gCommandTree["FORMAT"]["ELEMENTS"]["CALCULATE"]
        gCurrentRoot.mCommand.mParameters =
        {
            gParserTable.mParseCalcElement,
        }
        for lIndex = 2, 99 do
            gCurrentRoot.mCommand.mParameters[lIndex] = gParserTable.mParseCalcElementOptional
        end
        gCurrentRoot.mCommand.mExecute = function (lParameters)
        
            gStateVariables.Form_Elem_Calc.TIME = false
            gStateVariables.Form_Elem_Calc.STAT = false
            gStateVariables.Form_Elem_Calc.CALC = false
        
            for lIndex, lValue in ipairs(lParameters) do
                gStateVariables.Form_Elem_Calc[lValue] = true
            end
        end
        -- FORMat:ELEMents:CALCulate?
        -- NOTE: The 2400 doesn't actually implement this. The 2400 incorrectly
        --       provides the form:elem:sense1 query results when this query is
        --       executed.
        gCurrentRoot.mQuery.mExecute = function ()
            local lSeparate = ""
        
            if gStateVariables.Form_Elem_Calc.TIME then
                Print("TIME")
                lSeparate = ","
            end
            if gStateVariables.Form_Elem_Calc.STAT then
                Print(lSeparate)
                Print("STAT")
                lSeparate = ","
            end
            if gStateVariables.Form_Elem_Calc.CALC then
                Print(lSeparate)
                Print("CALC")
            end
        end
        
        -- FORMat:SOURce2 <name>
        gCurrentRoot = gCommandTree["FORMAT"]["SOURCE2"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mDataFormat
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            gStateVariables.Form_Sour2 = lParameters[1]
        end
        -- FORMat:SOURce2?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gStateVariables.Form_Sour2)
        end
        
        -----------------------------------------------------------------------
        -- OUTPUT subsystem commands
        -----------------------------------------------------------------------
        
        -- OUTPut[1]:STATe <b>
        gCurrentRoot = gCommandTree["OUTPUT"]["STATE"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mBoolean
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            if lParameters[1] then
                -- Turn on the output without delay
                if gAccessors.mGetSourceOutput() == 0 then
                    SetWithoutDelay(SmuOn)
                    local lError = errorqueue.next()
                    if lError == 5041 or lError == 802 then
                        gErrorQueue.Add(802)
                    end
                end
            else
                smua.abort()
                gAbortExecuted = true
                gAccessors.mSetSourceOutput(0)
            end
        end
        -- OUTPut[1]:STATe?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gResponseValues[gAccessors.mGetSourceOutput() == 1])
        end
        
        -- OUTPut[1]:SMODe <name>
        gCurrentRoot = gCommandTree["OUTPUT"]["SMODE"]
        gCurrentRoot.mCommand.mParameters =
        {
            {
                mParse = gParserTable.ParseParameterName,
                mNames =
                {
                    ["NORMAL"]      = "NORM",
                    ["NORM"]        = "NORM",
                    ["HIMPEDANCE"]  = "HIMP",
                    ["HIMP"]        = "HIMP",
                    ["ZERO"]        = "ZERO",
                    ["GUARD"]       = "GUAR",
                    ["GUAR"]        = "GUAR",
                }
            }
        }
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            gStateVariables.Outp_Smod = lParameters[1]
            if lParameters[1] == "NORM" then
                gSource.offfunc = gDCVOLTS
                -- .5% of present current range
                -- gSource.offlimiti = .005 * gAccessors.mGetSourceRangei()
                gSource.offmode = smua.OUTPUT_NORMAL
            elseif lParameters[1] == "HIMP" then
                gSource.offmode = smua.OUTPUT_HIGH_Z
            elseif lParameters[1] == "ZERO" then
                gSource.offmode = smua.OUTPUT_ZERO
            elseif lParameters[1] == "GUAR" then
                gSource.offfunc = gDCAMPS
                -- .5% of present voltage range
                -- gSource.offlimitv = .005 * gAccessors.mGetSourceRangev()
                gSource.offmode = smua.OUTPUT_NORMAL
            end
        end
        -- OUTPut[1]:SMODe?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gStateVariables.Outp_Smod)
        end
        
        -- OUTPut[1]:ENABle[:STATe] <b>
        gCurrentRoot = gCommandTree["OUTPUT"]["ENABLE"]["STATE"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mBoolean
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            if lParameters[1] then
                gSource.outputenableaction = smua.OE_OUTPUT_OFF
            else
                gSource.outputenableaction = smua.OE_NONE
            end
        end
        -- OUTPut[1]:ENABle[:STATe]?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gResponseValues[gSource.outputenableaction == 1])
        end
        
        -- OUTPut[1]:ENABle:TRIPped?
        -- Read DIGIO piin 24 OE/Interlock
        gCurrentRoot = gCommandTree["OUTPUT"]["ENABLE"]["TRIPPED"]
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gResponseValues[bit.test(gStatusMeasurement.condition, 11 + 1)])
        end
        
        -- OUTPut[1]:INTerlock:STATe <b>
        gCurrentRoot = gCommandTree["OUTPUT"]["INTERLOCK"]["STATE"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mBoolean
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            if lParameters[1] then
                gStateVariables.Outp_Interlock = 1
            else
                gStateVariables.Outp_Interlock = 0
            end
        end
        -- OUTPut[1]:INTerlock:STATe?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gResponseValues[gStateVariables.Outp_Interlock == 1])
        end
        
        -----------------------------------------------------------------------
        -- ROUTE subsystem commands
        -----------------------------------------------------------------------
        
        -- ROUTe:TERMinals <name> FRONt or REAR
        gCurrentRoot = gCommandTree["ROUTE"]["TERMINALS"]
        gCurrentRoot.mCommand.mParameters =
        {
            {
                mParse = gParserTable.ParseParameterName,
                mNames =
                {
                    -- This is not a typo. "FRONT" is accepted but the setting is
                    -- always taken as "REAR"
                    ["REAR"]        = "REAR",
                    ["FRONT"]       = "REAR",
                    ["FRON"]        = "REAR",
                }
            }
        }
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            gStateVariables.Route_Term = lParameters[1]
        end
        -- ROUTe:TERMinals?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gStateVariables.Route_Term)
        end
        
        -----------------------------------------------------------------------
        -- SOURCE subsystem commands
        -----------------------------------------------------------------------
        
        -- SOURce[1]:CLEar
        gCurrentRoot = gCommandTree["SOURCE1"]["CLEAR"]
        gCurrentRoot.mCommand.mExecute = function ()
            gAccessors.mSetSourceOutput(0)
        end
        
        -- SOURce[1]:CLEar:AUTO <b>
        gCurrentRoot = gCommandTree["SOURCE1"]["CLEAR"]["AUTO"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mBoolean
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            gStateVariables.Sour_Cle_Auto_State = lParameters[1]
        end
        -- SOURce[1]:CLEar:AUTO?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gResponseValues[gStateVariables.Sour_Cle_Auto_State])
        end
        
        -- SOURce[1]:CLEar:AUTO:MODE <name>
        gCurrentRoot = gCommandTree["SOURCE1"]["CLEAR"]["AUTO"]["MODE"]
        gCurrentRoot.mCommand.mParameters =
        {
            {
                mParse = gParserTable.ParseParameterName,
                mNames =
                {
                    ["ALWAYS"]      = "ALW",
                    ["ALW"]         = "ALW",
                    --["TCOUNT"]      = "TCO",
                    --["TCO"]         = "TCO",
                }
            }
        }
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            gStateVariables.Sour_Cle_Auto_Mode = lParameters[1]
        end
        -- SOURce[1]:CLEar:AUTO:MODE?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gStateVariables.Sour_Cle_Auto_Mode)
        end
        
        -- SOURce[1]:FUNCtion[:MODE] <name>
        gCurrentRoot = gCommandTree["SOURCE1"]["FUNCTION"]["MODE"]
        gCurrentRoot.mCommand.mParameters =
        {
            {
                mParse = gParserTable.ParseParameterName,
                mNames =
                {
                    ["VOLTAGE"]     = "VOLT",
                    ["VOLT"]        = "VOLT",
                    ["CURRENT"]     = "CURR",
                    ["CURR"]        = "CURR",
                    ["MEMORY"]      = "MEM",
                    ["MEM"]         = "MEM",
                }
            }
        }
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            gStateVariables.Sour_Func_Mode = lParameters[1]
            if lParameters[1] == "VOLT" then
                --Change the source function without delay
                if gAccessors.mGetSourceFunc() ~= gDCVOLTS then
                    gAccessors.mSetSourceOutput(0)
                    SetWithoutDelay(function () gAccessors.mSetSourceFunc(gDCVOLTS) end)
                end
                lMemScratch.Sour_Func_Mode = gDCVOLTS
            elseif lParameters[1] == "CURR" then
                --Change the source function without delay
                if gAccessors.mGetSourceFunc() ~= gDCAMPS then
                    gAccessors.mSetSourceOutput(0)
                    SetWithoutDelay(function () gAccessors.mSetSourceFunc(gDCAMPS) end)
                end
                lMemScratch.Sour_Func_Mode = gDCAMPS
            else -- "MEM"
                lMemScratch.Sour_Func_Mode = gAccessors.mGetSourceFunc()
            end
        end
        -- SOURce[1]:FUNCtion[:MODE]?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gStateVariables.Sour_Func_Mode)
        end
        
        -- SOURce[1]:DELay <n>
        gCurrentRoot = gCommandTree["SOURCE1"]["DELAY"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mDelay
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lDelay = lParameters[1]
            if lDelay >= 0 and lDelay <= 9999.999 then
                gStateVariables.Sour_Del = lDelay
                lMemScratch.Sour_Del = lDelay
                gStateVariables.Sour_Del_Auto = false
                lMemScratch.Sour_Del_Auto = false
                gAccessors.mSetSourceDelay(0)
            else
                gErrorQueue.Add(-222)
            end
        end
        -- SOURce[1]:DELay?
        gCurrentRoot.mQuery.mParameters = {gParserTable.mParseDelay}
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(string.format("%.5f",lParameters[1] or gStateVariables.Sour_Del))
        end
        
        -- SOURce[1]:DELay:AUTO <b>
        gCurrentRoot = gCommandTree["SOURCE1"]["DELAY"]["AUTO"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mBoolean
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            gStateVariables.Sour_Del_Auto = lParameters[1]
            lMemScratch.Sour_Del_Auto = lParameters[1]
            if lParameters[1] then
                gAccessors.mSetSourceDelay(smua.DELAY_AUTO)
            else
                gAccessors.mSetSourceDelay(0)
            end
        end
        -- SOURce[1]:DELay:AUTO?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gResponseValues[gStateVariables.Sour_Del_Auto])
        end
        
        -- SOURce[1]:CURRent:MODE <name>
        gCurrentRoot = gCommandTree["SOURCE1"]["CURRENT"]["MODE"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mFunctionMode
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            gStateVariables.Sour_Curr_Mode = lParameters[1]
        end
        -- SOURce[1]:CURRent:MODE?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gStateVariables.Sour_Curr_Mode)
        end
        
        -- SOURce[1]:VOLTage:MODE <name>
        gCurrentRoot = gCommandTree["SOURCE1"]["VOLTAGE"]["MODE"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mFunctionMode
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            gStateVariables.Sour_Volt_Mode = lParameters[1]
        end
        -- SOURce[1]:VOLTage:MODE?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gStateVariables.Sour_Volt_Mode)
        end
        
        -- SOURce[1]:CURRent:RANGe <n>|UP|DOWN
        gCurrentRoot = gCommandTree["SOURCE1"]["CURRENT"]["RANGE"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mCurrentRange
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lRange = lParameters[1]
            local lLevel = gMathAbs(gAccessors.mGetSourceLeveli())
        
            if lRange == "UP" then
                lRange = gAccessors.mGetSourceRangei() * 1.1
                if lRange > gOperatingBoundaries.mMaximumCurrentRange then
                    -- We are on the top range
                    return
                end
            elseif lRange == "DOWN" then
                if gAccessors.mGetSourceRangei() <= gOperatingBoundaries.mMinimumCurrentRange then
                    -- We are on the bottom range
                    return
                end
                lRange = gAccessors.mGetSourceRangei() * 0.09
            else
                lRange = gMathAbs(lRange)
            end
            if lRange <= gOperatingBoundaries.mMaximumCurrentRange then
                if lRange < lLevel then
                    for lIndex, lValue in ipairs(gRangeTable.mCurrent) do
                        if lRange < lValue * 1.01 then
                            if lLevel > lValue * 1.01 then
                                if gAccessors.mGetSourceLeveli() < 0 then
                                    gAccessors.mSetSourceLeveli(lValue)
                                    lMemScratch.Sour_Curr_Ampl = lValue
                                    gStateVariables.Sour_Curr_Trig_Ampl = lValue
                                else
                                    gAccessors.mSetSourceLeveli(lValue)
                                    lMemScratch.Sour_Curr_Ampl = lValue
                                    gStateVariables.Sour_Curr_Trig_Ampl = lValue
                                end
                            end
                            break
                        end
                    end
                end
        
                if gAccessors.mGetSourceLimitv() > gSafeOperatingArea.mVoltage and lRange > gSafeOperatingArea.mCurrent then
                    gAccessors.mSetSourceLimitv(gSafeOperatingArea.mVoltage)
                end
                lMemScratch.Sens_Volt_Prot = gAccessors.mGetSourceLimitv()
                if (gAccessors.mGetMeasureRangev()/gSafeOperatingArea.mVoltage) - 1 >= gEpsilon
                and lRange > gSafeOperatingArea.mCurrent then
                    gErrorQueue.Add(826)
                else
                    gAccessors.mSetSourceRangei(lRange)
                    lMemScratch.Sour_Curr_Rang = gAccessors.mGetSourceRangei()
                    lMemScratch.Sour_Curr_Rang_Auto = 0
                end
            else
                gErrorQueue.Add(-222)
            end  
        end
        -- SOURce[1]:CURRent:RANGe?
        gCurrentRoot.mQuery.mParameters = gParserTable.mCurrentRangeQuery
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(lParameters[1] or gAccessors.mGetSourceRangei())
        end
        
        -- SOURce[1]:VOLTage:RANGe <n>|UP|DOWN
        gCurrentRoot = gCommandTree["SOURCE1"]["VOLTAGE"]["RANGE"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mVoltageRange
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lRange = lParameters[1]
            local lLevel = gMathAbs(gAccessors.mGetSourceLevelv())
        
            if lRange == "UP" then
                lRange = gAccessors.mGetSourceRangev() * 1.1
                if lRange > gOperatingBoundaries.mMaximumVoltageRange then
                    -- We are on the top range
                    return
                end
            elseif lRange == "DOWN" then
                if gAccessors.mGetSourceRangev() <= gOperatingBoundaries.mMinimumVoltageRange then
                    -- We are on the bottom range
                    return
                end
                lRange = gAccessors.mGetSourceRangev() * 0.09
            else
                lRange = gMathAbs(lRange)
            end
            if lRange <= gOperatingBoundaries.mMaximumVoltageRange then
                if lRange < lLevel then
                    for lIndex, lValue in ipairs(gRangeTable.mVoltage) do
                        if lRange < lValue * 1.01 then
                            if lLevel > lValue * 1.01 then
                                if gAccessors.mGetSourceLevelv() < 0 then
                                    gAccessors.mSetSourceLevelv(lValue)
                                    lMemScratch.Sour_Volt_Ampl = lValue
                                    gStateVariables.Sour_Volt_Trig_Ampl = lValue
                                else
                                    gAccessors.mSetSourceLevelv(lValue)
                                    lMemScratch.Sour_Volt_Ampl = lValue
                                    gStateVariables.Sour_Volt_Trig_Ampl = lValue
                                end
                            end
                            break
                        end
                    end
                end
        
                if gAccessors.mGetSourceLimiti() > gSafeOperatingArea.mCurrent and lRange > gSafeOperatingArea.mVoltage then
                    gAccessors.mSetSourceLimiti(gSafeOperatingArea.mCurrent)
                end
        
                lMemScratch.Sens_Curr_Prot = gAccessors.mGetSourceLimiti()
                if (gAccessors.mGetMeasureRangei()/gSafeOperatingArea.mCurrent) - 1 >= gEpsilon
                and lRange > gSafeOperatingArea.mVoltage then
                    gErrorQueue.Add(826)
                else
                    gAccessors.mSetSourceRangev(lRange)
                    lMemScratch.Sour_Volt_Rang = gAccessors.mGetSourceRangev()
                    lMemScratch.Sour_Volt_Rang_Auto = 0
                end
            else
                gErrorQueue.Add(-222)
            end
        end
        -- SOURce[1]:VOLTage:RANGe?
        gCurrentRoot.mQuery.mParameters = gParserTable.mVoltageRangeQuery
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(string.format("%.2f",lParameters[1] or gAccessors.mGetSourceRangev()))
        end
        
        -- SOURce[1]:CURRent:RANGe:AUTO <b>
        gCurrentRoot = gCommandTree["SOURCE1"]["CURRENT"]["RANGE"]["AUTO"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mBoolean
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            if lParameters[1] then
                if gAccessors.mGetSourceLeveli() > gSafeOperatingArea.mCurrent and gAccessors.mGetSourceLimitv() > gSafeOperatingArea.mVoltage then
                    gAccessors.mSetSourceLeveli(gSafeOperatingArea.mCurrent)
                    lMemScratch.Sour_Curr_Ampl = gSafeOperatingArea.mCurrent
                end
                gAccessors.mSetSourceAutoRangei(1)
                lMemScratch.Sour_Curr_Rang_Auto = 1
            else
                gAccessors.mSetSourceAutoRangei(0)
                lMemScratch.Sour_Curr_Rang_Auto = 0
            end
        end
        -- SOURce[1]:CURRent:RANGe:AUTO?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gResponseValues[gAccessors.mGetSourceAutoRangei()== 1])
        end
        
        -- SOURce[1]:VOLTage:RANGe:AUTO <b>
        gCurrentRoot = gCommandTree["SOURCE1"]["VOLTAGE"]["RANGE"]["AUTO"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mBoolean
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            if lParameters[1] then
                if gAccessors.mGetSourceLevelv() > gSafeOperatingArea.mVoltage and gAccessors.mGetSourceLimiti() > gSafeOperatingArea.mCurrent then
                    gAccessors.mSetSourceLevelv(gSafeOperatingArea.mVoltage)
                    lMemScratch.Sour_Volt_Ampl = gSafeOperatingArea.mVoltage
                end
                gAccessors.mSetSourceAutoRangev(1)
                lMemScratch.Sour_Volt_Rang_Auto = 1
            else
                gAccessors.mSetSourceAutoRangev(0)
                lMemScratch.Sour_Volt_Rang_Auto = 0
            end
        end
        -- SOURce[1]:VOLTage:RANGe:AUTO?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gResponseValues[gAccessors.mGetSourceAutoRangev() == 1])
        end
        
        -- SOURce[1]:CURRent[:LEVel][:IMMediate][:AMPLitude] <n>
        gCurrentRoot = gCommandTree["SOURCE1"]["CURRENT"]["LEVEL"]["IMMEDIATE"]["AMPLITUDE"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mCurrentLevel
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lLevel = lParameters[1]
            -- Allowable amplitude = range + 1%(range)
            local lAllowableLevel = gAccessors.mGetSourceRangei() * 1.01
        
            if gMathAbs(lLevel) <= gOperatingBoundaries.mMaximumCurrentLevel then
                if gAccessors.mGetSourceAutoRangei()== 1 or gMathAbs(lLevel)/lAllowableLevel - 1 <= gEpsilon then
                    if gAccessors.mGetSourceLimitv() > gSafeOperatingArea.mVoltage and gMathAbs(lLevel) > gSafeOperatingArea.mCurrent * 1.01 then
                        gAccessors.mSetSourceLimitv(gSafeOperatingArea.mVoltage)
                    end
                    if (gAccessors.mGetMeasureRangev()/gSafeOperatingArea.mVoltage) - 1 >= gEpsilon
                    and lLevel > gSafeOperatingArea.mCurrent then
                        gErrorQueue.Add(826)
                    else
                        gAccessors.mSetSourceLeveli(lLevel)
                        gStateVariables.Sour_Curr_Trig_Ampl = lLevel
                        lMemScratch.Sour_Curr_Ampl = lLevel
                    end
                    lMemScratch.Sens_Volt_Prot = gAccessors.mGetSourceLimitv()
                else
                    gErrorQueue.Add(-221)
                end
            else
                gErrorQueue.Add(-222)
            end
        end
        -- SOURce[1]:CURRent[:LEVel][:IMMediate][:AMPLitude]?
        gCurrentRoot.mQuery.mParameters = gParserTable.mCurrentLevelQuery
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(lParameters[1] or gAccessors.mGetSourceLeveli())
        end
        
        -- SOURce[1]:VOLTage[:LEVel][:IMMediate][:AMPLitude] <n>
        gCurrentRoot = gCommandTree["SOURCE1"]["VOLTAGE"]["LEVEL"]["IMMEDIATE"]["AMPLITUDE"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mVoltageLevel
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lLevel = lParameters[1]
            -- Allowable amplitude = range + 1%(range)
            local lAllowableLevel = gAccessors.mGetSourceRangev() * 1.01
        
            if gMathAbs(lLevel) <= gOperatingBoundaries.mMaximumVoltageLevel then
                if gAccessors.mGetSourceAutoRangev() == 1 or gMathAbs(lLevel)/lAllowableLevel - 1 <= gEpsilon then
                    if gAccessors.mGetSourceLimiti() > gSafeOperatingArea.mCurrent and gMathAbs(lLevel) > gSafeOperatingArea.mVoltage * 1.01 then
                        gAccessors.mSetSourceLimiti(gSafeOperatingArea.mCurrent)
                    end
                    if (gAccessors.mGetMeasureRangei()/gSafeOperatingArea.mCurrent) - 1 >= gEpsilon
                    and lLevel > gSafeOperatingArea.mVoltage then
                        gErrorQueue.Add(826)
                    else
                        gAccessors.mSetSourceLevelv(lLevel)
                        gStateVariables.Sour_Volt_Trig_Ampl = lLevel
                        lMemScratch.Sour_Volt_Ampl = lLevel
                    end
                    lMemScratch.Sens_Curr_Prot = gAccessors.mGetSourceLimiti()
                else
                    gErrorQueue.Add(-221)
                end
            else
                gErrorQueue.Add(-222)
            end
        end
        -- SOURce[1]:VOLTage[:LEVel][:IMMediate][:AMPLitude]?
        gCurrentRoot.mQuery.mParameters = gParserTable.mVoltageLevelQuery
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(lParameters[1] or gAccessors.mGetSourceLevelv())
        end
        
        -- SOURce[1]:CURRent[:LEVel]:TRIGgered[:AMPLitude] <n>
        gCurrentRoot = gCommandTree["SOURCE1"]["CURRENT"]["LEVEL"]["TRIGGERED"]["AMPLITUDE"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mCurrentLevel
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lLevel = lParameters[1]
            -- Allowable amplitude = range + 1%(range)
            local lAllowableLevel = gAccessors.mGetSourceRangei() * 1.01
        
            if gMathAbs(lLevel) <= gOperatingBoundaries.mMaximumCurrentLevel then
                if gAccessors.mGetSourceAutoRangei()== 1 or gMathAbs(lLevel)/lAllowableLevel - 1 <= gEpsilon then
                    if gAccessors.mGetSourceLimitv() > gSafeOperatingArea.mVoltage and gMathAbs(lLevel) > gSafeOperatingArea.mCurrent * 1.01 then
                        gAccessors.mSetSourceLimitv(gSafeOperatingArea.mVoltage)
                    end
                    gStateVariables.Sour_Curr_Trig_Ampl = lLevel
                else
                    gErrorQueue.Add(-221)
                end
            else
                gErrorQueue.Add(-222)
            end
        end
        -- SOURce[1]:CURRent[:LEVel]:TRIGgered[:AMPLitude]?
        gCurrentRoot.mQuery.mParameters = gParserTable.mCurrentLevelQuery
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(lParameters[1] or gStateVariables.Sour_Curr_Trig_Ampl)
        end
        
        -- SOURce[1]:VOLTage[:LEVel]:TRIGgered[:AMPLitude] <n>
        gCurrentRoot = gCommandTree["SOURCE1"]["VOLTAGE"]["LEVEL"]["TRIGGERED"]["AMPLITUDE"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mVoltageLevel
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lLevel = lParameters[1]
            -- Allowable amplitude = range + 1%(range)
            local lAllowableLevel = gAccessors.mGetSourceRangev() * 1.01
        
            if gMathAbs(lLevel) <= gOperatingBoundaries.mMaximumVoltageLevel then
                if gAccessors.mGetSourceAutoRangev() == 1 or gMathAbs(lLevel)/lAllowableLevel - 1 <= gEpsilon then
                    if gAccessors.mGetSourceLimiti() > gSafeOperatingArea.mCurrent and gMathAbs(lLevel) > gSafeOperatingArea.mVoltage * 1.01 then
                        gAccessors.mSetSourceLimiti(gSafeOperatingArea.mCurrent)
                    end
                    gStateVariables.Sour_Volt_Trig_Ampl = lLevel
                else
                    gErrorQueue.Add(-221)
                end
            else
                gErrorQueue.Add(-222)
            end
        end
        -- SOURce[1]:VOLTage[:LEVel]:TRIGgered[:AMPLitude]?
        gCurrentRoot.mQuery.mParameters = gParserTable.mVoltageLevelQuery
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(lParameters[1] or gStateVariables.Sour_Volt_Trig_Ampl)
        end
        
        -- SOURce[1]:SWEep:RANGing <name>
        gCurrentRoot = gCommandTree["SOURCE1"]["SWEEP"]["RANGING"]
        gCurrentRoot.mCommand.mParameters =
        {
            {
                mParse = gParserTable.ParseParameterName,
                mNames =
                {
                    ["BEST"]        = "BEST",
                    ["AUTO"]        = "AUTO",
                    ["FIXED"]       = "FIX",
                    ["FIX"]         = "FIX",
                }
            }
        }
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            gStateVariables.Sour_Swe_Rang = lParameters[1]
        end
        -- SOURce[1]:SWEep:RANGing?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gStateVariables.Sour_Swe_Rang)
        end
        
        -- SOURce[1]:SWEep:SPACing <name>
        gCurrentRoot = gCommandTree["SOURCE1"]["SWEEP"]["SPACING"]
        gCurrentRoot.mCommand.mParameters =
        {
            {
                mParse = gParserTable.ParseParameterName,
                mNames =
                {
                    ["LINEAR"]      = "LIN",
                    ["LIN"]         = "LIN",
                    ["LOGARITHMIC"] = "LOG",
                    ["LOG"]         = "LOG",
                }
            }
        }
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            gStateVariables.Sour_Swe_Spac = lParameters[1]
        end
        -- SOURce[1]:SWEep:SPACing?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gStateVariables.Sour_Swe_Spac)
        end
        
        -- SOURce[1]:CURRent:STARt <n>
        gCurrentRoot = gCommandTree["SOURCE1"]["CURRENT"]["START"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mCurrentLevel
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lStart = lParameters[1]
        
            if lStart >= gOperatingBoundaries.mMinimumCurrentLevel and lStart <= gOperatingBoundaries.mMaximumCurrentLevel then
                gStateVariables.Sour_Curr_Start = lStart
                gStateVariables.Sour_Curr_Cent = (gStateVariables.Sour_Curr_Start + gStateVariables.Sour_Curr_Stop) / 2
                gStateVariables.Sour_Curr_Span = gStateVariables.Sour_Curr_Stop - gStateVariables.Sour_Curr_Start
                -- Update current step and points
                UpdateCurrentStep()
            else
                gErrorQueue.Add(-222)
            end
        end
        -- SOURce[1]:CURRent:STARt?
        gCurrentRoot.mQuery.mParameters = gParserTable.mCurrentLevelQuery
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(lParameters[1] or gStateVariables.Sour_Curr_Start)
        end
        
        -- SOURce[1]:CURRent:STOP <n>
        gCurrentRoot = gCommandTree["SOURCE1"]["CURRENT"]["STOP"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mCurrentLevel
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lStop = lParameters[1]
        
            if lStop >= gOperatingBoundaries.mMinimumCurrentLevel and lStop <= gOperatingBoundaries.mMaximumCurrentLevel then
                gStateVariables.Sour_Curr_Stop = lStop
                gStateVariables.Sour_Curr_Cent = (gStateVariables.Sour_Curr_Start + gStateVariables.Sour_Curr_Stop) / 2
                gStateVariables.Sour_Curr_Span = gStateVariables.Sour_Curr_Stop - gStateVariables.Sour_Curr_Start
                -- Update current step and points
                UpdateCurrentStep()
            else
                gErrorQueue.Add(-222)
            end
        end
        -- SOURce[1]:CURRent:STOP?
        gCurrentRoot.mQuery.mParameters = gParserTable.mCurrentLevelQuery
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(lParameters[1] or gStateVariables.Sour_Curr_Stop)
        end
        
        -- SOURce[1]:VOLTage:STARt <n>
        gCurrentRoot = gCommandTree["SOURCE1"]["VOLTAGE"]["START"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mVoltageLevel
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lStart = lParameters[1]
        
            if lStart >= gOperatingBoundaries.mMinimumVoltageLevel and lStart <= gOperatingBoundaries.mMaximumVoltageLevel then
                gStateVariables.Sour_Volt_Start = lStart
                gStateVariables.Sour_Volt_Cent = (gStateVariables.Sour_Volt_Start + gStateVariables.Sour_Volt_Stop) / 2
                gStateVariables.Sour_Volt_Span = gStateVariables.Sour_Volt_Stop - gStateVariables.Sour_Volt_Start
                -- Update voltage step and points
                UpdateVoltageStep()
            else
                gErrorQueue.Add(-222)
            end
        end
        -- SOURce[1]:VOLTage:STARt?
        gCurrentRoot.mQuery.mParameters = gParserTable.mVoltageLevelQuery
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(lParameters[1] or gStateVariables.Sour_Volt_Start)
        end
        
        -- SOURce[1]:VOLTage:STOP <n>
        gCurrentRoot = gCommandTree["SOURCE1"]["VOLTAGE"]["STOP"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mVoltageLevel
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lStop = lParameters[1]
        
            if lStop >= gOperatingBoundaries.mMinimumVoltageLevel and lStop <= gOperatingBoundaries.mMaximumVoltageLevel then
                gStateVariables.Sour_Volt_Stop = lStop
                gStateVariables.Sour_Volt_Cent = (gStateVariables.Sour_Volt_Start + gStateVariables.Sour_Volt_Stop) / 2
                gStateVariables.Sour_Volt_Span = gStateVariables.Sour_Volt_Stop - gStateVariables.Sour_Volt_Start
                -- Update voltage step and points
                UpdateVoltageStep()
            else
                gErrorQueue.Add(-222)
            end
        end
        -- SOURce[1]:VOLTage:STOP?
        gCurrentRoot.mQuery.mParameters = gParserTable.mVoltageLevelQuery
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(lParameters[1] or gStateVariables.Sour_Volt_Stop)
        end
        
        -- SOURce[1]:CURRent:CENTer <n>
        gCurrentRoot = gCommandTree["SOURCE1"]["CURRENT"]["CENTER"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mCurrentLevel
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lCenter = lParameters[1]
            local lHalfSpan = gStateVariables.Sour_Curr_Span / 2
        
            if lCenter - gMathAbs(lHalfSpan) >= gOperatingBoundaries.mMinimumCurrentLevel
                    and lCenter + gMathAbs(lHalfSpan) <= gOperatingBoundaries.mMaximumCurrentLevel then
                gStateVariables.Sour_Curr_Cent = lCenter
                gStateVariables.Sour_Curr_Start = lCenter - lHalfSpan
                gStateVariables.Sour_Curr_Stop = lCenter + lHalfSpan
            else
                gErrorQueue.Add(-222)
            end
        end
        -- SOURce[1]:CURRent:CENTer?
        gCurrentRoot.mQuery.mParameters = gParserTable.mCurrentLevelQuery
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(lParameters[1] or gStateVariables.Sour_Curr_Cent)
        end
        
        -- SOURce[1]:VOLTage:CENTer <n>
        gCurrentRoot = gCommandTree["SOURCE1"]["VOLTAGE"]["CENTER"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mVoltageLevel
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lCenter = lParameters[1]
            local lHalfSpan = gStateVariables.Sour_Volt_Span / 2
        
            if lCenter - gMathAbs(lHalfSpan) >= gOperatingBoundaries.mMinimumVoltageLevel
                    and lCenter + gMathAbs(lHalfSpan) <= gOperatingBoundaries.mMaximumVoltageLevel then
                gStateVariables.Sour_Volt_Cent = lCenter
                gStateVariables.Sour_Volt_Start = lCenter - lHalfSpan
                gStateVariables.Sour_Volt_Stop = lCenter + lHalfSpan
            else
                gErrorQueue.Add(-222)
            end
        end
        -- SOURce[1]:VOLTage:CENTer?
        gCurrentRoot.mQuery.mParameters = gParserTable.mVoltageLevelQuery
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(lParameters[1] or gStateVariables.Sour_Volt_Cent)
        end
        
        -- SOURce[1]:CURRent:SPAN <n>
        gCurrentRoot = gCommandTree["SOURCE1"]["CURRENT"]["SPAN"]
        gCurrentRoot.mCommand.mParameters =
        {
            {
                mParse = gParserTable.ParseParameterChoice,
                mData =
                {
                    gParserTable.mParseNRf,
                    gParserTable.mParseCurrentSpan,
                    gParserTable.mParseInfinity,
                }
            }
        }
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lCenter = gStateVariables.Sour_Curr_Cent
            local lHalfSpan = lParameters[1] / 2
        
            if lCenter - gMathAbs(lHalfSpan) >= gOperatingBoundaries.mMinimumCurrentLevel
                    and lCenter + gMathAbs(lHalfSpan) <= gOperatingBoundaries.mMaximumCurrentLevel then
                gStateVariables.Sour_Curr_Span = lParameters[1]
                gStateVariables.Sour_Curr_Start = lCenter - lHalfSpan
                gStateVariables.Sour_Curr_Stop = lCenter + lHalfSpan
                -- Update current step and points
                UpdateCurrentStep()
            else
                gErrorQueue.Add(-222)
            end
        end
        -- SOURce[1]:CURRent:SPAN?
        gCurrentRoot.mQuery.mParameters = {gParserTable.mParseCurrentSpan}
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(lParameters[1] or gStateVariables.Sour_Curr_Span)
        end
        
        -- SOURce[1]:VOLTage:SPAN <n>
        gCurrentRoot = gCommandTree["SOURCE1"]["VOLTAGE"]["SPAN"]
        gCurrentRoot.mCommand.mParameters =
        {
            {
                mParse = gParserTable.ParseParameterChoice,
                mData =
                {
                    gParserTable.mParseNRf,
                    gParserTable.mParseVoltageSpan,
                    gParserTable.mParseInfinity,
                }
            }
        }
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lCenter = gStateVariables.Sour_Volt_Cent
            local lHalfSpan = lParameters[1] / 2
        
            if lCenter - gMathAbs(lHalfSpan) >= gOperatingBoundaries.mMinimumVoltageLevel
                    and lCenter + gMathAbs(lHalfSpan) <= gOperatingBoundaries.mMaximumVoltageLevel then
                gStateVariables.Sour_Volt_Span = lParameters[1]
                gStateVariables.Sour_Volt_Start = lCenter - lHalfSpan
                gStateVariables.Sour_Volt_Stop = lCenter + lHalfSpan
                -- Update voltage step and points
                UpdateVoltageStep()
            else
                gErrorQueue.Add(-222)
            end
        end
        -- SOURce[1]:VOLTage:SPAN?
        gCurrentRoot.mQuery.mParameters = {gParserTable.mParseVoltageSpan}
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(lParameters[1] or gStateVariables.Sour_Volt_Span)
        end
        
        -- SOURce[1]:CURRent:STEP <n>
        gCurrentRoot = gCommandTree["SOURCE1"]["CURRENT"]["STEP"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mNRfMinMaxDef
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lStep = lParameters[1]
            local lStepMax, lStepMin
        
            -- Calculate Minimum and Maximum step size depending on the Start and Stop values
            if gStateVariables.Sour_Curr_Stop > gStateVariables.Sour_Curr_Start then
                lStepMax = gStateVariables.Sour_Curr_Span
                lStepMin = (gStateVariables.Sour_Curr_Span) / 2499
            else
                lStepMin = gStateVariables.Sour_Curr_Span
                lStepMax = (gStateVariables.Sour_Curr_Span) / 2499
            end
        
            if lStep == "MAX" then
               gStateVariables.Sour_Curr_Step = lStepMax
            elseif lStep == "MIN" then
               gStateVariables.Sour_Curr_Step = lStepMin
            elseif lStep == "DEF" then
               gStateVariables.Sour_Curr_Step = 0
            else
                if lStep >= lStepMin and lStep <= lStepMax then
                    gStateVariables.Sour_Curr_Step = lStep
                else
                    gErrorQueue.Add(-222)
                end
            end
        
            -- Update Sweep Points
            if gStateVariables.Sour_Curr_Step == 0 then -- to avoid NAN
                gStateVariables.Sour_Swe_Poin = 2500
            else
                gStateVariables.Sour_Swe_Poin =
                        math.floor((gStateVariables.Sour_Curr_Span / gStateVariables.Sour_Curr_Step) + 1)
                if gStateVariables.Sour_Swe_Poin > 2500 then
                    gStateVariables.Sour_Swe_Poin = 2500
                end
            end
        end
        -- SOURce[1]:CURRent:STEP?
        gCurrentRoot.mQuery.mParameters = gParserTable.mMinMaxDef
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            if lParameters[1] then
                local lStepMax, lStepMin
        
                -- Calculate Minimum and Maximum step size depending on the Start and Stop values
                if gStateVariables.Sour_Curr_Stop > gStateVariables.Sour_Curr_Start then
                    lStepMax = gStateVariables.Sour_Curr_Span
                    lStepMin = (gStateVariables.Sour_Curr_Span) / 2499
                else
                    lStepMin = gStateVariables.Sour_Curr_Span
                    lStepMax = (gStateVariables.Sour_Curr_Span) / 2499
                end
        
                if lParameters[1] == "MAX" then
                    Print(lStepMax)
                elseif lParameters[1] == "MIN" then
                    Print(lStepMin)
                elseif lParameters[1] == "DEF" then
                    Print(0)
                else
                    gErrorQueue.Add(-102)
                end
            else
               Print(gStateVariables.Sour_Curr_Step)
            end
        end
        
        -- SOURce[1]:VOLTage:STEP <n>
        gCurrentRoot = gCommandTree["SOURCE1"]["VOLTAGE"]["STEP"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mNRfMinMaxDef
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lStep = lParameters[1]
            local lStepMax, lStepMin
        
            -- Calculate Minimum and Maximum step size depending on the Start and Stop values
            if gStateVariables.Sour_Volt_Stop > gStateVariables.Sour_Volt_Start then
                lStepMax = gStateVariables.Sour_Volt_Span
                lStepMin = gStateVariables.Sour_Volt_Span / 2499
            else
                lStepMin = gStateVariables.Sour_Volt_Span
                lStepMax = gStateVariables.Sour_Volt_Span / 2499
            end
        
            if lStep == "MAX" then
               gStateVariables.Sour_Volt_Step = lStepMax
            elseif lStep == "MIN" then
               gStateVariables.Sour_Volt_Step = lStepMin
            elseif lStep == "DEF" then
               gStateVariables.Sour_Volt_Step = 0
            else
                if lStep >= lStepMin and lStep <= lStepMax then
                    gStateVariables.Sour_Volt_Step = lStep
                else
                    gErrorQueue.Add(-222)
                end
            end
        
            -- Update Sweep Points
            if gStateVariables.Sour_Volt_Step == 0 then  -- to avoid NAN
                gStateVariables.Sour_Swe_Poin = 2500
            else
                gStateVariables.Sour_Swe_Poin =
                        math.floor((gStateVariables.Sour_Volt_Span / gStateVariables.Sour_Volt_Step) + 1)
                if gStateVariables.Sour_Swe_Poin > 2500 then
                    gStateVariables.Sour_Swe_Poin = 2500
                end
            end
        end
        -- SOURce[1]:VOLTage:STEP?
        gCurrentRoot.mQuery.mParameters = gParserTable.mMinMaxDef
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            if lParameters[1] then
                local lStepMax, lStepMin
        
                -- Calculate Minimum and Maximum step size depending on the Start and Stop values
                if gStateVariables.Sour_Volt_Stop > gStateVariables.Sour_Volt_Start then
                    lStepMax = gStateVariables.Sour_Volt_Span
                    lStepMin = gStateVariables.Sour_Volt_Span / 2499
                else
                    lStepMin = gStateVariables.Sour_Volt_Span
                    lStepMax = gStateVariables.Sour_Volt_Span / 2499
                end
        
                if lParameters[1] == "MAX" then
                    Print(lStepMax)
                elseif lParameters[1] == "MIN" then
                    Print(lStepMin)
                elseif lParameters[1] == "DEF" then
                    Print(0)
                end
            else
               Print(gStateVariables.Sour_Volt_Step)
            end
        end
        
        -- SOURce[1]:SWEep:POINts <n>
        gCurrentRoot = gCommandTree["SOURCE1"]["SWEEP"]["POINTS"]
        gCurrentRoot.mCommand.mParameters =
        {
            {
                mParse = gParserTable.ParseParameterChoice,
                mData =
                {
                    gParserTable.mParseInteger,
                    gParserTable.mParsePoints,
                    gParserTable.mParseInfinity,
                }
            }
        }
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lPoints = lParameters[1]
            if lPoints >= 2 and lPoints <= 2500 then
                gStateVariables.Sour_Swe_Poin = lPoints
                UpdateVoltageStep()
                UpdateCurrentStep()
            else
                gErrorQueue.Add(-222)
            end
        end
        -- SOURce[1]:SWEep:POINts?
        gCurrentRoot.mQuery.mParameters = {gParserTable.mParsePoints}
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(tostring(lParameters[1] or gStateVariables.Sour_Swe_Poin))
        end
        
        -- SOURce[1]:SWEep:DIRection <name>
        gCurrentRoot = gCommandTree["SOURCE1"]["SWEEP"]["DIRECTION"]
        gCurrentRoot.mCommand.mParameters =
        {
            {
                mParse = gParserTable.ParseParameterName,
                mNames =
                {
                    ["UP"]          = "UP",
                    ["DOWN"]        = "DOWN",
                }
            }
        }
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            gStateVariables.Sour_Swe_Dir = lParameters[1]
        end
        -- SOURce[1]:SWEep:DIRection?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gStateVariables.Sour_Swe_Dir)
        end
        
        -- SOURce[1]:LIST:CURRent <NRf list>
        gCurrentRoot = gCommandTree["SOURCE1"]["LIST"]["CURRENT"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mSourceList
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lAbsValue
            local lMax = 0
        
            for lIndex, lValue in ipairs(lParameters) do
                lAbsValue = gMathAbs(lValue)
                if lAbsValue > lMax then
                    if lAbsValue > gOperatingBoundaries.mMaximumCurrentLevel then
                        gErrorQueue.Add(-222)
                        return
                    end
                    lMax = lAbsValue
                end
            end
            gStateVariables.Sour_List_Curr_Values = lParameters
            gStateVariables.Sour_List_Curr_Max = lMax
        end
        -- SOURce[1]:LIST:CURRent?
        gCurrentRoot.mQuery.mExecute = function ()
            local lData = gStateVariables.Sour_List_Curr_Values
            local lCount = table.getn(lData)
        
            PrintNumber(lData[1])
            for lIndex = 2, lCount do
                Print(",")
                PrintNumber(lData[lIndex])
            end
        end
        
        -- SOURce[1]:LIST:VOLTage <NRf list>
        gCurrentRoot = gCommandTree["SOURCE1"]["LIST"]["VOLTAGE"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mSourceList
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lAbsValue
            local lMax = 0
        
            for lIndex, lValue in ipairs(lParameters) do
                lAbsValue = gMathAbs(lValue)
                if lAbsValue > lMax then
                    if lAbsValue > gOperatingBoundaries.mMaximumVoltageLevel then
                        gErrorQueue.Add(-222)
                        return
                    end
                    lMax = lAbsValue
                end
            end
            gStateVariables.Sour_List_Volt_Values = lParameters
            gStateVariables.Sour_List_Volt_Max = lMax
        end
        -- SOURce[1]:LIST:VOLTage?
        gCurrentRoot.mQuery.mExecute = function ()
            local lData = gStateVariables.Sour_List_Volt_Values
            local lCount = table.getn(lData)
        
            PrintNumber(lData[1])
            for lIndex = 2, lCount do
                Print(",")
                PrintNumber(lData[lIndex])
            end
        end
        
        -- SOURce[1]:LIST:CURRent:APPend <NRf list>
        gCurrentRoot = gCommandTree["SOURCE1"]["LIST"]["CURRENT"]["APPEND"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mSourceList
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lAbsValue
            local lMax = gStateVariables.Sour_List_Curr_Max
        
            if table.getn(gStateVariables.Sour_List_Curr_Values) + table.getn(lParameters) <= 2500 then
                for lIndex, lValue in ipairs(lParameters) do
                    lAbsValue = gMathAbs(lValue)
                    if lAbsValue > lMax then
                        if lAbsValue > gOperatingBoundaries.mMaximumCurrentLevel then
                            gErrorQueue.Add(-222)
                            return
                        end
                        lMax = lAbsValue
                    end
                end
                for lIndex, lValue in ipairs(lParameters) do
                    table.insert(gStateVariables.Sour_List_Curr_Values, lValue)
                end
                gStateVariables.Sour_List_Curr_Max = lMax
            else
                gErrorQueue.Add(-223)
            end
        end
        
        -- SOURce[1]:LIST:VOLTage:APPend <NRf list>
        gCurrentRoot = gCommandTree["SOURCE1"]["LIST"]["VOLTAGE"]["APPEND"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mSourceList
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lAbsValue
            local lMax = gStateVariables.Sour_List_Volt_Max
        
            if table.getn(gStateVariables.Sour_List_Volt_Values) + table.getn(lParameters) <= 2500 then
                for lIndex, lValue in ipairs(lParameters) do
                    lAbsValue = gMathAbs(lValue)
                    if lAbsValue > lMax then
                        if lAbsValue > gOperatingBoundaries.mMaximumVoltageLevel then
                            gErrorQueue.Add(-222)
                            return
                        end
                        lMax = lAbsValue
                    end
                end
                for lIndex, lValue in ipairs(lParameters) do
                    table.insert(gStateVariables.Sour_List_Volt_Values, lValue)
                end
                gStateVariables.Sour_List_Volt_Max = lMax
            else
                gErrorQueue.Add(-223)
            end
        end
        
        -- SOURce[1]:LIST:CURRent:POINts?
        gCurrentRoot = gCommandTree["SOURCE1"]["LIST"]["CURRENT"]["POINTS"]
        gCurrentRoot.mQuery.mExecute = function ()
            Print(table.getn(gStateVariables.Sour_List_Curr_Values))
        end
        
        -- SOURce[1]:LIST:VOLTage:POINts?
        gCurrentRoot = gCommandTree["SOURCE1"]["LIST"]["VOLTAGE"]["POINTS"]
        gCurrentRoot.mQuery.mExecute = function ()
            Print(table.getn(gStateVariables.Sour_List_Volt_Values))
        end
        
        -- SOURce[1]:LIST:CURRent:STARt <n>
        gCurrentRoot = gCommandTree["SOURCE1"]["LIST"]["CURRENT"]["START"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mIntegerMinMaxDef
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lStart = lParameters[1]
            local lMax = table.getn(gStateVariables.Sour_List_Curr_Values)
        
            if lStart == "MIN" or lStart == "DEF" then
                lStart = 1
            elseif lStart == "MAX" then
                lStart = lMax
            end
        
            if lStart >= 1 and lStart <= lMax then
                gStateVariables.Sour_List_Curr_Start = lStart
            else
                gErrorQueue.Add(-222)
            end
        end
        -- SOURce[1]:LIST:CURRent:STARt?
        -- The 2400 doesn't actually allow MIN, MAX, or DEF in this query
        gCurrentRoot.mQuery.mExecute = function ()
            Print(tostring(gStateVariables.Sour_List_Curr_Start))
        end
        
        -- SOURce[1]:LIST:VOLTage:STARt <n>
        gCurrentRoot = gCommandTree["SOURCE1"]["LIST"]["VOLTAGE"]["START"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mIntegerMinMaxDef
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lStart = lParameters[1]
            local lMax = table.getn(gStateVariables.Sour_List_Volt_Values)
        
            if lStart == "MIN" or lStart == "DEF" then
                lStart = 1
            elseif lStart == "MAX" then
                lStart = lMax
            end
        
            if lStart >= 1 and lStart <= lMax then
                gStateVariables.Sour_List_Volt_Start = lStart
            else
                gErrorQueue.Add(-222)
            end
        end
        -- SOURce[1]:LIST:VOLTage:STARt?
        -- The 2400 doesn't actually allow MIN, MAX, or DEF in this query
        gCurrentRoot.mQuery.mExecute = function ()
            Print(tostring(gStateVariables.Sour_List_Volt_Start))
        end
        
        -- SOURce[1]:PULSe:WIDTh <n>
        gCurrentRoot = gCommandTree["SOURCE1"]["PULSE"]["WIDTH"]
        gCurrentRoot.mCommand.mParameters =
        {
            {
                mParse = gParserTable.ParseParameterChoice,
                mData =
                {
                    gParserTable.mParseNRf,
                    gParserTable.mParsePulseWidth,
                    gParserTable.mParseInfinity,
                }
            }
        }
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            lWidth = lParameters[1]
        
            if lWidth >= 0.00015 and lWidth <= 0.00500 then
                gStateVariables.Sour_Puls_Widt = lWidth
                --lMemScratch.Sour_Puls_Width = lWidth
            else
                gErrorQueue.Add(-222)
            end
        end
        -- SOURce[1]:PULSe:WIDTh?
        gCurrentRoot.mQuery.mParameters = {gParserTable.mParsePulseWidth}
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(string.format("%.5f", lParameters[1] or gStateVariables.Sour_Puls_Widt))
        end
        
        -- SOURce[1]:PULSe:DELay <n>
        gCurrentRoot = gCommandTree["SOURCE1"]["PULSE"]["DELAY"]
        gCurrentRoot.mCommand.mParameters =
        {
            {
                mParse = gParserTable.ParseParameterChoice,
                mData =
                {
                    gParserTable.mParseNRf,
                    gParserTable.mParsePulseDelay,
                    gParserTable.mParseInfinity,
                }
            }
        }
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            lDelay = lParameters[1]
        
            if lDelay >= 0 and lDelay <= 4294 then
                gStateVariables.Sour_Puls_Del = lDelay
                --lMemScratch.Sour_Puls_Del = lDelay
            else
                gErrorQueue.Add(-222)
            end
        end
        -- SOURce[1]:PULSe:DELay?
        gCurrentRoot.mQuery.mParameters = {gParserTable.mParsePulseDelay}
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(string.format("%.5f",lParameters[1] or gStateVariables.Sour_Puls_Del))
        end
        
        -----------------------------------------------------------------
        --DIGIO pins 7-10 in 2600 correspond to DIGIO pins 1-4 in 2400
        if gDigioSupport then
            -- SOURce2:TTL[:LEVel] <NRf> | <NDN>
            -- SOURce2:TTL[:DEFault] <NRf> | <NDN>
            gCurrentRoot = gCommandTree["SOURCE2"]["TTL"]["LEVEL"]
            gCurrentRoot.mCommand.mParameters = gParserTable.mNDN
            gCurrentRoot.mCommand.mExecute = function (lParameters)
                local lLevel = lParameters[1]
                if lLevel >= 0 and lLevel <= gStateVariables.Sour2_Bsize_MaxValue then
                    gStateVariables.Sour2_Ttl_Lev = lLevel
                    UpdateDigOut(lLevel)
                else
                    gErrorQueue.Add(-222)
                end
            end
            -- SOURce2:TTL[:LEVel]?
            -- SOURce2:TTL[:DEFault]?
            gCurrentRoot.mQuery.mExecute = function ()
                PrintSource2(gStateVariables.Sour2_Ttl_Lev)
            end
        
            -- SOURce2:TTL:[LEVel]:ACTual?
            gCurrentRoot = gCommandTree["SOURCE2"]["TTL"]["LEVEL"]["ACTUAL"]
            gCurrentRoot.mQuery.mExecute = function ()
                PrintSource2(gStateVariables.Sour2_Ttl_Act)   
            end
        
            -- SOURce2:BSIZe <n>
            gCurrentRoot = gCommandTree["SOURCE2"]["BSIZE"]
            gCurrentRoot.mCommand.mParameters = gParserTable.mInteger
            gCurrentRoot.mCommand.mExecute = function (lParameters)
                local lBSize = lParameters[1]
                if lBSize == 3 then
                    gStateVariables.Sour2_Bsize = 3
                    gStateVariables.Sour2_Bsize_MaxValue = 7
                elseif lBSize == 4 or lBSize == 16 then
                    gStateVariables.Sour2_Bsize = 4
                    gStateVariables.Sour2_Bsize_MaxValue = 15
                else
                    gErrorQueue.Add(-222)
                    return
                end
                if gStateVariables.Sour2_Ttl_Lev > gStateVariables.Sour2_Bsize_MaxValue then
                    gStateVariables.Sour2_Ttl_Lev = gStateVariables.Sour2_Bsize_MaxValue
                end
                UpdatePin4()
                UpdateDigOut(gStateVariables.Sour2_Ttl_Lev)
                UpdateCalc2Source2()
            end
            -- SOURce2:BSIZe?
            gCurrentRoot.mQuery.mExecute = function ()
                Print(tostring(gStateVariables.Sour2_Bsize))
            end
        
            -- SOURce2:TTL4:MODE <name>
            gCurrentRoot = gCommandTree["SOURCE2"]["TTL4"]["MODE"]
            gCurrentRoot.mCommand.mParameters =
            {
                {
                    mParse = gParserTable.ParseParameterName,
                    mNames =
                    {
                        ["EOTEST"]      = "EOT",
                        ["EOT"]         = "EOT",
                        ["BUSY"]        = "BUSY",
                    }
                }
            }
            gCurrentRoot.mCommand.mExecute = function (lParameters)
                gStateVariables.Sour2_Ttl4_Mode = lParameters[1]
                UpdatePin4()
            end
            -- SOURce2:TTL4:MODE?
            gCurrentRoot.mQuery.mExecute = function ()
                Print(gStateVariables.Sour2_Ttl4_Mode)
            end
        
            -- SOURce2:TTL4:BSTate <b>
            gCurrentRoot = gCommandTree["SOURCE2"]["TTL4"]["BSTATE"]
            gCurrentRoot.mCommand.mParameters = gParserTable.mAny
            gCurrentRoot.mCommand.mExecute = function (lParameters)
                local lText = lParameters[1]
                local lState, lError
        
                if lText == "ON" or lText == "OFF" then
                    gErrorQueue.Add(-102)
                    return
                elseif lText == "HI" then
                    lState = 1
                elseif lText == "LO" then
                    lState = 0
                else
                    lState, lError = gParserTable.ParseParameterBoolean(lParameters[1])
        
                    if lError then
                        gErrorQueue.Add(lError)
                        return
                    end
                end
                gStateVariables.Sour2_Ttl4_Bst = lState
                UpdatePin4()
                UpdateDigOut(gStateVariables.Sour2_Ttl_Lev)
            end
            -- SOURce2:TTL4:BSTate?
            gCurrentRoot.mQuery.mExecute = function ()
                Print(gResponseValues[gStateVariables.Sour2_Ttl4_Bst])
            end
        
            -- SOURce2:CLEar:IMMediate
            gCurrentRoot = gCommandTree["SOURCE2"]["CLEAR"]["IMMEDIATE"]
            gCurrentRoot.mCommand.mExecute = function ()
                UpdateDigOut(gStateVariables.Sour2_Ttl_Lev)
            end
        
            -- SOURce2:CLEar:AUTO <b>
            gCurrentRoot = gCommandTree["SOURCE2"]["CLEAR"]["AUTO"]
            gCurrentRoot.mCommand.mParameters = gParserTable.mBoolean
            gCurrentRoot.mCommand.mExecute = function (lParameters)
                gStateVariables.Sour2_Cle_Auto = lParameters[1]
            end
            -- SOURce2:CLEar:AUTO?
            gCurrentRoot.mQuery.mExecute = function ()
                Print(gResponseValues[gStateVariables.Sour2_Cle_Auto])
            end
        
            -- SOURce2:CLEar:AUTO:DELay <n>
            gCurrentRoot = gCommandTree["SOURCE2"]["CLEAR"]["AUTO"]["DELAY"]
            gCurrentRoot.mCommand.mParameters =
            {
                {
                    mParse = gParserTable.ParseParameterChoice,
                    mData =
                    {
                        gParserTable.mParseNRf,
                        gParserTable.mParseAutoDelay,
                        gParserTable.mParseInfinity,
                    }
                }
            }
            gCurrentRoot.mCommand.mExecute = function (lParameters)
                local lDelay = lParameters[1]
                if lDelay >= 0 and lDelay <= 60 then
                    gStateVariables.Sour2_Cle_Del = lDelay
                else
                    gErrorQueue.Add(-222)
                end
            end
            -- SOURce2:CLEar:AUTO:DELay?
            gCurrentRoot.mQuery.mParameters = {gParserTable.mParseAutoDelay}
            gCurrentRoot.mQuery.mExecute = function (lParameters)
                Print(string.format("%.5f",lParameters[1] or gStateVariables.Sour2_Cle_Del))
            end
        end
        -- SOURce[1]:MEMory:POINts <n>
        gCurrentRoot = gCommandTree["SOURCE1"]["MEMORY"]["POINTS"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mSMIndex
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lPoints = lParameters[1]
            if lPoints >= 1 and lPoints <= 100 then
                gStateVariables.Sour_Mem_Poin = lPoints
            else
                gErrorQueue.Add(-222)
            end
        end
        -- SOURce[1]:MEMory:POINts?
        gCurrentRoot.mQuery.mParameters = gParserTable.mSMIndexQuery
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(tostring(lParameters[1] or gStateVariables.Sour_Mem_Poin))
        end
        
        -- SOURce[1]:MEMory:STARt <NRf>
        gCurrentRoot = gCommandTree["SOURCE1"]["MEMORY"]["START"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mSMIndex
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lMemLoc = lParameters[1]
            if lMemLoc >= 1 and lMemLoc <= 100 then
                gStateVariables.Sour_Mem_Start = lMemLoc
            else
                gErrorQueue.Add(-222)
            end
        end
        -- SOURce[1]:MEMory:STARt?
        gCurrentRoot.mQuery.mParameters = gParserTable.mSMIndexQuery
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(tostring(lParameters[1] or gStateVariables.Sour_Mem_Start))
        end
        
        -- SOURce[1]:MEMory:RECall <NRf>
        gCurrentRoot = gCommandTree["SOURCE1"]["MEMORY"]["RECALL"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mSMIndex
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lMemLoc = lParameters[1]
            if lMemLoc >= 1 and lMemLoc <= 100 then
                RecallSourceMemoryLocation(lMemLoc)
            else
                gErrorQueue.Add(-222)
            end
        end
        
        -- SOURce[1]:MEMory:SAVE <NRf>
        gCurrentRoot = gCommandTree["SOURCE1"]["MEMORY"]["SAVE"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mSMIndex
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lMemLoc = lParameters[1]
            if lMemLoc >= 1 and lMemLoc <= 100 then
                SaveSourceMemoryLocation(lMemLoc)
            else
                gErrorQueue.Add(-222)
            end
        end
        
        -- SOURce[1]:CURRent[:LEVel]:TRIGgered:SFACtor <n>
        gCurrentRoot = gCommandTree["SOURCE1"]["CURRENT"]["LEVEL"]["TRIGGERED"]["SFACTOR"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mGeneralPositive
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lSFactor = lParameters[1]
            if lSFactor >= -999.9999e18 and lSFactor <= 999.9999e18 then
                gStateVariables.Sour_Curr_Trig_Sfac = lSFactor
                lMemScratch.Sour_Curr_Trig_Sfac = lSFactor
            else
                gErrorQueue.Add(-222)
            end
        end
        -- SOURce[1]:CURRent[:LEVel]:TRIGgered:SFACtor?
        gCurrentRoot.mQuery.mParameters = gParserTable.mGeneralPositiveQuery
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(lParameters[1] or gStateVariables.Sour_Curr_Trig_Sfac)
        end
        
        -- SOURce[1]:VOLTAGE[:LEVel]:TRIGgered:SFACtor <n>
        gCurrentRoot = gCommandTree["SOURCE1"]["VOLTAGE"]["LEVEL"]["TRIGGERED"]["SFACTOR"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mGeneralPositive
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lSFactor = lParameters[1]
            if lSFactor >= -999.9999e18 and lSFactor <= 999.9999e18 then
                gStateVariables.Sour_Volt_Trig_Sfac = lSFactor
                lMemScratch.Sour_Volt_Trig_Sfac = lSFactor
            else
                gErrorQueue.Add(-222)
            end
        end
        -- SOURce[1]:VOLTAGE[:LEVel]:TRIGgered:SFACtor?
        gCurrentRoot.mQuery.mParameters = gParserTable.mGeneralPositiveQuery
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(lParameters[1] or gStateVariables.Sour_Volt_Trig_Sfac)
        end
        
        -- SOURce[1]:CURRent[:LEVel]:TRIGgered:SFACtor:STATe <b>
        gCurrentRoot = gCommandTree["SOURCE1"]["CURRENT"]["LEVEL"]["TRIGGERED"]["SFACTOR"]["STATE"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mBoolean
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            gStateVariables.Sour_Curr_Trig_Sfac_State = lParameters[1]
            lMemScratch.Sour_Curr_Trig_Sfac_Stat = lParameters[1]
        end
        -- SOURce[1]:CURRent[:LEVel]:TRIGgered:SFACtor:STATe?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gResponseValues[gStateVariables.Sour_Curr_Trig_Sfac_State])
        end
        
        -- SOURce[1]:VOLTAGE[:LEVel]:TRIGgered:SFACtor:STATe <b>
        gCurrentRoot = gCommandTree["SOURCE1"]["VOLTAGE"]["LEVEL"]["TRIGGERED"]["SFACTOR"]["STATE"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mBoolean
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            gStateVariables.Sour_Volt_Trig_Sfac_State = lParameters[1]
            lMemScratch.Sour_Volt_Trig_Sfac_Stat = lParameters[1]
        end
        -- SOURce[1]:VOLTAGE[:LEVel]:TRIGgered:SFACtor:STATe?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gResponseValues[gStateVariables.Sour_Volt_Trig_Sfac_State])
        end
        
        -- SOURce[1]:SOAK <NRf>
        gCurrentRoot = gCommandTree["SOURCE1"]["SOAK"]
        -- SOURce[1]:SOAK?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(0)
        end
        
        
        -- Not Implemented
        --:SOURce[1]:VOLTage:PROTection[:LEVel] <n>
        --:SOURce[1]:VOLTage:PROTection[:LEVel]?
        --:SOURce[1]:VOLTage:PROTection:TRIPPED?
        
        
        -----------------------------------------------------------------------
        -- Trigger subsystem commands Pins 1, 2, 3 and 4 of the Digital IO
        -- are used as tlink lines to generate Trigger signals and to receive
        -- input triggers local variables are used to store the tlink information
        -- The implementation is done in the TriggerSmu()
        -----------------------------------------------------------------------
        -- INITiate[:IMMediate]
        gCurrentRoot = gCommandTree["INITIATE"]["IMMEDIATE"]
        gCurrentRoot.mCommand.mExecute = function ()
            if gAccessors.mGetSourceOutput() == 1 or gStateVariables.Sour_Cle_Auto_State then
                gPrintEnable = false
                Initiate()
            else
                gErrorQueue.Add(803)
            end
        end
        
        -- ABORt
        gCurrentRoot = gCommandTree["ABORT"]
        gCurrentRoot.mCommand.mExecute = function ()
            gAbortExecuted = true
            smua.abort()
        end
        
        -- *TRG
        gCurrentRoot = gCommandTree["*TRG"]
        gCurrentRoot.mCommand.mExecute = function ()
            if gStateVariables.Arm_Sour == "BUS" then
                trigger.generator[2].assert()
                gTrgExecuted = true
            end
        end
        
        -- GET
        gSpecialCommands[gRemoteComm.types.TRIGGER].mCommand = gSpecialCommands["*TRG"].mCommand
        
        -- ARM[:SEQuence[1]][LAYer[1]]:COUNt <n> (1-2500)
        gCurrentRoot = gCommandTree["ARM"]["SEQUENCE1"]["LAYER1"]["COUNT"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mTriggerCount
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lCount = lParameters[1]
        
            if lCount == gInf then
                gArm.count = 0
            else
                if lCount >= 1 and lCount <= math.floor(2500 / gTrigger.count) then
                    gArm.count = lCount
                else
                    gErrorQueue.Add(-222)
                end
            end
        end
        -- ARM[:SEQuence[1]][LAYer[1]]:COUNt?
        gCurrentRoot.mQuery.mParameters = gParserTable.mTriggerCountQuery
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            if lParameters[1] then
                Print(tostring(lParameters[1]))
            else
                if gArm.count == 0 then
                    Print(gInf)
                else
                    Print(tostring(gArm.count))
                end
            end
        end
        
        -- TRIGger:CLEar
        gCurrentRoot = gCommandTree["TRIGGER"]["CLEAR"]
        gCurrentRoot.mCommand.mExecute = function ()
        -- clears digio pins 1-4 and 10-14
        -- digio pins 8,9 (SOT and EOT are also cleared)
        if gDigioSupport then
            for N = 1, 4 do
                gTriggerLines[N].clear()
            end
            for N = 8, 14 do
                gTriggerLines[N].clear()
            end
        end
            display.trigger.clear()
            trigger.clear()
        end
        
        -- TRIGger[:SEQuence[1]]:COUNt <n>(1-2500)
        gCurrentRoot = gCommandTree["TRIGGER"]["SEQUENCE1"]["COUNT"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mTriggerCount
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lCount = lParameters[1]
            local lArmCount = gArm.count
            if lArmCount == 0 then
                lArmCount = 1
            end
        
            if lCount >= 1 and lCount <= math.floor(2500 / lArmCount) then
                gTrigger.count = lCount
            else
                gErrorQueue.Add(-222)
            end
        end
        -- TRIGger[:SEQuence[1]]:COUNt?
        gCurrentRoot.mQuery.mParameters = gParserTable.mTriggerCountQuery
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(tostring(lParameters[1] or gTrigger.count))
        end
        
        --Need to look if smua.trigger.autoclear() clears the ARMED_EVENT_ID
        -- TRIGger[:SEQuence[1]]:DELay <n>
        gCurrentRoot = gCommandTree["TRIGGER"]["SEQUENCE1"]["DELAY"]
        gCurrentRoot.mCommand.mParameters =
        {
            {
                mParse = gParserTable.ParseParameterChoice,
                mData =
                {
                    gParserTable.mParseNRf,
                    gParserTable.mParseTriggerDelay,
                    gParserTable.mParseInfinity,
                }
            }
        }
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lDelay = lParameters[1]
        
            if lDelay >= 0 and lDelay <= 999.99988 then
                gStateVariables.Trig_Del = lDelay
                lMemScratch.Trig_Del = lDelay
            else
                gErrorQueue.Add(-222)
            end
        end
        -- TRIGger[:SEQuence[1]]:DELay?
        gCurrentRoot.mQuery.mParameters = {gParserTable.mParseTriggerDelay}
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(string.format("%.5f", lParameters[1] or gStateVariables.Trig_Del))
        end
        
        -- ARM[:SEQuence[1]][LAYer[1]]:SOURce <name>
        gCurrentRoot = gCommandTree["ARM"]["SEQUENCE1"]["LAYER1"]["SOURCE"]
        if gDigioSupport then
            gCurrentRoot.mCommand.mParameters =
            {
                {
                    mParse = gParserTable.ParseParameterName,
                    mNames =
                    {
                        ["IMMEDIATE"]   = "IMM",
                        ["IMM"]         = "IMM",
                        ["TIMER"]       = "TIM",
                        ["TIM"]         = "TIM",
                        ["TLINK"]       = "TLIN",
                        ["TLIN"]        = "TLIN",
                        ["NSTEST"]      = "NST",
                        ["NST"]         = "NST",
                        ["PSTEST"]      = "PST",
                        ["PST"]         = "PST",
                        ["BSTEST"]      = "BST",
                        ["BST"]         = "BST",
                        ["MANUAL"]      = "MAN",
                        ["MAN"]         = "MAN",
                        ["BUS"]         = "BUS",
                    }
                }
            }
        else
            gCurrentRoot.mCommand.mParameters =
            {
                {
                    mParse = gParserTable.ParseParameterName,
                    mNames =
                    {
                        ["IMMEDIATE"]   = "IMM",
                        ["IMM"]         = "IMM",
                        ["TIMER"]       = "TIM",
                        ["TIM"]         = "TIM",
                        ["MANUAL"]      = "MAN",
                        ["MAN"]         = "MAN",
                        ["BUS"]         = "BUS",
                    }
                }
            }
        end
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            gStateVariables.Arm_Sour = lParameters[1]
        end
        -- ARM[:SEQuence[1]][LAYer[1]]:SOURce?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gStateVariables.Arm_Sour)
        end
        
        -- TRIGger[:SEQuence[1]]:SOURce <name>
        gCurrentRoot = gCommandTree["TRIGGER"]["SEQUENCE1"]["SOURCE"]
        gCurrentRoot.mCommand.mParameters =
        {
            {
                mParse = gParserTable.ParseParameterName,
                mNames =
                {
                    ["IMMEDIATE"]   = "IMM",
                    ["IMM"]         = "IMM",
                    ["TLINK"]       = "TLIN",
                    ["TLIN"]        = "TLIN",
                }
            }
        }
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            gStateVariables.Trig_Sour = lParameters[1]
        end
        -- TRIGger[:SEQuence[1]]:SOURce?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gStateVariables.Trig_Sour)
        end
        
        -- ARM[:SEQuence[1]][:LAYer[1]]:TIMer <n>
        gCurrentRoot = gCommandTree["ARM"]["SEQUENCE1"]["LAYER1"]["TIMER"]
        gCurrentRoot.mCommand.mParameters =
        {
            {
                mParse = gParserTable.ParseParameterChoice,
                mData =
                {
                    gParserTable.mParseNRf,
                    gParserTable.mParseArmTimer,
                    gParserTable.mParseInfinity,
                }
            }
        }
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lTime = lParameters[1]
            if lTime >= 0.001 and lTime <= 99999.992 then
                gStateVariables.Arm_Tim = lTime
            else
                gErrorQueue.Add(-222)
            end
        end
        -- ARM[:SEQuence[1]][:LAYer[1]]:TIMer?
        gCurrentRoot.mQuery.mParameters = {gParserTable.mParseArmTimer}
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(string.format("%.3f", lParameters[1] or gStateVariables.Arm_Tim))
        end
        
        -- ARM[:SEQuence[1]][LAYer[1]][:TCONfigure]:DIRection <name>
        gCurrentRoot = gCommandTree["ARM"]["SEQUENCE1"]["LAYER1"]["TCONFIGURE"]["DIRECTION"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mTriggerDirection
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            gStateVariables.Arm_Dir = lParameters[1]
        end
        -- ARM[:SEQuence[1]][LAYer[1]][:TCONfigure]:DIRection?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gStateVariables.Arm_Dir)
        end
        
        -- TRIGger[:SEQuence[1]][:TCONfigure]:DIRection <name>
        gCurrentRoot = gCommandTree["TRIGGER"]["SEQUENCE1"]["TCONFIGURE"]["DIRECTION"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mTriggerDirection
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            gStateVariables.Trig_Dir = lParameters[1]
        end
        -- TRIGger[:SEQuence[1]][:TCONfigure]:DIRection?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gStateVariables.Trig_Dir)
        end
        
        if gDigioSupport then
            -- ARM[:SEQuence[1]][LAYer[1]][:TCONfigure]:ILINe <NRf>
            gCurrentRoot = gCommandTree["ARM"]["SEQUENCE1"]["LAYER1"]["TCONFIGURE"]["ASYNCHRONOUS"]["ILINE"]
            gCurrentRoot.mCommand.mParameters = gParserTable.mInteger
            gCurrentRoot.mCommand.mExecute = function (lParameters)
                local lILine = lParameters[1]
                if lILine >= 1 and lILine <= 4 then
                    gStateVariables.Arm_Ilin = lILine
                else
                    gErrorQueue.Add(-222)
                end
            end
            -- ARM[:SEQuence[1]][LAYer[1]][:TCONfigure]:ILINe?
            gCurrentRoot.mQuery.mExecute = function ()
                Print(tostring(gStateVariables.Arm_Ilin))
            end
        
            -- TRIGger[:SEQuence[1]][:TCONfigure]:ILINe <NRf>
            gCurrentRoot = gCommandTree["TRIGGER"]["SEQUENCE1"]["TCONFIGURE"]["ASYNCHRONOUS"]["ILINE"]
            gCurrentRoot.mCommand.mParameters = gParserTable.mInteger
            gCurrentRoot.mCommand.mExecute = function (lParameters)
                local lILine = lParameters[1]
                if lILine >= 1 and lILine <= 4 then
                    gStateVariables.Trig_Ilin = lILine
                else
                    gErrorQueue.Add(-222)
                end
            end
            -- TRIGger[:SEQuence[1]][:TCONfigure]:ILINe?
            gCurrentRoot.mQuery.mExecute = function ()
                Print(tostring(gStateVariables.Trig_Ilin))
            end
        
            -- ARM[:SEQuence[1]][LAYer[1]][:TCONfigure]:OLINe <NRf>
            gCurrentRoot = gCommandTree["ARM"]["SEQUENCE1"]["LAYER1"]["TCONFIGURE"]["ASYNCHRONOUS"]["OLINE"]
            gCurrentRoot.mCommand.mParameters = gParserTable.mInteger
            gCurrentRoot.mCommand.mExecute = function (lParameters)
                local lOLine = lParameters[1]
                if lOLine >= 1 and lOLine <= 4 then
                    gStateVariables.Arm_Olin = lOLine
                else
                    gErrorQueue.Add(-222)
                end
            end
            -- ARM[:SEQuence[1]][LAYer[1]][:TCONfigure]:OLINe?
            gCurrentRoot.mQuery.mExecute = function ()
                Print(tostring(gStateVariables.Arm_Olin))
            end
        
            -- TRIGger[:SEQuence[1]][:TCONfigure]:OLINe <NRf>
            gCurrentRoot = gCommandTree["TRIGGER"]["SEQUENCE1"]["TCONFIGURE"]["ASYNCHRONOUS"]["OLINE"]
            gCurrentRoot.mCommand.mParameters = gParserTable.mInteger
            gCurrentRoot.mCommand.mExecute = function (lParameters)
                local lOLine = lParameters[1]
                if lOLine >= 1 and lOLine <= 4 then
                    gStateVariables.Trig_Olin = lOLine
                else
                    gErrorQueue.Add(-222)
                end
            end
            -- TRIGger[:SEQuence[1]][:TCONfigure]:OLINe?
            gCurrentRoot.mQuery.mExecute = function ()
                Print(tostring(gStateVariables.Trig_Olin))
            end
        
            -- ARM[:SEQuence[1]][LAYer[1]][:TCONfigure]:OUTPut <Name list>
            gCurrentRoot = gCommandTree["ARM"]["SEQUENCE1"]["LAYER1"]["TCONFIGURE"]["ASYNCHRONOUS"]["OUTPUT"]
            gCurrentRoot.mCommand.mParameters = {gParserTable.mParseArmEvent}
            for lIndex = 2, 99 do
                gCurrentRoot.mCommand.mParameters[lIndex] = gParserTable.mParseArmEventOptional
            end
            gCurrentRoot.mCommand.mExecute = function (lParameters)
                gStateVariables.Arm_Outp.TEX = false
                gStateVariables.Arm_Outp.TENT = false
        
                for lIndex, lValue in ipairs(lParameters) do
                    if lValue ~= "NONE" then
                        gStateVariables.Arm_Outp[lValue] = true
                    end
                end
            end
            -- ARM[:SEQuence[1]][LAYer[1]][:TCONfigure]:OUTPut?
            gCurrentRoot.mQuery.mExecute = function ()
                local lSeparate = ""
        
                if gStateVariables.Arm_Outp.TEX then
                    Print("TEX")
                    lSeparate = ","
                end
                if gStateVariables.Arm_Outp.TENT then
                    Print(lSeparate)
                    Print("TENT")
                    lSeparate = ","
                end
                if string.len(lSeparate) == 0 then
                    Print("NONE")
                end
            end
        end
        -- TRIGger[:SEQuence[1]][:TCONfigure][:ASYNchronous]:INPut <event list>
        gCurrentRoot = gCommandTree["TRIGGER"]["SEQUENCE1"]["TCONFIGURE"]["ASYNCHRONOUS"]["INPUT"]
        gCurrentRoot.mCommand.mParameters = {gParserTable.mParseTriggerEvent}
        for lIndex = 2, 99 do
            gCurrentRoot.mCommand.mParameters[lIndex] = gParserTable.mParseTriggerEventOptional
        end
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            gStateVariables.Trig_Inp = "NONE"
            for lIndex, lValue in ipairs(lParameters) do
                if lValue ~= "NONE" then
                    if gStateVariables.Trig_Inp == "NONE" then
                        gStateVariables.Trig_Inp = lValue
                    else
                         gErrorQueue.Add(-221)
                    end
                end
            end
        end
        -- TRIGger[:SEQuence[1]][:TCONfigure][:ASYNchronous]:INPut?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gStateVariables.Trig_Inp)
        end
        
        if gDigioSupport then
            -- TRIGger[:SEQuence[1]][:TCONfigure]:OUTPut <event list>
            gCurrentRoot = gCommandTree["TRIGGER"]["SEQUENCE1"]["TCONFIGURE"]["ASYNCHRONOUS"]["OUTPUT"]
            gCurrentRoot.mCommand.mParameters = {gParserTable.mParseTriggerEvent}
            for lIndex = 2, 99 do
                gCurrentRoot.mCommand.mParameters[lIndex] = gParserTable.mParseTriggerEventOptional
            end
            gCurrentRoot.mCommand.mExecute = function (lParameters)
                gStateVariables.Trig_Outp.SOUR = false
                gStateVariables.Trig_Outp.DEL = false
                gStateVariables.Trig_Outp.SENS = false
        
                for lIndex, lValue in ipairs(lParameters) do
                    if lValue ~= "NONE" then
                        gStateVariables.Trig_Outp[lValue] = true
                    end
                end
            end
            -- TRIGger[:SEQuence[1]][:TCONfigure]:OUTPut?
            gCurrentRoot.mQuery.mExecute = function ()
                local lSeparate = ""
        
                if gStateVariables.Trig_Outp.SOUR then
                    Print("SOUR")
                    lSeparate = ","
                end
                if gStateVariables.Trig_Outp.DEL then
                    Print(lSeparate)
                    Print("DEL")
                    lSeparate = ","
                end
                if gStateVariables.Trig_Outp.SENS then
                    Print(lSeparate)
                    Print("SENS")
                    lSeparate = ","
                end
                if string.len(lSeparate) == 0 then
                    Print("NONE")
                end
            end
        end
        -----------------------------------------------------------------------
        -- TRACe|DATA subsystem commands
        -- check for floating point errors when comparing
        -----------------------------------------------------------------------
        -- TRACe:DATA?
        -- DATA:DATA?
        gCurrentRoot = gCommandTree["TRACE"]["DATA"]
        gCurrentRoot.mQuery.mExecute = function ()
            if gTraceBuffer.mCount > 0 then
                if gStateVariables.Trac_Feed == "SENS1" then
                    PrintTraceBuffer(1, gTraceBuffer.mCount)
                else
                    PrintCalculateBuffer(1, gTraceBuffer.mCount, gTraceBuffer)
                end
            else
                gErrorQueue.Add(-230)
            end
        end
        
        -- TRACe:CLEar
        -- DATA:CLEar
        gCurrentRoot = gCommandTree["TRACE"]["CLEAR"]
        gCurrentRoot.mCommand.mExecute = function ()
            if gStateVariables.Trac_Cont == "NEXT" then
                gErrorQueue.Add(800)
            else
                ClearBuffer(gTraceBuffer)
            end
        end
        
        -- TRACe:FREE?
        -- DATA:FREE?
        gCurrentRoot = gCommandTree["TRACE"]["FREE"]
        gCurrentRoot.mQuery.mExecute = function ()
            Print(tostring(60000-(gTraceBuffer.mCount * 24)))
            Print(",")
            Print(tostring(gTraceBuffer.mCount * 24))
        end
        
        -- TRACe:POINts <n>
        -- DATA:POINts <n>
        gCurrentRoot = gCommandTree["TRACE"]["POINTS"]
        gCurrentRoot.mCommand.mParameters =
        {
            {
                mParse = gParserTable.ParseParameterChoice,
                mData =
                {
                    gParserTable.mParseInteger,
                    gParserTable.mParseTracePoints,
                    gParserTable.mParseInfinity,
                }
            }
        }
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lPoints = lParameters[1]
            if gStateVariables.Trac_Cont == "NEXT" then
                gErrorQueue.Add(800)
            else
                if lPoints >= 1 and lPoints <= 2500 then
                    gStateVariables.Trac_Poin = lPoints
                    ClearBuffer(gTraceBuffer)
                else
                    gErrorQueue.Add(-222)
                end
            end
        end
        -- TRACe:POINts?
        -- DATA:POINts?
        gCurrentRoot.mQuery.mParameters = {gParserTable.mParseTracePoints}
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(tostring(lParameters[1] or gStateVariables.Trac_Poin))
        end
        
        -- TRACe:POINts:ACTual?
        -- DATA:POINts:ACTual?
        gCurrentRoot = gCommandTree["TRACE"]["POINTS"]["ACTUAL"]
        gCurrentRoot.mQuery.mExecute = function ()
            Print(tostring(gTraceBuffer.mCount))
        end
        
        -- TRACe:FEED <name>
        -- DATA:FEED <name>
        gCurrentRoot = gCommandTree["TRACE"]["FEED"]
        gCurrentRoot.mCommand.mParameters =
        {
            {
                mParse = gParserTable.ParseParameterName,
                mNames =
                {
                    ["SENSE1"]      = "SENS1",
                    ["SENSE"]       = "SENS1",
                    ["SENS1"]       = "SENS1",
                    ["SENS"]        = "SENS1",
                    ["CALCULATE1"]  = "CALC1",
                    ["CALCULATE"]   = "CALC1",
                    ["CALC1"]       = "CALC1",
                    ["CALC"]        = "CALC1",
                    ["CALCULATE2"]  = "CALC2",
                    ["CALC2"]       = "CALC2",
                }
            }
        }
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            if gStateVariables.Trac_Cont == "NEXT" then
                gErrorQueue.Add(800)
            else
                gStateVariables.Trac_Feed = lParameters[1]
            end
        end
        -- TRACe:FEED?
        -- DATA:FEED?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gStateVariables.Trac_Feed)
        end
        
        -- TRACe:FEED:CONTrol <name>
        -- DATA:FEED:CONTrol <name>
        gCurrentRoot = gCommandTree["TRACE"]["FEED"]["CONTROL"]
        gCurrentRoot.mCommand.mParameters =
        {
            {
                mParse = gParserTable.ParseParameterName,
                mNames =
                {
                    ["NEVER"]       = "NEV",
                    ["NEV"]         = "NEV",
                    ["NEXT"]        = "NEXT",
                }
            }
        }
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            if lParameters[1] == "NEXT" and gStateVariables.Trac_Cont == "NEV" then
                ClearBuffer(gTraceBuffer)
            end
            gStateVariables.Trac_Cont = lParameters[1]
        end
        -- TRACe:FEED:CONTrol?
        -- DATA:FEED:CONTrol?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gStateVariables.Trac_Cont)
        end
        
        -- TRACe:TSTAMP:FORMAT <name>
        -- DATA:TSTAMP:FORMAT <name>
        gCurrentRoot = gCommandTree["TRACE"]["TSTAMP"]["FORMAT"]
        gCurrentRoot.mCommand.mParameters =
        {
            {
                mParse = gParserTable.ParseParameterName,
                mNames =
                {
                    ["ABSOLUTE"]    = "ABS",
                    ["ABS"]         = "ABS",
                    ["DELTA"]       = "DELT",
                    ["DELT"]        = "DELT",
                }
            }
        }
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            gStateVariables.Trac_Tst_Form = lParameters[1]
        end
        -- TRACe:TSTAMP:FORMAT?
        -- DATA:TSTAMP:FORMAT?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gStateVariables.Trac_Tst_Form)
        end
        
        -----------------------------------------------------------------------
        -- SENSE subsystem commands
        -----------------------------------------------------------------------
        -- [:SENSe[1]]:DATA[:LATest]?
        gCurrentRoot = gCommandTree["SENSE1"]["DATA"]["LATEST"]
        gCurrentRoot.mQuery.mExecute = function ()
            if gSampleBuffer.mCount > 0 then
                PrintSampleBuffer(gSampleBuffer.mCount, gSampleBuffer.mCount)
            else
                gErrorQueue.Add(-230)
            end
        end
        
        -- [:SENSe[1]]:FUNCtion:CONCurrent <b>
        gCurrentRoot = gCommandTree["SENSE1"]["FUNCTION"]["CONCURRENT"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mBoolean
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            if lParameters[1] then
                gStateVariables.Sens_Func_Conc = true
                lMemScratch.Sens_Func_Conc = true
            else
                gStateVariables.Sens_Func_Conc = false
                lMemScratch.Sens_Func_Conc = false
                gStateVariables.Sens_Func.VOLT = true
                gStateVariables.Sens_Func.CURR = false
                gStateVariables.Sens_Func.RES = false
                gStateVariables.Sens_Func.ANY = true
                lMemScratch.Sens_Func_Volt = true
                lMemScratch.Sens_Func_Curr = false
                lMemScratch.Sens_Func_Res = false
                lMemScratch.Sens_Func_Any = true
            end
        end
        -- [:SENSe[1]]:FUNCtion:CONCurrent?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gResponseValues[gStateVariables.Sens_Func_Conc])
        end
        
        -- [:SENSe[1]]:FUNCtion[:ON] <function list>
        gCurrentRoot = gCommandTree["SENSE1"]["FUNCTION"]["ON"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mFunctionList
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            if gStateVariables.Sens_Func_Conc then
                -- It is ok to enable them all
                for lIndex, lValue in ipairs(lParameters) do
                    gStateVariables.Sens_Func[lValue] = true
                end
                gStateVariables.Sens_Func.ANY = true
            elseif lParameters[2] then
                -- Only one allowed when not in concurrent mode
                gErrorQueue.Add(-108)
                return
            else
                gStateVariables.Sens_Func.VOLT = false
                gStateVariables.Sens_Func.CURR = false
                gStateVariables.Sens_Func.RES = false
                gStateVariables.Sens_Func[lParameters[1]] = true
                gStateVariables.Sens_Func.ANY = true
            end
            lMemScratch.Sens_Func_Volt = gStateVariables.Sens_Func.VOLT
            lMemScratch.Sens_Func_Curr = gStateVariables.Sens_Func.CURR
            lMemScratch.Sens_Func_Res = gStateVariables.Sens_Func.RES
            lMemScratch.Sens_Func_Any = gStateVariables.Sens_Func.ANY
        end
        -- [:SENSe[1]]:FUNCtion[:ON]?
        gCurrentRoot.mQuery.mExecute = function ()
            local lSeparate = ""
        
            if gStateVariables.Sens_Func.VOLT then
                Print('"VOLT:DC"')
                lSeparate = ","
            end
            if gStateVariables.Sens_Func.CURR then
                Print(lSeparate)
                Print('"CURR:DC"')
                lSeparate = ","
            end
            if gStateVariables.Sens_Func.RES then
                Print(lSeparate)
                Print('"RES"')
                lSeparate = ","
            end
            if string.len(lSeparate) == 0 then
                Print('""')
            end
        end
        
        -- [:SENSe[1]]:FUNCtion[:ON]:ALL
        gCurrentRoot = gCommandTree["SENSE1"]["FUNCTION"]["ON"]["ALL"]
        gCurrentRoot.mCommand.mExecute = function ()
            if gStateVariables.Sens_Func_Conc then
                gStateVariables.Sens_Func.VOLT = true
                gStateVariables.Sens_Func.CURR = true
                gStateVariables.Sens_Func.RES = true
            else
                gStateVariables.Sens_Func.VOLT = false
                gStateVariables.Sens_Func.CURR = false
                gStateVariables.Sens_Func.RES = true
            end
            gStateVariables.Sens_Func.ANY = true
            lMemScratch.Sens_Func_Volt = gStateVariables.Sens_Func.VOLT
            lMemScratch.Sens_Func_Curr = gStateVariables.Sens_Func.CURR
            lMemScratch.Sens_Func_Res = gStateVariables.Sens_Func.RES
            lMemScratch.Sens_Func_Any = true
        end
        
        -- [:SENSe[1]]:FUNCtion[:ON]:COUNT?
        gCurrentRoot = gCommandTree["SENSE1"]["FUNCTION"]["ON"]["COUNT"]
        gCurrentRoot.mQuery.mExecute = function ()
            Print(tostring((gStateVariables.Sens_Func.VOLT and 1 or 0) +
                    (gStateVariables.Sens_Func.CURR and 1 or 0) +
                    (gStateVariables.Sens_Func.RES and 1 or 0)))
        end
        
        -- [:SENSe[1]]:FUNCtion:OFF <function list>
        gCurrentRoot = gCommandTree["SENSE1"]["FUNCTION"]["OFF"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mFunctionList
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            for lIndex, lValue in ipairs(lParameters) do
                gStateVariables.Sens_Func[lValue] = false
            end
        end
        -- [:SENSe[1]]:FUNCtion:OFF?
        gCurrentRoot.mQuery.mExecute = function ()
            local lSeparate = ""
        
            if not gStateVariables.Sens_Func.VOLT then
                Print('"VOLT:DC"')
                lSeparate = ","
            end
            if not gStateVariables.Sens_Func.CURR then
                Print(lSeparate)
                Print('"CURR:DC"')
                lSeparate = ","
            end
            if not gStateVariables.Sens_Func.RES then
                Print(lSeparate)
                Print('"RES"')
                lSeparate = ","
            end
            if string.len(lSeparate) == 0 then
                Print('""')
            end
        end
        
        -- [:SENSe[1]]:FUNCtion:OFF:ALL
        gCurrentRoot = gCommandTree["SENSE1"]["FUNCTION"]["OFF"]["ALL"]
        gCurrentRoot.mCommand.mExecute = function ()
            gStateVariables.Sens_Func.VOLT = false
            gStateVariables.Sens_Func.CURR = false
            gStateVariables.Sens_Func.RES = false
            gStateVariables.Sens_Func.ANY = false
            lMemScratch.Sens_Func_Volt = false
            lMemScratch.Sens_Func_Curr = false
            lMemScratch.Sens_Func_Res = false
            lMemScratch.Sens_Func_Any = false
        end
        
        -- [:SENSe[1]]:FUNCtion:OFF:COUNT?
        gCurrentRoot = gCommandTree["SENSE1"]["FUNCTION"]["OFF"]["COUNT"]
        gCurrentRoot.mQuery.mExecute = function ()
            Print(tostring((gStateVariables.Sens_Func.VOLT and 0 or 1) +
                    (gStateVariables.Sens_Func.CURR and 0 or 1) +
                    (gStateVariables.Sens_Func.RES and 0 or 1)))
        end
        
        -- [:SENSe[1]]:FUNCtion:STATE? <name>
        gCurrentRoot = gCommandTree["SENSE1"]["FUNCTION"]["STATE"]
        gCurrentRoot.mQuery.mParameters = {gParserTable.mParseFunctionName}
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(gResponseValues[gStateVariables.Sens_Func[lParameters[1]]])
        end
        
        -- [:SENSe[1]]:CURRent[:DC]:NPLCycles(.001-25) (.01-10 in 2400) <n>
        gCurrentRoot = gCommandTree["SENSE1"]["CURRENT"]["DC"]["NPLCYCLES"]
        gCurrentRoot.mCommand.mParameters =
        {
            {
                mParse = gParserTable.ParseParameterChoice,
                mData =
                {
                    gParserTable.mParseNRf,
                    gParserTable.mParseNplc,
                    gParserTable.mParseInfinity,
                }
            }
        }
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lNplc = lParameters[1]
        
            if lNplc >= 0.001 and lNplc <= 25 then
                gAccessors.mSetMeasureNplc(lNplc)
                lMemScratch.Sens_Nplc = lNplc
            else
                gErrorQueue.Add(-222)
            end
        end
        -- [:SENSe[1]]:CURRent[:DC]:NPLCycles?
        gCurrentRoot.mQuery.mParameters = {gParserTable.mParseNplc}
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(string.format("%.3f", lParameters[1] or gAccessors.mGetMeasureNplc()))
        end
        
        -- [:SENSe[1]]:CURRent[:DC]:PROTection[:LEVel] <n>
        gCurrentRoot = gCommandTree["SENSE1"]["CURRENT"]["DC"]["PROTECTION"]["LEVEL"]
        gCurrentRoot.mCommand.mParameters =
        {
            {
                mParse = gParserTable.ParseParameterChoice,
                mData =
                {
                    gParserTable.mParseNRf,
                    gParserTable.mParseCurrentLimit,
                    gParserTable.mParseInfinity,
                }
            }
        }
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lLevel = gMathAbs(lParameters[1])
        
            if lLevel >= gOperatingBoundaries.mMinimumCurrentLimit and lLevel <= gOperatingBoundaries.mMaximumCurrentLimit then
                gStateVariables.Sens_Curr_Prot = lLevel
                lMemScratch.Actual_Curr_Prot = lLevel
                if (gAccessors.mGetSourceRangev() > gSafeOperatingArea.mVoltage * 1.01 or gStateVariables.Sour_Volt_Trig_Ampl > gSafeOperatingArea.mVoltage * 1.01)
                and lLevel > gSafeOperatingArea.mCurrent then --and (lLevel/gAccessors.mGetMeasureRangei()) - 1 >= gEpsilon  then
                    if gAccessors.mGetMeasureAutoRangei() == 0 then 
                        lLevel = gAccessors.mGetMeasureRangei()
                    else
                        lLevel = gSafeOperatingArea.mCurrent
                    end            
                end
                gAccessors.mSetSourceLimiti(lLevel)
                lMemScratch.Sens_Curr_Prot = lLevel
            else
                gErrorQueue.Add(-222)
            end
        end
        -- [:SENSe[1]]:CURRent[:DC]:PROTection[:LEVel]?
        gCurrentRoot.mQuery.mParameters = {gParserTable.mParseCurrentLimit}
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            --Print(lParameters[1] or gAccessors.mGetSourceLimiti())
            Print(lParameters[1] or gStateVariables.Sens_Curr_Prot)
        end
        
        -- [:SENSe[1]]:CURRent[:DC]:PROTection:TRIPped?
        gCurrentRoot = gCommandTree["SENSE1"]["CURRENT"]["DC"]["PROTECTION"]["TRIPPED"]
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gResponseValues[gAccessors.mGetSourceFunc() == gDCVOLTS and gSource.compliance])
        end
        
        -- [:SENSe[1]]:CURRent[:DC]:PROTection:RSYNchronize <b>
        gCurrentRoot = gCommandTree["SENSE1"]["CURRENT"]["DC"]["PROTECTION"]["RSYNCHRONIZE"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mBoolean
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            if lParameters[1] then
                gStateVariables.Sens_Curr_Prot_Rsyn = true
                gStateVariables.Sens_Volt_Prot_Rsyn = true
                if gAccessors.mGetMeasureAutoRangei() == 0 then
                    gAccessors.mSetMeasureAutoRangei(smua.AUTORANGE_FOLLOW_LIMIT)
                    lMemScratch.Sens_Curr_Rang_Auto = smua.AUTORANGE_FOLLOW_LIMIT
                end
                if gAccessors.mGetMeasureAutoRangev() == 0 then
                    gAccessors.mSetMeasureAutoRangev(smua.AUTORANGE_FOLLOW_LIMIT)
                    lMemScratch.Sens_Volt_Rang_Auto = smua.AUTORANGE_FOLLOW_LIMIT
                end
            else
                gStateVariables.Sens_Curr_Prot_Rsyn = false
                gStateVariables.Sens_Volt_Prot_Rsyn = false
                if gAccessors.mGetMeasureAutoRangei() == smua.AUTORANGE_FOLLOW_LIMIT then
                    gAccessors.mSetMeasureAutoRangei(0)
                    lMemScratch.Sens_Curr_Rang_Auto = 0
                end
                if gAccessors.mGetMeasureAutoRangev() == smua.AUTORANGE_FOLLOW_LIMIT then
                    gAccessors.mSetMeasureAutoRangev(0)
                    lMemScratch.Sens_Volt_Rang_Auto = 0
                end
            end
        end
        -- [:SENSe[1]]:CURRent[:DC]:PROTection:RSYNchronize?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gResponseValues[gStateVariables.Sens_Curr_Prot_Rsyn])
        end
        
        -- [:SENSe[1]]:VOLTage[:DC]:PROTection[:LEVel] <n>
        gCurrentRoot = gCommandTree["SENSE1"]["VOLTAGE"]["DC"]["PROTECTION"]["LEVEL"]
        gCurrentRoot.mCommand.mParameters =
        {
            {
                mParse = gParserTable.ParseParameterChoice,
                mData =
                {
                    gParserTable.mParseNRf,
                    gParserTable.mParseVoltageLimit,
                    gParserTable.mParseInfinity,
                }
            }
        }
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lLevel = gMathAbs(lParameters[1])
        
            if lLevel >= gOperatingBoundaries.mMimimumVoltageLimit and lLevel <= gOperatingBoundaries.mMaximumVoltageLimit then
                gStateVariables.Sens_Volt_Prot = lLevel
                lMemScratch.Actual_Volt_Prot = lLevel
                if (gAccessors.mGetSourceRangei() > gSafeOperatingArea.mCurrent * 1.01 or gStateVariables.Sour_Curr_Trig_Ampl > gSafeOperatingArea.mCurrent * 1.01)
                and lLevel > gSafeOperatingArea.mVoltage then --and (lLevel/gAccessors.mGetMeasureRangev()) - 1 >= gEpsilon  then
                    if gAccessors.mGetMeasureAutoRangev() == 0 then 
                        lLevel = gAccessors.mGetMeasureRangev()
                    else
                        lLevel = gSafeOperatingArea.mVoltage
                    end 
                end
                gAccessors.mSetSourceLimitv(lLevel)
                lMemScratch.Sens_Volt_Prot = lLevel
            else
                gErrorQueue.Add(-222)
            end 
        end
        -- [:SENSe[1]]:VOLTage[:DC]:PROTection[:LEVel]?
        gCurrentRoot.mQuery.mParameters = {gParserTable.mParseVoltageLimit}
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            --Print(lParameters[1] or gAccessors.mGetSourceLimitv())
            Print(lParameters[1] or gStateVariables.Sens_Volt_Prot)
        end
        
        -- [:SENSe[1]]:VOLTage[:DC]:PROTection:TRIPped?
        gCurrentRoot = gCommandTree["SENSE1"]["VOLTAGE"]["DC"]["PROTECTION"]["TRIPPED"]
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gResponseValues[gAccessors.mGetSourceFunc() == gDCAMPS and gSource.compliance])
        end
        
        -- [:SENSe[1]]:VOLTage[:DC]:PROTection:RSYNchronize <b>
        gCurrentRoot = gCommandTree["SENSE1"]["VOLTAGE"]["DC"]["PROTECTION"]["RSYNCHRONIZE"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mBoolean
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            if lParameters[1] then
                gStateVariables.Sens_Curr_Prot_Rsyn = true
                gStateVariables.Sens_Volt_Prot_Rsyn = true
                if gAccessors.mGetMeasureAutoRangei() == 0 then
                    gAccessors.mSetMeasureAutoRangei(smua.AUTORANGE_FOLLOW_LIMIT)
                    lMemScratch.Sens_Curr_Rang_Auto = smua.AUTORANGE_FOLLOW_LIMIT
                end
                if gAccessors.mGetMeasureAutoRangev() == 0 then
                    gAccessors.mSetMeasureAutoRangev(smua.AUTORANGE_FOLLOW_LIMIT)
                    lMemScratch.Sens_Volt_Rang_Auto = smua.AUTORANGE_FOLLOW_LIMIT
                end
            else
                gStateVariables.Sens_Curr_Prot_Rsyn = false
                gStateVariables.Sens_Volt_Prot_Rsyn = false
                if gAccessors.mGetMeasureAutoRangei() == smua.AUTORANGE_FOLLOW_LIMIT then
                    gAccessors.mSetMeasureAutoRangei(0)
                    lMemScratch.Sens_Curr_Rang_Auto = 0
                end
                if gAccessors.mGetMeasureAutoRangev() == smua.AUTORANGE_FOLLOW_LIMIT then
                    gAccessors.mSetMeasureAutoRangev(0)
                    lMemScratch.Sens_Volt_Rang_Auto = 0
                end
            end
        end
        -- [:SENSe[1]]:VOLTage[:DC]:PROTection:RSYNchronize?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gResponseValues[gStateVariables.Sens_Volt_Prot_Rsyn])
        end
        
        -- [:SENSe[1]]:CURRent[:DC]:RANGe:AUTO <b>
        gCurrentRoot = gCommandTree["SENSE1"]["CURRENT"]["DC"]["RANGE"]["AUTO"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mBoolean
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            if lParameters[1] then
                gAccessors.mSetMeasureAutoRangei(1)
                lMemScratch.Sens_Curr_Rang_Auto = 1
            else
                gAccessors.mSetMeasureAutoRangei(0)
                lMemScratch.Sens_Curr_Rang_Auto = 0
            end
            if gAccessors.mGetMeasureAutoRangei() == 0 then
                if gStateVariables.Sens_Curr_Prot_Rsyn then
                    gAccessors.mSetMeasureAutoRangei(smua.AUTORANGE_FOLLOW_LIMIT)
                    lMemScratch.Sens_Curr_Rang_Auto = smua.AUTORANGE_FOLLOW_LIMIT
                end
            end
        end
        -- [:SENSe[1]]:CURRent[:DC]:RANGe:AUTO?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gResponseValues[gAccessors.mGetMeasureAutoRangei() == 1])
        end
        
        -- [:SENSe[1]]:CURRent[:DC]:RANGe:AUTO:ULIMit?
        gCurrentRoot = gCommandTree["SENSE1"]["CURRENT"]["DC"]["RANGE"]["AUTO"]["ULIMIT"]
        gCurrentRoot.mQuery.mExecute = function ()
            for i, v in ipairs(gRangeTable.mCurrentLimit) do
                if gAccessors.mGetSourceLimiti() < v or gMathAbs(v/gAccessors.mGetSourceLimiti() - 1) < gEpsilon then
                    Print(v)
                    break
                end
            end
        end
        
        -- [:SENSe[1]]:CURRent[:DC]:RANGe:AUTO:LLIMit <n>
        gCurrentRoot = gCommandTree["SENSE1"]["CURRENT"]["DC"]["RANGE"]["AUTO"]["LLIMIT"]
        gCurrentRoot.mCommand.mParameters =
        {
            {
                mParse = gParserTable.ParseParameterChoice,
                mData =
                {
                    gParserTable.mParseNRf,
                    gParserTable.mParseCurrentLowRange,
                    gParserTable.mParseInfinity,
                }
            }
        }
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lLimit = gMathAbs(lParameters[1])
            local lCurrentLimit = gAccessors.mGetSourceLimiti()
            local lCurrentLimitRange
        
            for lIndex, lValue in ipairs(gRangeTable.mCurrentLimit) do
                if lCurrentLimit < lValue or gMathAbs(lValue/lCurrentLimit - 1) < gEpsilon then
                    lCurrentLimitRange = lValue
                    break
                end
            end
            if lLimit <= gOperatingBoundaries.mMaximumCurrentLowRange then
                if lLimit <= lCurrentLimitRange then
                    gMeasure.lowrangei = lLimit
                else
                    gErrorQueue.Add(-221)
                end
            else
                gErrorQueue.Add(-222)
            end
        end
        -- [:SENSe[1]]:CURRent[:DC]:RANGe:AUTO:LLIMit?
        gCurrentRoot.mQuery.mParameters = {gParserTable.mParseCurrentLowRange}
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(lParameters[1] or gMeasure.lowrangei)
        end
        
        -- [:SENSe[1]]:VOLTage[:DC]:RANGe:AUTO <b>
        gCurrentRoot = gCommandTree["SENSE1"]["VOLTAGE"]["DC"]["RANGE"]["AUTO"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mBoolean
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            if lParameters[1] then
                gAccessors.mSetMeasureAutoRangev(1)
                lMemScratch.Sens_Volt_Rang_Auto = 1
            else
                gAccessors.mSetMeasureAutoRangev(0)
                lMemScratch.Sens_Volt_Rang_Auto = 0
            end
            if gAccessors.mGetMeasureAutoRangev() == 0 then
                if gStateVariables.Sens_Volt_Prot_Rsyn then
                    gAccessors.mSetMeasureAutoRangev(smua.AUTORANGE_FOLLOW_LIMIT)
                    lMemScratch.Sens_Volt_Rang_Auto = smua.AUTORANGE_FOLLOW_LIMIT
                end
            end
        end
        -- [:SENSe[1]]:VOLTage[:DC]:RANGe:AUTO?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gResponseValues[gAccessors.mGetMeasureAutoRangev() == 1])
        end
        
        -- [:SENSe[1]]:VOLTage[:DC]:RANGe:AUTO:ULIMit?
        gCurrentRoot = gCommandTree["SENSE1"]["VOLTAGE"]["DC"]["RANGE"]["AUTO"]["ULIMIT"]
        gCurrentRoot.mQuery.mExecute = function ()
            for i, v in ipairs(gRangeTable.mVoltageLimit) do
                if gAccessors.mGetSourceLimitv() < v or gMathAbs(v/gAccessors.mGetSourceLimitv() - 1) < gEpsilon then
                    Print(v)
                    break
                end
            end
        end
        
        -- [:SENSe[1]]:VOLTage[:DC]:RANGe:AUTO:LLIMit <n>
        gCurrentRoot = gCommandTree["SENSE1"]["VOLTAGE"]["DC"]["RANGE"]["AUTO"]["LLIMIT"]
        gCurrentRoot.mCommand.mParameters =
        {
            {
                mParse = gParserTable.ParseParameterChoice,
                mData =
                {
                    gParserTable.mParseNRf,
                    gParserTable.mParseVoltageLowRange,
                    gParserTable.mParseInfinity,
                }
            }
        }
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lLimit = gMathAbs(lParameters[1])
            local lVoltageLimit = gAccessors.mGetSourceLimitv()
            local lVoltageLimitRange
        
            for lIndex, lValue in ipairs(gRangeTable.mVoltageLimit) do
                if lVoltageLimit < lValue or gMathAbs(lValue/lVoltageLimit - 1) < gEpsilon then
                    lVoltageLimitRange = lValue
                    break
                end
            end
            if lLimit <= gOperatingBoundaries.mMaximumVoltageLowRange then
                if lLimit <= lVoltageLimitRange then
                    gMeasure.lowrangev = lLimit
                else
                    gErrorQueue.Add(-221)
                end
            else
                gErrorQueue.Add(-222)
            end
        end
        -- [:SENSe[1]]:VOLTage[:DC]:RANGe:AUTO:LLIMit?
        gCurrentRoot.mQuery.mParameters = {gParserTable.mParseVoltageLowRange}
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(lParameters[1] or gMeasure.lowrangev)
        end
        
        -- [:SENSe[1]]:CURRent[:DC]:RANGe[:UPPer] <n> |UP|DOWN|
        gCurrentRoot = gCommandTree["SENSE1"]["CURRENT"]["DC"]["RANGE"]["UPPER"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mCurrentRange
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lRange = lParameters[1]
        
            if lRange == "UP" then
                lRange = gAccessors.mGetMeasureRangei() * 1.1
                if lRange > gOperatingBoundaries.mMaximumCurrentRange then
                    -- We are on the top range
                    return
                end
            elseif lRange == "DOWN" then
                if gAccessors.mGetMeasureRangei() <= gOperatingBoundaries.mMinimumCurrentRange then
                    -- We are on the bottom range
                    return
                end
                lRange = gAccessors.mGetMeasureRangei() * 0.09
            else
                lRange = gMathAbs(lRange)
            end
            if lRange <= gOperatingBoundaries.mMaximumCurrentRange then
                if (gAccessors.mGetSourceRangev()/gSafeOperatingArea.mVoltage) - 1 >= gEpsilon
                and lRange > gSafeOperatingArea.mCurrent then
                    gErrorQueue.Add(826)
                else
                    gAccessors.mSetMeasureRangei(lRange)
                    gAccessors.mSetSourceLimiti(gAccessors.mGetMeasureRangei())
                    lMemScratch.Sens_Curr_Rang = gAccessors.mGetMeasureRangei()
                    lMemScratch.Sens_Curr_Rang_Auto = 0
                end
            else
                gErrorQueue.Add(-222)
            end
        end
        -- [:SENSe[1]]:CURRent[:DC]:RANGe[:UPPer]?
        gCurrentRoot.mQuery.mParameters = gParserTable.mCurrentRangeQuery
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(lParameters[1] or gAccessors.mGetMeasureRangei())
        end
        
        -- [:SENSe[1]]:VOLTage[:DC]:RANGe[:UPPer] <n> |UP|DOWN|
        gCurrentRoot = gCommandTree["SENSE1"]["VOLTAGE"]["DC"]["RANGE"]["UPPER"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mVoltageRange
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lRange = lParameters[1]
        
            if lRange == "UP" then
                lRange = gAccessors.mGetMeasureRangev() * 1.1
                if lRange > gOperatingBoundaries.mMaximumVoltageRange then
                    -- We are on the top range
                    return
                end
            elseif lRange == "DOWN" then
                if gAccessors.mGetMeasureRangev() <= gOperatingBoundaries.mMinimumVoltageRange then
                    -- We are on the bottom range
                    return
                end
                lRange = gAccessors.mGetMeasureRangev() * 0.09
            else
                lRange = gMathAbs(lRange)
            end
            if lRange <= gOperatingBoundaries.mMaximumVoltageRange then
                if (gAccessors.mGetSourceRangei()/gSafeOperatingArea.mCurrent) - 1 >= gEpsilon
                and lRange > gSafeOperatingArea.mVoltage then
                    gErrorQueue.Add(826)
                else            
                    gAccessors.mSetMeasureRangev(lRange)
                    gAccessors.mSetSourceLimitv(gAccessors.mGetMeasureRangev())
                    lMemScratch.Sens_Volt_Rang = gAccessors.mGetMeasureRangev()
                    lMemScratch.Sens_Volt_Rang_Auto = 0
                    
                end        
            else
                gErrorQueue.Add(-222)
            end
        end
        -- [:SENSe[1]]:VOLTage[:DC]:RANGe[:UPPer]?
        gCurrentRoot.mQuery.mParameters = gParserTable.mVoltageRangeQuery
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(string.format("%.2f",lParameters[1] or gAccessors.mGetMeasureRangev()))
        end
        
        -- [:SENSe[1]]:AVERage:TCONtrol <name>
        gCurrentRoot = gCommandTree["SENSE1"]["AVERAGE"]["TCONTROL"]
        gCurrentRoot.mCommand.mParameters =
        {
            {
                mParse = gParserTable.ParseParameterName,
                mNames =
                {
                    ["REPEAT"]      = smua.FILTER_REPEAT_AVG,
                    ["REP"]         = smua.FILTER_REPEAT_AVG,
                    ["MOVING"]      = smua.FILTER_MOVING_AVG,
                    ["MOV"]         = smua.FILTER_MOVING_AVG,
                }
            }
        }
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            gMeasure.filter.type = lParameters[1]
            lMemScratch.Sens_Aver_Tcon = lParameters[1]
        end
        -- [:SENSe[1]]:AVERage:TCONtrol?
        gCurrentRoot.mQuery.mExecute = function ()
            if gMeasure.filter.type == smua.FILTER_REPEAT_AVG then
                Print("REP")
            elseif gMeasure.filter.type == smua.FILTER_MOVING_AVG then
                Print("MOV")
            end
        end
        
        -- [:SENSe[1]]:AVERage:COUNt <n>
        gCurrentRoot = gCommandTree["SENSE1"]["AVERAGE"]["COUNT"]
        gCurrentRoot.mCommand.mParameters =
        {
            {
                mParse = gParserTable.ParseParameterChoice,
                mData =
                {
                    gParserTable.mParseInteger,
                    gParserTable.mParseFilterCount,
                    gParserTable.mParseInfinity,
                }
            }
        }
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lCount = lParameters[1]
            if lCount >= 1 and lCount <= 100 then
                gMeasure.filter.count = lCount
                lMemScratch.Sens_Aver_Coun = lCount
            else
                gErrorQueue.Add(-222)
            end
        end
        -- [:SENSe[1]]:AVERage:COUNt?
        gCurrentRoot.mQuery.mParameters = {gParserTable.mParseFilterCount}
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(tostring(lParameters[1] or gMeasure.filter.count))
        end
        
        -- [:SENSe[1]]:AVERage:STATe <b>
        gCurrentRoot = gCommandTree["SENSE1"]["AVERAGE"]["STATE"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mBoolean
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            if lParameters[1] then
                gMeasure.filter.enable = smua.FILTER_ON
                lMemScratch.Sens_Aver_Stat = smua.FILTER_ON
            else
                gMeasure.filter.enable = smua.FILTER_OFF
                lMemScratch.Sens_Aver_Stat = smua.FILTER_OFF
            end
        end
        -- [:SENSe[1]]:AVERage:STATe?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gResponseValues[gMeasure.filter.enable == smua.FILTER_ON])
        end
        
        -- [:SENSe[1]]:RESistance:MODE <name>
        gCurrentRoot = gCommandTree["SENSE1"]["RESISTANCE"]["MODE"]
        gCurrentRoot.mCommand.mParameters =
        {
            {
                mParse = gParserTable.ParseParameterName,
                mNames =
                {
                    ["MANUAL"]      = "MAN",
                    ["MAN"]         = "MAN",
                    --["AUTO"]        = "AUTO",
                }
            }
        }
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            gStateVariables.Sens_Res_Mode = lParameters[1]
        end
        -- [:SENSe[1]]:RESistance:MODE?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gStateVariables.Sens_Res_Mode)
        end
        
        
        -- [:SENSe[1]]:RESistance:RANGE[:UPPer] <n> |UP|DOWN|
        gCurrentRoot = gCommandTree["SENSE1"]["RESISTANCE"]["RANGE"]["UPPER"]
        gCurrentRoot.mCommand.mParameters =
        {
            {
                mParse = gParserTable.ParseParameterChoice,
                mData =
                {
                    gParserTable.mParseNRf,
                    gParserTable.mParseResistanceRange,
                    gParserTable.mParseUpDown,
                    gParserTable.mParseInfinity,
                }
            }
        }
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lRange = lParameters[1]
        
            if lRange == "UP" then
                lRange = gStateVariables.Sens_Res_Range * 1.1
                if lRange > gOperatingBoundaries.mMaximumResistanceRange then
                    -- We are on the top range
                    return
                end
            elseif lRange == "DOWN" then
                if gStateVariables.Sens_Res_Range <= gOperatingBoundaries.mMinimumResistanceRange then
                    -- We are on the bottom range
                    return
                end
                lRange = gStateVariables.Sens_Res_Range * 0.09
            else
                lRange = gMathAbs(lRange)
            end
            if lRange <= gOperatingBoundaries.mMaximumResistanceRange then
                for lIndex, lValue in ipairs(gRangeTable.mResistance) do
                    if lRange < lValue then
                        gStateVariables.Sens_Res_Range = lValue
                        break
                    end
                end
            else
                gErrorQueue.Add(-222)
            end
        end
        -- [:SENSe[1]]:RESistance:RANGE[:UPPer]?
        gCurrentRoot.mQuery.mParameters = {gParserTable.mParseResistanceRange}
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(lParameters[1] or gStateVariables.Sens_Res_Range)
        end
        
        -- [:SENSe[1]]:RESistance:RANGE[:UPPer]:AUTO <b>
        gCurrentRoot = gCommandTree["SENSE1"]["RESISTANCE"]["RANGE"]["UPPER"]["AUTO"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mBoolean
        gCurrentRoot.mCommand.mExecute = NullFunction
        -- [:SENSe[1]]:RESistance:RANGE[:UPPer]:AUTO?
        gCurrentRoot.mQuery.mExecute = function ()
            -- Print 0 Always OFF
            Print("0")
        end
        
        -----------------------------------------------------------------------
        -- SYSTem subsystem commands
        -----------------------------------------------------------------------
        -- SYSTem:PRESet
        gCurrentRoot = gCommandTree["SYSTEM"]["PRESET"]
        gCurrentRoot.mCommand.mExecute = function ()
            --smua.reset()
            smua.abort()
            gAbortExecuted = true
            reset()
            ResetDefaults()
            presetDefaults()
        end
        
        -- SYSTem:POSetup <name>
        -- user setup 0-4 in 2400 correspond to user setups 1-5
        gCurrentRoot = gCommandTree["SYSTEM"]["POSETUP"]
        gCurrentRoot.mCommand.mParameters =
        {
            {
                mParse = gParserTable.ParseParameterName,
                mNames =
                {
                    ["RST"]         = 0,
                    ["PRES"]        = 0,
                    ["PRESET"]      = 0,
                    ["SAV0"]        = 1,
                    ["SAV1"]        = 2,
                    ["SAV2"]        = 3,
                    ["SAV3"]        = 4,
                    ["SAV4"]        = 5,
                }
            }
        }
        gCurrentRoot.mCommand.mExecute = function ()--lParameters)
            --setup.poweron = lParameters[1]
        end
        -- SYSTem:POSetup?
        gCurrentRoot.mQuery.mExecute = function ()
            if setup.poweron == 0 then
                Print("RST")
            elseif setup.poweron == 1 then
                Print("SAV0")
            elseif setup.poweron == 2 then
                Print("SAV1")
            elseif setup.poweron == 3 then
                Print("SAV2")
            elseif setup.poweron == 4 then
                Print("SAV3")
            elseif setup.poweron == 5 then
                Print("SAV4")
            end
        end
        
        -- SYSTem:VERSion?
        gCurrentRoot = gCommandTree["SYSTEM"]["VERSION"]
        gCurrentRoot.mQuery.mExecute = function ()
            Print("1996.0")
        end
        
        -- SYSTem:ERRor[:NEXT]?
        gCurrentRoot = gCommandTree["SYSTEM"]["ERROR"]["NEXT"]
        gCurrentRoot.mQuery.mExecute = function ()
             gErrorQueue.ReadError()
        end
        
        -- SYSTem:ERRor:ALL?
        gCurrentRoot = gCommandTree["SYSTEM"]["ERROR"]["ALL"]
        gCurrentRoot.mQuery.mExecute = function ()
             gErrorQueue.ReadErrorAll()
        end
        
        -- SYSTem:ERRor:COUNt?
        gCurrentRoot = gCommandTree["SYSTEM"]["ERROR"]["COUNT"]
        gCurrentRoot.mQuery.mExecute = function ()
             gErrorQueue.ErrorCount()
        end
        
        -- SYSTem:ERRor:CODE[:NEXT]?
        gCurrentRoot = gCommandTree["SYSTEM"]["ERROR"]["CODE"]["NEXT"]
        gCurrentRoot.mQuery.mExecute = function ()
             gErrorQueue.ReadErrorCode()
        end
        
        -- SYSTem:ERRor:CODE:ALL?
        gCurrentRoot = gCommandTree["SYSTEM"]["ERROR"]["CODE"]["ALL"]
        gCurrentRoot.mQuery.mExecute = function ()
             gErrorQueue.ReadErrorCodeAll()
        end
        
        -- SYSTem:CLEar
        gCurrentRoot = gCommandTree["SYSTEM"]["CLEAR"]
        gCurrentRoot.mCommand.mExecute = function ()
             gErrorQueue.Clear()
        end
        
        -- SYSTem:AZERo:STATe <name>
        gCurrentRoot = gCommandTree["SYSTEM"]["AZERO"]["STATE"]
        gCurrentRoot.mCommand.mParameters =
        {
            {
                mParse = gParserTable.ParseParameterChoice,
                mData =
                {
                    {
                        mParse = gParserTable.ParseParameterName,
                        mNames =
                        {
                            ["ONCE"]        = "ONCE",
                        }
                    },
                    {mParse = gParserTable.ParseParameterBoolean},
                }
            }
        }
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            if lParameters[1] then
                if lParameters[1] == true then
                    gAccessors.mSetMeasureAutoZero(smua.AUTOZERO_AUTO)
                    lMemScratch.Syst_Azer_Stat = smua.AUTOZERO_AUTO            
                else -- lParameters[1] == "ONCE"
                    gAccessors.mSetMeasureAutoZero(smua.AUTOZERO_ONCE)
                    lMemScratch.Syst_Azer_Stat = smua.AUTOZERO_OFF
                end
            else -- false
                gAccessors.mSetMeasureAutoZero(smua.AUTOZERO_OFF)
                lMemScratch.Syst_Azer_Stat = smua.AUTOZERO_OFF
            end
        end
        -- SYSTem:AZERo:STATe?
        gCurrentRoot.mQuery.mExecute = function ()
            if gAccessors.mGetMeasureAutoZero() == smua.AUTOZERO_ONCE then
                Print("0")
            elseif gAccessors.mGetMeasureAutoZero() == smua.AUTOZERO_AUTO then
                Print("1")
            else -- if gAccessors.mGetMeasureAutoZero() == smua.AUTOZERO_OFF then
                Print("0")
            end
        end
        
        -- :SYSTem:AZERo:CACHing:STATe <b>
        gCurrentRoot = gCommandTree["SYSTEM"]["AZERO"]["CACHING"]["STATE"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mBoolean
        gCurrentRoot.mCommand.mExecute = function ()
            -- No action
        end
        gCurrentRoot.mQuery.mExecute = function ()
            Print(1)
        end
        
        -- SYSTem:AZERo:CACHing:NPLCycles?
        gCurrentRoot = gCommandTree["SYSTEM"]["AZERO"]["CACHING"]["NPLCYCLES"]
        gCurrentRoot.mQuery.mExecute = function ()
            Print("0")
        end
        
        -- SYSTem:AZERo:CACHing:REFResh
        gCurrentRoot = gCommandTree["SYSTEM"]["AZERO"]["CACHING"]["REFRESH"]
        gCurrentRoot.mCommand.mExecute = function ()
            -- No action
        end
        
        -- :SYSTem:AZERo:CACHing:RESet
        gCurrentRoot = gCommandTree["SYSTEM"]["AZERO"]["CACHING"]["RESET"]
        gCurrentRoot.mCommand.mExecute = function ()
            -- No action
        end
        
        -- SYSTem:RSENse <b>
        gCurrentRoot = gCommandTree["SYSTEM"]["RSENSE"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mBoolean
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            if lParameters[1] then
                gAccessors.mSetSense(smua.SENSE_REMOTE)
                lMemScratch.Syst_Rsen = smua.SENSE_REMOTE
            else
                gAccessors.mSetSense(smua.SENSE_LOCAL)
                lMemScratch.Syst_Rsen = smua.SENSE_LOCAL
            end
        end
        -- SYSTem:RSENse?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gResponseValues[gAccessors.mGetSense() == smua.SENSE_REMOTE])
        end
        
        -- SYSTem:BEEPer[:IMMediate] <freq, time>
        gCurrentRoot = gCommandTree["SYSTEM"]["BEEPER"]["IMMEDIATE"]
        gCurrentRoot.mCommand.mParameters =
        {
            gParserTable.mParseNRf,
            {
                mParse = gParserTable.ParseParameterNRf,
                mOptional = true,
                mDefault = 1,
            },
        }
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lFrequency = lParameters[1]
            local lTime = lParameters[2]
        
            if lFrequency >= 65 and lFrequency <= 2e6 and lTime >= 0 and lTime <= 7.9 then
                if lTime > 512/lFrequency then
                    lTime = 512/lFrequency
                end
                if lTime < 0.1 then
                    lTime = 0.1
                end
                beeper.beep(lTime, lFrequency)
            else
                gErrorQueue.Add(-222)
            end
        end
        
        -- SYSTem:BEEPer:STATe <b>
        gCurrentRoot = gCommandTree["SYSTEM"]["BEEPER"]["STATE"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mBoolean
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            if lParameters[1] then
                beeper.enable = beeper.ON
            else
                beeper.enable = beeper.OFF
            end
        end
        -- SYSTem:BEEPer:STATe?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gResponseValues[beeper.enable == beeper.ON])
        end
        
        -- SYSTem:LFRequency <freq>
        gCurrentRoot = gCommandTree["SYSTEM"]["LFREQUENCY"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mInteger
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lFrequency = lParameters[1]
            if lFrequency == 50 then
                localnode.linefreq = lFrequency
            elseif lFrequency == 60 then
                localnode.linefreq = lFrequency
            else
                gErrorQueue.Add(-222)
            end
        end
        -- SYSTem:LFRequency?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(tostring(localnode.linefreq))
        end
        
        -- SYSTem:LFRequency:AUTO <b>
        gCurrentRoot = gCommandTree["SYSTEM"]["LFREQUENCY"]["AUTO"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mBoolean
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            localnode.autolinefreq = lParameters[1]
        end
        -- SYSTem:LFRequency:AUTO?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gResponseValues[localnode.autolinefreq])
        end
        
        -- SYSTem:TIME?
        gCurrentRoot = gCommandTree["SYSTEM"]["TIME"]
        gCurrentRoot.mQuery.mExecute = function ()
            Print(os.time() - gSystemClockOffset)
        end
        
        -- SYSTem:TIME:RESet
        gCurrentRoot = gCommandTree["SYSTEM"]["TIME"]["RESET"]
        gCurrentRoot.mCommand.mExecute = function ()
           gSystemClockOffset = os.time()
        end
        
        -- SYSTem:TIME:RESet:AUTO <b>
        gCurrentRoot = gCommandTree["SYSTEM"]["TIME"]["RESET"]["AUTO"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mBoolean
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            gStateVariables.Syst_Time_Res_Auto = lParameters[1]
        end
        -- SYSTem:TIME:RESet:AUTO?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gResponseValues[gStateVariables.Syst_Time_Res_Auto])
        end
        
        -- SYSTem:MEP:STATe?
        gCurrentRoot = gCommandTree["SYSTEM"]["MEP"]["STATE"]
        gCurrentRoot.mQuery.mExecute = function ()
            Print("1")
        end
        
        -- SYSTem:RWLock <b>
        gCurrentRoot = gCommandTree["SYSTEM"]["RWLOCK"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mBoolean
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            if lParameters[1] then
                display.locallockout = display.LOCK
            else
                display.locallockout = display.UNLOCK
            end
        end
        
        -- SYSTem:MEMory:INITialize
        gCurrentRoot = gCommandTree["SYSTEM"]["MEMORY"]["INITIALIZE"]
        gCurrentRoot.mCommand.mExecute = function ()
            Init.SysMemInit()
        end
        
        -- SYSTem:REMote
        gCurrentRoot = gCommandTree["SYSTEM"]["REM"]
        gCurrentRoot.mCommand.mExecute = function ()
        end
        
        -- Commands not Supported
        -- :SYSTem:KEY <n>
        -- :SYSTem:KEY?
        -- :SYSTem:GUARd OHMS|CABLe
        -- :SYSTem:GUARd?
        -- :SYSTem:CCHeck <b>
        -- :SYSTem:CCHeck:RESistance <NRf>
        
        -----------------------------------------------------------------------
        -- STATUS Subsystem
        -----------------------------------------------------------------------
        
        -- STATus:MEASurement[:EVENt]?
        gCurrentRoot = gCommandTree["STATUS"]["MEASUREMENT"]["EVENT"]
        gCurrentRoot.mQuery.mExecute = function ()
            PrintStatusRegister(measStatus.mEvent)
            -- Clear the event register after it is read
            StatusModel.ClearEvent(measStatus)
        end
        
        -- STATus:MEASurement:ENABle <NDN> OR <NRf>
        gCurrentRoot = gCommandTree["STATUS"]["MEASUREMENT"]["ENABLE"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mNDN
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lValue = lParameters[1]
            if lValue < 0 then
                gErrorQueue.Add(-222)
            else
                if lValue > 32767 then
                    lValue = 32767
                end
                StatusModel.SetEnable(measStatus, lValue)
            end
        end
        -- STATus:MEASurement:ENABle?
        gCurrentRoot.mQuery.mExecute = function ()
            PrintStatusRegister(measStatus.mEventEnable)
        end
        
        -- STATus:MEASurement:CONDition?
        gCurrentRoot = gCommandTree["STATUS"]["MEASUREMENT"]["CONDITION"]
        gCurrentRoot.mQuery.mExecute = function ()
            PrintStatusRegister(measStatus.mCondition)
        end
        
        --:STATus:OPERation[:EVENt]?
        gCurrentRoot = gCommandTree["STATUS"]["OPERATION"]["EVENT"]
        gCurrentRoot.mQuery.mExecute = function ()
            PrintStatusRegister(operStatus.mEvent)
            StatusModel.ClearEvent(operStatus)
        end
        
        -- STATus:OPERation:ENABle <NDN> OR <NRf>
        gCurrentRoot = gCommandTree["STATUS"]["OPERATION"]["ENABLE"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mNDN
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lValue = lParameters[1]
            if lValue < 0 then
                gErrorQueue.Add(-222)
            else
                if lValue > 32767 then
                    lValue = 32767
                end
                StatusModel.SetEnable(operStatus, lValue)
            end
        end
        -- STATus:OPERation:ENABle?
        gCurrentRoot.mQuery.mExecute = function ()
            PrintStatusRegister(operStatus.mEventEnable)
        end
        
        -- STATus:OPERation:CONDition?
        gCurrentRoot = gCommandTree["STATUS"]["OPERATION"]["CONDITION"]
        gCurrentRoot.mQuery.mExecute = function ()
           PrintStatusRegister(operStatus.mCondition)
        end
        
        -- STATus:QUEStionable[:EVENt]?
        gCurrentRoot = gCommandTree["STATUS"]["QUESTIONABLE"]["EVENT"]
        gCurrentRoot.mQuery.mExecute = function ()
            PrintStatusRegister(quesStatus.mEvent)
            StatusModel.ClearEvent(quesStatus)
        end
        
        -- STATus:QUEStionable:ENABle <NDN> OR <NRf>
        gCurrentRoot = gCommandTree["STATUS"]["QUESTIONABLE"]["ENABLE"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mNDN
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lValue = lParameters[1]
            if lValue < 0 then
                gErrorQueue.Add(-222)
            else
                if lValue > 32767 then
                    lValue = 32767
                end
                StatusModel.SetEnable(quesStatus, lValue)
            end
        end
        -- STATus:QUEStionable:ENABle?
        gCurrentRoot.mQuery.mExecute = function ()
            PrintStatusRegister(quesStatus.mEventEnable)
        end
        
        -- STATus:QUEStionable:CONDition?
        gCurrentRoot = gCommandTree["STATUS"]["QUESTIONABLE"]["CONDITION"]
        gCurrentRoot.mQuery.mExecute = function ()
            PrintStatusRegister(quesStatus.mCondition)
        end
        
        -- *ESE <NRf> | <NDN>
        gCurrentRoot = gCommandTree["*ESE"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mNDN
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lValue = lParameters[1]
            if lValue >= 0 and lValue <= 255 then
                StatusModel.SetEnable(standardStatus, lValue)
            else
                gErrorQueue.Add(-222)
            end
        end
        -- *ESE?
        gCurrentRoot.mQuery.mExecute = function ()
            PrintStatusRegister(tostring(standardStatus.mEventEnable))
        end
        
        -- *ESR?
        gCurrentRoot = gCommandTree["*ESR"]
        gCurrentRoot.mQuery.mExecute = function ()
            PrintStatusRegister(standardStatus.mEvent)
            StatusModel.ClearEvent(standardStatus)
        end
        
        -- STATus:PRESet
        gCurrentRoot = gCommandTree["STATUS"]["PRESET"]
        gCurrentRoot.mCommand.mExecute = function ()
            -- Clear All Event Enable registers
            StatusModel.SetEnable(measStatus, 0)
            StatusModel.SetEnable(quesStatus, 0)
            StatusModel.SetEnable(operStatus, 0)
            StatusModel.SetEnable(standardStatus, 0)
            gErrorQueue.EnableErrorEvents({-440, -100, 500, 900})
        end
        
        -- STATus:QUEue[:NEXT]?
        gCurrentRoot = gCommandTree["STATUS"]["QUEUE"]["NEXT"]
        gCurrentRoot.mQuery.mExecute = function ()
            gErrorQueue.ReadError()
        end
        
        -- STATus:QUEue:ENABle <LIST>
        gCurrentRoot = gCommandTree["STATUS"]["QUEUE"]["ENABLE"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mNumList
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            gErrorQueue.EnableErrorEvents(lParameters[1])
        end
        -- STATus:QUEue:ENABle?
        gCurrentRoot.mQuery.mExecute = function ()
             gErrorQueue.PrintErrorEvents(true)
        end
        
        -- STATus:QUEue:DISable <LIST>
        gCurrentRoot = gCommandTree["STATUS"]["QUEUE"]["DISABLE"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mNumList
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            gErrorQueue.DisableErrorEvents(lParameters[1])
        end
        -- STATus:QUEue:DISable?
        gCurrentRoot.mQuery.mExecute = function ()
            gErrorQueue.PrintErrorEvents(false)
        end
        
        -- STATus:QUEue:CLEar
        gCurrentRoot = gCommandTree["STATUS"]["QUEUE"]["CLEAR"]
        gCurrentRoot.mCommand.mExecute = function ()
            gErrorQueue.Clear()
        end
        
        -- *SRE <NRf> | <NDN>
        gCurrentRoot = gCommandTree["*SRE"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mNDN
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lValue = lParameters[1]
            if lValue >= 0 and lValue <= 255 then
                status.request_enable = lValue
                UpdateStatusModel()
            else
                gErrorQueue.Add(-222)
            end
        end
        -- *SRE?
        gCurrentRoot.mQuery.mExecute = function ()
            PrintStatusRegister(tostring(status.request_enable))
        end
        
        -- *STB?
        gCurrentRoot = gCommandTree["*STB"]
        gCurrentRoot.mQuery.mExecute = function ()
            -- gRemoteComm.status.override is set to 175 and bitwise not of gRemoteComm.status.override is 80
            PrintStatusRegister(tostring(bit.bitor(bit.bitand(StatusModel.mStatus, 175), bit.bitand(status.condition, 80))))
        end
        
        -----------------------------------------------------------------------
        --  :CALCulate[1] subsystem
        -----------------------------------------------------------------------
        
        -- CALCulate[1]:MATH[:EXPression]:CATalog?
        gCurrentRoot = gCommandTree["CALCULATE1"]["MATH"]["EXPRESSION"]["CATALOG"]
        gCurrentRoot.mQuery.mExecute = function ()
            local lInsertComa = false
            for lIndex,lValue in ipairs(gMathCatalog) do
                if lInsertComa then
                    Print(",")
                end
                Print('"')
                Print(lValue)
                Print('"')
                lInsertComa = true
            end
            Print(',"%DEV"')
        end
        
        -- CALCulate[1]:MATH[:EXPression]:NAME <name>
        gCurrentRoot = gCommandTree["CALCULATE1"]["MATH"]["EXPRESSION"]["NAME"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mString
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            if not string.find(lParameters[1], "^%w[%w_]*$") then
                gErrorQueue.Add(-151)
            else
                lParameters[1] = string.upper(lParameters[1])
                -- If name does not exist
                if not gMathCatalog[lParameters[1]] then
                    -- If there is no undefined expression
                    if not gStateVariables.Calc1_Undefined_Expression_Exists then
                        for i = 5, 9 do
                            if not gMathCatalog[i] then
                                gMathCatalog[i] = lParameters[1]
                                gMathCatalog[lParameters[1]] = {}
                                gMathCatalog[lParameters[1]].mExpression = BuildExpression("(9.91E37)", 1)
                                gMathCatalog[lParameters[1]].mUnits = gStateVariables.Calc1_Selected.mTempUnits
                                gMathCatalog[lParameters[1]].mTempUnits = gMathCatalog[lParameters[1]].mUnits
                                gMathCatalog[lParameters[1]].mName = lParameters[1]
                                gMathCatalog[lParameters[1]].mDefined = false
                                gStateVariables.Calc1_Selected = gMathCatalog[lParameters[1]]
                                gStateVariables.Calc1_Selected_Index = i
                                gStateVariables.Calc1_Undefined_Expression_Exists = true
                                break
                            elseif i == 9 then
                                --Expression list full
                                gErrorQueue.Add(804)
                            end
                        end
                    else
                        gErrorQueue.Add(805)
                    end
                -- Select the function name
                else
                    for i = 1, 9 do
                        if gMathCatalog[i] == lParameters[1] then
                            gStateVariables.Calc1_Selected_Index = i
                            gStateVariables.Calc1_Selected = gMathCatalog[lParameters[1]]
                            gStateVariables.Calc1_Selected.mTempUnits = gMathCatalog[lParameters[1]].mTempUnits
                            break
                        end
                    end
                end
                lMemScratch.Calc1_Math_Name = gStateVariables.Calc1_Selected.mName
            end
        end
        
        -- CALCulate[1]:MATH[:EXPression]:NAME?
        gCurrentRoot.mQuery.mExecute = function ()
            Print('"')
            Print(gStateVariables.Calc1_Selected.mName)
            Print('"')
        end
        
        -- CALCulate[1]:MATH[:EXPRession]:DELETE[:SELected] <name>
        gCurrentRoot = gCommandTree["CALCULATE1"]["MATH"]["EXPRESSION"]["DELETE"]["SELECTED"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mString
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            lParameters[1] = lParameters[1]
            if gMathCatalog[lParameters[1]] then
                for i = 1, 9 do
                    if gMathCatalog[i] and gMathCatalog[i] == lParameters[1] then
                        if i >= 5 then
                            if not gMathCatalog[gMathCatalog[i]].mDefined then
                                 gStateVariables.Calc1_Undefined_Expression_Exists = false
                            end
                            gMathCatalog[gMathCatalog[i]] = nil
                            gMathCatalog[i] = nil
                        else
                            gErrorQueue.Add(808)
                        end
                        break
                    end
                end
            else
                gErrorQueue.Add(806)
            end
        end
        
        -- CALCulate[1]:MATH[:EXPression]:DELETE:ALL
        gCurrentRoot = gCommandTree["CALCULATE1"]["MATH"]["EXPRESSION"]["DELETE"]["ALL"]
        gCurrentRoot.mCommand.mExecute = function ()
            for i = 5, 9 do
                if gMathCatalog[i] then
                    gMathCatalog[gMathCatalog[i]] = nil
                    gMathCatalog[i] = nil
                    gStateVariables.Calc1_Undefined_Expression_Exists = false
                end
            end
        end
        
        -- CALCulate[1]:MATH:UNITs <name>
        gCurrentRoot = gCommandTree["CALCULATE1"]["MATH"]["UNITS"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mString
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            lUnits = lParameters[1]
            if string.len(lUnits) < 3 then
                lUnits = lUnits .. string.rep(" ", 3 - string.len(lUnits))
            end
            if string.len(lUnits) <= 3 then
                --gStateVariables.Calc1_Selected.mUnits = lUnits
                gStateVariables.Calc1_Selected.mTempUnits = lUnits
            else
                gErrorQueue.Add(-223)
            end
        end
        -- CALCulate[1]:MATH[:EXPression]:UNITs?
        gCurrentRoot.mQuery.mExecute = function ()
            --local lUnits = string.gsub(gStateVariables.Calc1_SelectedUNITS, '"', '""')
            --local lUnits = gStateVariables.Calc1_SelectedUNITS
            --local lUnits = gStateVariables.Calc1_Selected.mUnits
            local lUnits = gStateVariables.Calc1_Selected.mTempUnits
            Print('"')
            Print(lUnits)
            Print('"')
        end
        
        -- CALCulate[1]:STATe <b>
        gCurrentRoot = gCommandTree["CALCULATE1"]["STATE"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mBoolean
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            gStateVariables.Calc1_Stat = lParameters[1]
            lMemScratch.Calc1_Stat = lParameters[1]
        end
        -- CALCulate[1]:STATe?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gResponseValues[gStateVariables.Calc1_Stat])
        end
        
        -- CALCulate[1]:MATH[:EXPression][:DEFine] <form>
        gCurrentRoot = gCommandTree["CALCULATE1"]["MATH"]["EXPRESSION"]["DEFINE"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mExpression
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lExpression
            if gStateVariables.Calc1_Selected_Index > 4 and gStateVariables.Calc1_Selected_Index < 10 then
                lExpression = BuildExpression(string.gsub(lParameters[1], "%s", ""), 1)
                if lExpression then
                    gStateVariables.Calc1_Selected.mExpression = lExpression
                    if not gMathCatalog[gStateVariables.Calc1_Selected_Index] then
                        gStateVariables.Calc1_Selected.mName = ""
                    end
                    if not gStateVariables.Calc1_Selected.mDefined then
                        gStateVariables.Calc1_Undefined_Expression_Exists = false
                    end
                end
            else
                gErrorQueue.Add(807)
            end
        end
        -- CALCulate[1]:MATH[:EXPression][:DEFine]?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gStateVariables.Calc1_Selected.mExpression.mText)
        end
        
        -- CALCulate[1]:DATA?
        gCurrentRoot = gCommandTree["CALCULATE1"]["DATA"]
        gCurrentRoot.mQuery.mExecute = function ()
            if gArm.count ~= 0 then
                if gCalculate1Buffer.mCount > 0 then
                    PrintCalculateBuffer(1,gCalculate1Buffer.mCount, gCalculate1Buffer)
                else
                    gErrorQueue.Add(-230)
                end
            else
                gErrorQueue.Add(830)
            end
        end
        
        -- CALCulate[1]:DATA:LATest?
        gCurrentRoot = gCommandTree["CALCULATE1"]["DATA"]["LATEST"]
        gCurrentRoot.mQuery.mExecute = function ()
            if gArm.count ~= 0 then
                if gCalculate1Buffer.mCount > 0 then
                    PrintCalculateBuffer(gCalculate1Buffer.mCount,gCalculate1Buffer.mCount, gCalculate1Buffer)
                else
                    gErrorQueue.Add(-230)
                end
            else
                gErrorQueue.Add(830)
            end
        end
        -----------------------------------------------------------------------
        -- CALCulate2 Subsystem
        -----------------------------------------------------------------------
        
        -- CALCulate2:FEED <name>
        gCurrentRoot = gCommandTree["CALCULATE2"]["FEED"]
        gCurrentRoot.mCommand.mParameters =
        {
            {
                mParse = gParserTable.ParseParameterName,
                mNames =
                {
                    ["CALCULATE1"]  = "CALC1",
                    ["CALCULATE"]   = "CALC1",
                    ["CALC1"]       = "CALC1",
                    ["CALC"]        = "CALC1",
                    ["CURRENT"]     = "CURR",
                    ["CURR"]        = "CURR",
                    ["VOLTAGE"]     = "VOLT",
                    ["VOLT"]        = "VOLT",
                    ["RESISTANCE"]  = "RES",
                    ["RES"]         = "RES",
                }
            }
        }
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            gStateVariables.Calc2_Feed = lParameters[1]
            lMemScratch.Calc2_Feed = lParameters[1]
        end
        -- CALCulate2:FEED?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gStateVariables.Calc2_Feed)
        end
        
        -- CALCulate2:NULL:OFFSet <n>
        gCurrentRoot = gCommandTree["CALCULATE2"]["NULL"]["OFFSET"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mGeneralZero
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lOffset = lParameters[1]
            if lOffset >= -9.999999E+20 and lOffset <= 9.999999E+20 then
                gStateVariables.Calc2_Null_Offs = lOffset
                lMemScratch.Calc2_Null_Offs = lOffset
            else
                gErrorQueue.Add(-222)
            end
        end
        -- CALCulate2:NULL:OFFSet?
        gCurrentRoot.mQuery.mParameters = gParserTable.mGeneralZeroQuery
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(lParameters[1] or gStateVariables.Calc2_Null_Offs)
        end
        
        -- CALCulate2:NULL:STATe <b>
        gCurrentRoot = gCommandTree["CALCULATE2"]["NULL"]["STATE"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mBoolean
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            gStateVariables.Calc2_Null_Stat = lParameters[1]
            lMemScratch.Calc2_Null_Stat = lParameters[1]
        end
        -- CALCulate2:NULL:STATe?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gResponseValues[gStateVariables.Calc2_Null_Stat])
        end
        
        -- CALCulate2:NULL:ACQuire
        gCurrentRoot = gCommandTree["CALCULATE2"]["NULL"]["ACQUIRE"]
        gCurrentRoot.mCommand.mExecute = function ()
            if gSampleBuffer.mCount > 0 then
                if gStateVariables.Calc2_Feed == "VOLT" then
                    if gSampleBuffer.mVoltage[gSampleBuffer.mCount] ~= gNan then
                       gStateVariables.Calc2_Null_Offs = gSampleBuffer.mVoltage[gSampleBuffer.mCount]
                    end
                elseif gStateVariables.Calc2_Feed == "CURR" then
                    if gSampleBuffer.mCurrent[gSampleBuffer.mCount] ~= gNan then
                       gStateVariables.Calc2_Null_Offs = gSampleBuffer.mCurrent[gSampleBuffer.mCount]
                    end
                elseif gStateVariables.Calc2_Feed == "RES" then
                    if gSampleBuffer.mResistance[gSampleBuffer.mCount] ~= gNan then
                       gStateVariables.Calc2_Null_Offs = gSampleBuffer.mResistance[gSampleBuffer.mCount]
                    end
                elseif gStateVariables.Calc2_Feed == "CALC1" then
                    if gCalculate1Buffer.mCount > 0 then
                        if gCalculate1Buffer.mData[gCalculate1Buffer.mCount] ~= gNan then
                            gStateVariables.Calc2_Null_Offs = gCalculate1Buffer.mData[gCalculate1Buffer.mCount]
                        end
                    end
                end
            end
            lMemScratch.Calc2_Null_Offs = gStateVariables.Calc2_Null_Offs
        end
        
        -- CALCulate2:DATA:LATEST?
        gCurrentRoot = gCommandTree["CALCULATE2"]["DATA"]["LATEST"]
        gCurrentRoot.mQuery.mExecute = function ()
            if gArm.count ~= 0 then
                if gCalculate2Buffer.mCount > 0 then
                    PrintCalculateBuffer(gCalculate2Buffer.mCount, gCalculate2Buffer.mCount, gCalculate2Buffer)
                else
                    gErrorQueue.Add(-230)
                end
            else
                gErrorQueue.Add(830)
            end
        end
        
        -- CALCulate2:DATA?
        gCurrentRoot = gCommandTree["CALCULATE2"]["DATA"]
        gCurrentRoot.mQuery.mExecute = function ()
            if gArm.count ~= 0 then
                if gCalculate2Buffer.mCount > 0 then
                    PrintCalculateBuffer(1, gCalculate2Buffer.mCount, gCalculate2Buffer)
                else
                    gErrorQueue.Add(-230)
                end
            else
                gErrorQueue.Add(830)
            end
        end
        
        ----------------------- LIMit[1] -----------------------------------
        -- CALCulate2:LIMit[1]:COMPliance:FAIL <name>
        gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT1"]["COMPLIANCE"]["FAIL"]
        gCurrentRoot.mCommand.mParameters =
        {
            {
                mParse = gParserTable.ParseParameterName,
                mNames =
                {
                    ["IN"]          = "IN",
                    ["OUT"]         = "OUT",
                }
            }
        }
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            gStateVariables.Calc2_Lim1_Fail = lParameters[1]
            lMemScratch.Calc2_Lim1_Fail = lParameters[1]
        end
        -- CALCulate2:LIMit[1]:COMPliance:FAIL?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gStateVariables.Calc2_Lim1_Fail)
        end
        if gDigioSupport then
            -- CALCulate2:LIMit[1]:COMPliance:SOURce2 <NRf> | <NDN>
            gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT1"]["COMPLIANCE"]["SOURCE2"]
            gCurrentRoot.mCommand.mParameters = gParserTable.mNDN
            gCurrentRoot.mCommand.mExecute = function (lParameters)
                local lValue = lParameters[1]
                if lValue >= 0 and lValue <= gStateVariables.Sour2_Bsize_MaxValue then
                    gStateVariables.Calc2_Lim1_Sour2 = lValue
                    lMemScratch.Calc2_Lim1_Sour2 = lValue
                else
                    gErrorQueue.Add(-222)
                end
            end
            -- CALCulate2:LIMit[1]:COMPliance:SOURce2?
            gCurrentRoot.mQuery.mExecute = function ()
                PrintSource2(gStateVariables.Calc2_Lim1_Sour2)
            end
        end
        -- CALCulate2:LIMit[1]:STATe <b>
        gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT1"]["STATE"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mBoolean
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            gStateVariables.Calc2_Lim1_Stat = lParameters[1]
            lMemScratch.Calc2_Lim1_Stat = lParameters[1]
        end
        -- CALCulate2:LIMit[1]:STATe?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gResponseValues[gStateVariables.Calc2_Lim1_Stat])
        end
        
        -- CALCulate2:LIMit[1]:FAIL?
        gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT1"]["FAIL"]
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gResponseValues[gStateVariables.Calc2_Lim1_Result])
        end
        
        ----------------------- LIMit[2] -----------------------------------
        -- CALCulate2:LIMit2:UPPer[:DATA] <n>
        gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT2"]["UPPER"]["DATA"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mGeneralPositive
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lData = lParameters[1]
            if lData >= -9.999999E+20 and lData <= 9.999999E+20 then
                gStateVariables.Calc2_Lim_Upp[2] = lData
                lMemScratch.Calc2_Lim2_Upp = lData
            else
                gErrorQueue.Add(-222)
            end
        end
        -- CALCulate2:LIMit2:UPPer[:DATA]?
        gCurrentRoot.mQuery.mParameters = gParserTable.mGeneralPositiveQuery
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(lParameters[1] or gStateVariables.Calc2_Lim_Upp[2])
        end
        
        if gDigioSupport then
            -- CALCulate2:LIMit2:UPPer:SOURce2 <NRf> | <NDN>
            gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT2"]["UPPER"]["SOURCE2"]
            gCurrentRoot.mCommand.mParameters = gParserTable.mNDN
            gCurrentRoot.mCommand.mExecute = function (lParameters)
                local lValue = lParameters[1]
                if lValue >= 0 and lValue <= gStateVariables.Sour2_Bsize_MaxValue then
                    gStateVariables.Calc2_Lim_Upp_Sour2[2] = lValue
                    lMemScratch.Calc2_Lim2_Upp_Sour2 = lValue
                else
                    gErrorQueue.Add(-222)
                end
            end
            -- CALCulate2:LIMit2:UPPer:SOURce2?
            gCurrentRoot.mQuery.mExecute = function ()
                PrintSource2(gStateVariables.Calc2_Lim_Upp_Sour2[2])
            end
        end
        -- CALCulate2:LIMit2:LOWer[:DATA] <n>
        gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT2"]["LOWER"]["DATA"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mGeneralNegative
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lData = lParameters[1]
            if lData >= -9.999999E+20 and lData <= 9.999999E+20 then
                gStateVariables.Calc2_Lim_Low[2] = lData
                lMemScratch.Calc2_Lim2_Low = lData
            else
                gErrorQueue.Add(-222)
            end
        end
        -- CALCulate2:LIMit2:LOWer[:DATA]?
        gCurrentRoot.mQuery.mParameters = gParserTable.mGeneralNegativeQuery
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(lParameters[1] or gStateVariables.Calc2_Lim_Low[2])
        end
        
        if gDigioSupport then
            -- CALCulate2:LIMit2:LOWer:SOURce2 <NRf> | <NDN>
            gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT2"]["LOWER"]["SOURCE2"]
            gCurrentRoot.mCommand.mParameters = gParserTable.mNDN
            gCurrentRoot.mCommand.mExecute = function (lParameters)
                local lValue = lParameters[1]
                if lValue >= 0 and lValue <= gStateVariables.Sour2_Bsize_MaxValue then
                    gStateVariables.Calc2_Lim_Low_Sour2[2] = lValue
                    lMemScratch.Calc2_Lim2_Low_Sour2 = lValue
                    gStateVariables.Calc2_Lim_Pass_Sour2[2] = lValue
                    lMemScratch.Calc2_Lim2_Pass_Sour2 = lValue
                else
                    gErrorQueue.Add(-222)
                end
            end
            -- CALCulate2:LIMit2:LOWer:SOURce2?
            gCurrentRoot.mQuery.mExecute = function ()
                PrintSource2(gStateVariables.Calc2_Lim_Low_Sour2[2])
        
            end
        
            -- CALCulate2:LIMit2:PASS:SOURce2 <NRf> | <NDN>
            gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT2"]["PASS"]["SOURCE2"]
            gCurrentRoot.mCommand.mParameters = gParserTable.mNDN
            gCurrentRoot.mCommand.mExecute = function (lParameters)
                local lValue = lParameters[1]
                if lValue >= 0 and lValue <= gStateVariables.Sour2_Bsize_MaxValue then
                    gStateVariables.Calc2_Lim_Pass_Sour2[2] = lValue
                    lMemScratch.Calc2_Lim2_Pass_Sour2 = lValue
                    gStateVariables.Calc2_Lim_Low_Sour2[2] = lValue
                    lMemScratch.Calc2_Lim2_Low_Sour2 = lValue
                else
                    gErrorQueue.Add(-222)
                end
            end
            -- CALCulate2:LIMit2:PASS:SOURce2?
            gCurrentRoot.mQuery.mExecute = function ()
                PrintSource2(gStateVariables.Calc2_Lim_Pass_Sour2[2])
            end
        end
        -- CALCulate2:LIMit2:STATe <b>
        gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT2"]["STATE"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mBoolean
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            gStateVariables.Calc2_Lim_Stat[2] = lParameters[1]
            lMemScratch.Calc2_Lim2_Stat = lParameters[1]
        end
        -- CALCulate2:LIMit2:STATe?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gResponseValues[gStateVariables.Calc2_Lim_Stat[2]])
        end
        
        -- CALCulate2:LIMit2:FAIL?
        gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT2"]["FAIL"]
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gResponseValues[gStateVariables.Calc2_Lim_Result[2]])
        end
        
        ----------------------- LIMit[3] -----------------------------------
        -- CALCulate2:LIMit3:UPPer[:DATA] <n>
        gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT3"]["UPPER"]["DATA"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mGeneralPositive
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lData = lParameters[1]
            if lData >= -9.999999E+20 and lData <= 9.999999E+20 then
                gStateVariables.Calc2_Lim_Upp[3] = lData
                lMemScratch.Calc2_Lim3_Upp = lData
            else
                gErrorQueue.Add(-222)
            end
        end
        -- CALCulate2:LIMit3:UPPer[:DATA]?
        gCurrentRoot.mQuery.mParameters = gParserTable.mGeneralPositiveQuery
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(lParameters[1] or gStateVariables.Calc2_Lim_Upp[3])
        end
        
        if gDigioSupport then
            -- CALCulate2:LIMit[3]:UPPer:SOURce2 <NRf> | <NDN>
            gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT3"]["UPPER"]["SOURCE2"]
            gCurrentRoot.mCommand.mParameters = gParserTable.mNDN
            gCurrentRoot.mCommand.mExecute = function (lParameters)
                local lValue = lParameters[1]
                if lValue >= 0 and lValue <= gStateVariables.Sour2_Bsize_MaxValue then
                    gStateVariables.Calc2_Lim_Upp_Sour2[3] = lValue
                    lMemScratch.Calc2_Lim3_Upp_Sour2 = lValue
                else
                    gErrorQueue.Add(-222)
                end
            end
            -- CALCulate2:LIMit[3]:UPPer:SOURce2?
            gCurrentRoot.mQuery.mExecute = function ()
                PrintSource2(gStateVariables.Calc2_Lim_Upp_Sour2[3])
            end
        end
        -- CALCulate2:LIMit3:LOWer[:DATA] <n>
        gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT3"]["LOWER"]["DATA"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mGeneralNegative
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lData = lParameters[1]
            if lData >= -9.999999E+20 and lData <= 9.999999E+20 then
                gStateVariables.Calc2_Lim_Low[3] = lData
                lMemScratch.Calc2_Lim3_Low = lData
            else
                gErrorQueue.Add(-222)
            end
        end
        -- CALCulate2:LIMit3:LOWer[:DATA]?
        gCurrentRoot.mQuery.mParameters = gParserTable.mGeneralNegativeQuery
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(lParameters[1] or gStateVariables.Calc2_Lim_Low[3])
        end
        
        if gDigioSupport then
            -- CALCulate2:LIMit3:LOWer:SOURce2 <NRf> | <NDN>
            gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT3"]["LOWER"]["SOURCE2"]
            gCurrentRoot.mCommand.mParameters = gParserTable.mNDN
            gCurrentRoot.mCommand.mExecute = function (lParameters)
                local lValue = lParameters[1]
                if lValue >= 0 and lValue <= gStateVariables.Sour2_Bsize_MaxValue then
                    gStateVariables.Calc2_Lim_Low_Sour2[3] = lValue
                    lMemScratch.Calc2_Lim3_Low_Sour2 = lValue
                    gStateVariables.Calc2_Lim_Pass_Sour2[3] = lValue
                    lMemScratch.Calc2_Lim3_Pass_Sour2 = lValue
                else
                    gErrorQueue.Add(-222)
                end
            end
            -- CALCulate2:LIMit3:LOWer:SOURce2?
            gCurrentRoot.mQuery.mExecute = function ()
                PrintSource2(gStateVariables.Calc2_Lim_Low_Sour2[3])
            end
        
            -- CALCulate2:LIMit3:PASS:SOURce2 <NRf> | <NDN>
            gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT3"]["PASS"]["SOURCE2"]
            gCurrentRoot.mCommand.mParameters = gParserTable.mNDN
            gCurrentRoot.mCommand.mExecute = function (lParameters)
                local lValue = lParameters[1]
                if lValue >= 0 and lValue <= gStateVariables.Sour2_Bsize_MaxValue then
                    gStateVariables.Calc2_Lim_Pass_Sour2[3] = lValue
                    lMemScratch.Calc2_Lim3_Pass_Sour2 = lValue
                    gStateVariables.Calc2_Lim_Low_Sour2[3] = lValue
                    lMemScratch.Calc2_Lim3_Low_Sour2 = lValue
                else
                    gErrorQueue.Add(-222)
                end
            end
            -- CALCulate2:LIMit3:PASS:SOURce2?
            gCurrentRoot.mQuery.mExecute = function ()
                PrintSource2(gStateVariables.Calc2_Lim_Pass_Sour2[3])
            end
        end
        -- CALCulate2:LIMit3:STATe <b>
        gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT3"]["STATE"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mBoolean
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            gStateVariables.Calc2_Lim_Stat[3] = lParameters[1]
            lMemScratch.Calc2_Lim3_Stat = lParameters[1]
        end
        -- CALCulate2:LIMit3:STATe?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gResponseValues[gStateVariables.Calc2_Lim_Stat[3]])
        end
        
        -- CALCulate2:LIMit3:FAIL?
        gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT3"]["FAIL"]
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gResponseValues[gStateVariables.Calc2_Lim_Result[3]])
        end
        
        ----------------------- LIMit[5] -----------------------------------
        -- CALCulate2:LIMit5:UPPer[:DATA] <n>
        gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT5"]["UPPER"]["DATA"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mGeneralPositive
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lData = lParameters[1]
            if lData >= -9.999999E+20 and lData <= 9.999999E+20 then
                gStateVariables.Calc2_Lim_Upp[5] = lData
                lMemScratch.Calc2_Lim5_Upp = lData
            else
                gErrorQueue.Add(-222)
            end
        end
        -- CALCulate2:LIMit5:UPPer[:DATA]?
        gCurrentRoot.mQuery.mParameters = gParserTable.mGeneralPositiveQuery
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(lParameters[1] or gStateVariables.Calc2_Lim_Upp[5])
        end
        
        if gDigioSupport then
            -- CALCulate2:LIMit[5]:UPPer:SOURce2 <NRf> | <NDN>
            gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT5"]["UPPER"]["SOURCE2"]
            gCurrentRoot.mCommand.mParameters = gParserTable.mNDN
            gCurrentRoot.mCommand.mExecute = function (lParameters)
                local lValue = lParameters[1]
                if lValue >= 0 and lValue <= gStateVariables.Sour2_Bsize_MaxValue then
                    gStateVariables.Calc2_Lim_Upp_Sour2[5] = lValue
                    lMemScratch.Calc2_Lim5_Upp_Sour2 = lValue
                else
                    gErrorQueue.Add(-222)
                end
            end
            -- CALCulate2:LIMit[5]:UPPer:SOURce2?
            gCurrentRoot.mQuery.mExecute = function ()
                PrintSource2(gStateVariables.Calc2_Lim_Upp_Sour2[5])
            end
        end
        -- CALCulate2:LIMit5:LOWer[:DATA] <n>
        gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT5"]["LOWER"]["DATA"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mGeneralNegative
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lData = lParameters[1]
            if lData >= -9.999999E+20 and lData <= 9.999999E+20 then
                gStateVariables.Calc2_Lim_Low[5] = lData
                lMemScratch.Calc2_Lim5_Low = lData
            else
                gErrorQueue.Add(-222)
            end
        end
        -- CALCulate2:LIMit5:LOWer[:DATA]?
        gCurrentRoot.mQuery.mParameters = gParserTable.mGeneralNegativeQuery
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(lParameters[1] or gStateVariables.Calc2_Lim_Low[5])
        end
        
        if gDigioSupport then
            -- CALCulate2:LIMit5:LOWer:SOURce2 <NRf> | <NDN>
            gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT5"]["LOWER"]["SOURCE2"]
            gCurrentRoot.mCommand.mParameters = gParserTable.mNDN
            gCurrentRoot.mCommand.mExecute = function (lParameters)
                local lValue = lParameters[1]
                if lValue >= 0 and lValue <= gStateVariables.Sour2_Bsize_MaxValue then
                    gStateVariables.Calc2_Lim_Low_Sour2[5] = lValue
                    lMemScratch.Calc2_Lim5_Low_Sour2 = lValue
                    gStateVariables.Calc2_Lim_Pass_Sour2[5] = lValue
                    lMemScratch.Calc2_Lim5_Pass_Sour2 = lValue
                else
                    gErrorQueue.Add(-222)
                end
            end
            -- CALCulate2:LIMit5:LOWer:SOURce2?
            gCurrentRoot.mQuery.mExecute = function ()
                PrintSource2(gStateVariables.Calc2_Lim_Low_Sour2[5])
            end
        
            -- CALCulate2:LIMit5:PASS:SOURce2 <NRf> | <NDN>
            gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT5"]["PASS"]["SOURCE2"]
            gCurrentRoot.mCommand.mParameters = gParserTable.mNDN
            gCurrentRoot.mCommand.mExecute = function (lParameters)
                local lValue = lParameters[1]
                if lValue >= 0 and lValue <= gStateVariables.Sour2_Bsize_MaxValue then
                    gStateVariables.Calc2_Lim_Pass_Sour2[5] = lValue
                    lMemScratch.Calc2_Lim5_Pass_Sour2 = lValue
                    gStateVariables.Calc2_Lim_Low_Sour2[5] = lValue
                    lMemScratch.Calc2_Lim5_Low_Sour2 = lValue
                else
                    gErrorQueue.Add(-222)
                end
            end
            -- CALCulate2:LIMit5:PASS:SOURce2?
            gCurrentRoot.mQuery.mExecute = function ()
                PrintSource2(gStateVariables.Calc2_Lim_Pass_Sour2[5])
            end
        end
        -- CALCulate2:LIMit5:STATe <b>
        gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT5"]["STATE"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mBoolean
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            gStateVariables.Calc2_Lim_Stat[5] = lParameters[1]
            lMemScratch.Calc2_Lim5_Stat = lParameters[1]
        end
        -- CALCulate2:LIMit5:STATe?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gResponseValues[gStateVariables.Calc2_Lim_Stat[5]])
        end
        
        -- CALCulate2:LIMit5:FAIL?
        gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT5"]["FAIL"]
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gResponseValues[gStateVariables.Calc2_Lim_Result[5]])
        end
        
        ----------------------- LIMit[6] -----------------------------------
        -- CALCulate2:LIMit6:UPPer[:DATA] <n>
        gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT6"]["UPPER"]["DATA"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mGeneralPositive
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lData = lParameters[1]
            if lData >= -9.999999E+20 and lData <= 9.999999E+20 then
                gStateVariables.Calc2_Lim_Upp[6] = lData
                lMemScratch.Calc2_Lim6_Upp = lData
            else
                gErrorQueue.Add(-222)
            end
        end
        -- CALCulate2:LIMit6:UPPer[:DATA]?
        gCurrentRoot.mQuery.mParameters = gParserTable.mGeneralPositiveQuery
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(lParameters[1] or gStateVariables.Calc2_Lim_Upp[6])
        end
        
        if gDigioSupport then
            -- CALCulate2:LIMit[6]:UPPer:SOURce2 <NRf> | <NDN>
            gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT6"]["UPPER"]["SOURCE2"]
            gCurrentRoot.mCommand.mParameters = gParserTable.mNDN
            gCurrentRoot.mCommand.mExecute = function (lParameters)
                local lValue = lParameters[1]
                if lValue >= 0 and lValue <= gStateVariables.Sour2_Bsize_MaxValue then
                    gStateVariables.Calc2_Lim_Upp_Sour2[6] = lValue
                    lMemScratch.Calc2_Lim6_Upp_Sour2 = lValue
                else
                    gErrorQueue.Add(-222)
                end
            end
            -- CALCulate2:LIMit[6]:UPPer:SOURce2?
            gCurrentRoot.mQuery.mExecute = function ()
                PrintSource2(gStateVariables.Calc2_Lim_Upp_Sour2[6])
            end
        end
        
        -- CALCulate2:LIMit6:LOWer[:DATA] <n>
        gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT6"]["LOWER"]["DATA"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mGeneralNegative
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lData = lParameters[1]
            if lData >= -9.999999E+20 and lData <= 9.999999E+20 then
                gStateVariables.Calc2_Lim_Low[6] = lData
                lMemScratch.Calc2_Lim6_Low = lData
            else
                gErrorQueue.Add(-222)
            end
        end
        -- CALCulate2:LIMit6:LOWer[:DATA]?
        gCurrentRoot.mQuery.mParameters = gParserTable.mGeneralNegativeQuery
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(lParameters[1] or gStateVariables.Calc2_Lim_Low[6])
        end
        
        if gDigioSupport then
            -- CALCulate2:LIMit6:LOWer:SOURce2 <NRf> | <NDN>
            gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT6"]["LOWER"]["SOURCE2"]
            gCurrentRoot.mCommand.mParameters = gParserTable.mNDN
            gCurrentRoot.mCommand.mExecute = function (lParameters)
                local lValue = lParameters[1]
                if lValue >= 0 and lValue <= gStateVariables.Sour2_Bsize_MaxValue then
                    gStateVariables.Calc2_Lim_Low_Sour2[6] = lValue
                    lMemScratch.Calc2_Lim6_Low_Sour2 = lValue
                    gStateVariables.Calc2_Lim_Pass_Sour2[6] = lValue
                    lMemScratch.Calc2_Lim6_Pass_Sour2 = lValue
                else
                    gErrorQueue.Add(-222)
                end
            end
            -- CALCulate2:LIMit6:LOWer:SOURce2?
            gCurrentRoot.mQuery.mExecute = function ()
                PrintSource2(gStateVariables.Calc2_Lim_Low_Sour2[6])
            end
        
            -- CALCulate2:LIMit6:PASS:SOURce2 <NRf> | <NDN>
            gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT6"]["PASS"]["SOURCE2"]
            gCurrentRoot.mCommand.mParameters = gParserTable.mNDN
            gCurrentRoot.mCommand.mExecute = function (lParameters)
                local lValue = lParameters[1]
                if lValue >= 0 and lValue <= gStateVariables.Sour2_Bsize_MaxValue then
                    gStateVariables.Calc2_Lim_Pass_Sour2[6] = lValue
                    lMemScratch.Calc2_Lim6_Pass_Sour2 = lValue
                    gStateVariables.Calc2_Lim_Low_Sour2[6] = lValue
                    lMemScratch.Calc2_Lim6_Low_Sour2 = lValue
                else
                    gErrorQueue.Add(-222)
                end
            end
            -- CALCulate2:LIMit6:PASS:SOURce2?
            gCurrentRoot.mQuery.mExecute = function ()
                PrintSource2(gStateVariables.Calc2_Lim_Pass_Sour2[6])
            end
        end
        -- CALCulate2:LIMit6:STATe <b>
        gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT6"]["STATE"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mBoolean
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            gStateVariables.Calc2_Lim_Stat[6] = lParameters[1]
            lMemScratch.Calc2_Lim6_Stat = lParameters[1]
        end
        -- CALCulate2:LIMit6:STATe?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gResponseValues[gStateVariables.Calc2_Lim_Stat[6]])
        end
        
        -- CALCulate2:LIMit6:FAIL?
        gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT6"]["FAIL"]
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gResponseValues[gStateVariables.Calc2_Lim_Result[6]])
        end
        
        ----------------------- LIMit[7] -----------------------------------
        -- CALCulate2:LIMit7:UPPer[:DATA] <n>
        gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT7"]["UPPER"]["DATA"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mGeneralPositive
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lData = lParameters[1]
            if lData >= -9.999999E+20 and lData <= 9.999999E+20 then
                gStateVariables.Calc2_Lim_Upp[7] = lData
                lMemScratch.Calc2_Lim7_Upp = lData
            else
                gErrorQueue.Add(-222)
            end
        end
        -- CALCulate2:LIMit7:UPPer[:DATA]?
        gCurrentRoot.mQuery.mParameters = gParserTable.mGeneralPositiveQuery
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(lParameters[1] or gStateVariables.Calc2_Lim_Upp[7])
        end
        
        if gDigioSupport then
            -- CALCulate2:LIMit[7]:UPPer:SOURce2 <NRf> | <NDN>
            gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT7"]["UPPER"]["SOURCE2"]
            gCurrentRoot.mCommand.mParameters = gParserTable.mNDN
            gCurrentRoot.mCommand.mExecute = function (lParameters)
                local lValue = lParameters[1]
                if lValue >= 0 and lValue <= gStateVariables.Sour2_Bsize_MaxValue then
                    gStateVariables.Calc2_Lim_Upp_Sour2[7] = lValue
                    lMemScratch.Calc2_Lim7_Upp_Sour2 = lValue
                else
                    gErrorQueue.Add(-222)
                end
            end
            -- CALCulate2:LIMit[7]:UPPer:SOURce2?
            gCurrentRoot.mQuery.mExecute = function ()
                PrintSource2(gStateVariables.Calc2_Lim_Upp_Sour2[7])
            end
        end
        -- CALCulate2:LIMit7:LOWer[:DATA] <n>
        gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT7"]["LOWER"]["DATA"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mGeneralNegative
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lData = lParameters[1]
            if lData >= -9.999999E+20 and lData <= 9.999999E+20 then
                gStateVariables.Calc2_Lim_Low[7] = lData
                lMemScratch.Calc2_Lim7_Low = lData
            else
                gErrorQueue.Add(-222)
            end
        end
        -- CALCulate2:LIMit7:LOWer[:DATA]?
        gCurrentRoot.mQuery.mParameters = gParserTable.mGeneralNegativeQuery
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(lParameters[1] or gStateVariables.Calc2_Lim_Low[7])
        end
        
        if gDigioSupport then
            -- CALCulate2:LIMit7:LOWer:SOURce2 <NRf> | <NDN>
            gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT7"]["LOWER"]["SOURCE2"]
            gCurrentRoot.mCommand.mParameters = gParserTable.mNDN
            gCurrentRoot.mCommand.mExecute = function (lParameters)
                local lValue = lParameters[1]
                if lValue >= 0 and lValue <= gStateVariables.Sour2_Bsize_MaxValue then
                    gStateVariables.Calc2_Lim_Low_Sour2[7] = lValue
                    lMemScratch.Calc2_Lim7_Low_Sour2 = lValue
                    gStateVariables.Calc2_Lim_Pass_Sour2[7] = lValue
                    lMemScratch.Calc2_Lim7_Pass_Sour2 = lValue
                else
                    gErrorQueue.Add(-222)
                end
            end
            -- CALCulate2:LIMit7:LOWer:SOURce2?
            gCurrentRoot.mQuery.mExecute = function ()
                PrintSource2(gStateVariables.Calc2_Lim_Low_Sour2[7])
            end
        
            -- CALCulate2:LIMit7:PASS:SOURce2 <NRf> | <NDN>
            gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT7"]["PASS"]["SOURCE2"]
            gCurrentRoot.mCommand.mParameters = gParserTable.mNDN
            gCurrentRoot.mCommand.mExecute = function (lParameters)
                local lValue = lParameters[1]
                if lValue >= 0 and lValue <= gStateVariables.Sour2_Bsize_MaxValue then
                    gStateVariables.Calc2_Lim_Pass_Sour2[7] = lValue
                    lMemScratch.Calc2_Lim7_Pass_Sour2 = lValue
                    gStateVariables.Calc2_Lim_Low_Sour2[7] = lValue
                    lMemScratch.Calc2_Lim7_Low_Sour2 = lValue
                else
                    gErrorQueue.Add(-222)
                end
            end
            -- CALCulate2:LIMit7:PASS:SOURce2?
            gCurrentRoot.mQuery.mExecute = function ()
                PrintSource2(gStateVariables.Calc2_Lim_Pass_Sour2[7])
            end
        end
        -- CALCulate2:LIMit7:STATe <b>
        gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT7"]["STATE"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mBoolean
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            gStateVariables.Calc2_Lim_Stat[7] = lParameters[1]
            lMemScratch.Calc2_Lim7_Stat = lParameters[1]
        end
        -- CALCulate2:LIMit7:STATe?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gResponseValues[gStateVariables.Calc2_Lim_Stat[7]])
        end
        
        -- CALCulate2:LIMit7:FAIL?
        gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT7"]["FAIL"]
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gResponseValues[gStateVariables.Calc2_Lim_Result[7]])
        end
        
        ----------------------- LIMit[8] -----------------------------------
        -- CALCulate2:LIMit8:UPPer[:DATA] <n>
        gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT8"]["UPPER"]["DATA"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mGeneralPositive
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lData = lParameters[1]
            if lData >= -9.999999E+20 and lData <= 9.999999E+20 then
                gStateVariables.Calc2_Lim_Upp[8] = lData
                lMemScratch.Calc2_Lim8_Upp = lData
            else
                gErrorQueue.Add(-222)
            end
        end
        -- CALCulate2:LIMit8:UPPer[:DATA]?
        gCurrentRoot.mQuery.mParameters = gParserTable.mGeneralPositiveQuery
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(lParameters[1] or gStateVariables.Calc2_Lim_Upp[8])
        end
        
        if gDigioSupport then
            -- CALCulate2:LIMit[8]:UPPer:SOURce2 <NRf> | <NDN>
            gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT8"]["UPPER"]["SOURCE2"]
            gCurrentRoot.mCommand.mParameters = gParserTable.mNDN
            gCurrentRoot.mCommand.mExecute = function (lParameters)
                local lValue = lParameters[1]
                if lValue >= 0 and lValue <= gStateVariables.Sour2_Bsize_MaxValue then
                    gStateVariables.Calc2_Lim_Upp_Sour2[8] = lValue
                    lMemScratch.Calc2_Lim8_Upp_Sour2 = lValue
                else
                    gErrorQueue.Add(-222)
                end
            end
            -- CALCulate2:LIMit[8]:UPPer:SOURce2?
            gCurrentRoot.mQuery.mExecute = function ()
                PrintSource2(gStateVariables.Calc2_Lim_Upp_Sour2[8])
            end
        end
        -- CALCulate2:LIMit8:LOWer[:DATA] <n>
        gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT8"]["LOWER"]["DATA"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mGeneralNegative
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lData = lParameters[1]
            if lData >= -9.999999E+20 and lData <= 9.999999E+20 then
                gStateVariables.Calc2_Lim_Low[8] = lData
                lMemScratch.Calc2_Lim8_Low = lData
            else
                gErrorQueue.Add(-222)
            end
        end
        -- CALCulate2:LIMit8:LOWer[:DATA]?
        gCurrentRoot.mQuery.mParameters = gParserTable.mGeneralNegativeQuery
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(lParameters[1] or gStateVariables.Calc2_Lim_Low[8])
        end
        
        if gDigioSupport then
            -- CALCulate2:LIMit8:LOWer:SOURce2 <NRf> | <NDN>
            gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT8"]["LOWER"]["SOURCE2"]
            gCurrentRoot.mCommand.mParameters = gParserTable.mNDN
            gCurrentRoot.mCommand.mExecute = function (lParameters)
                local lValue = lParameters[1]
                if lValue >= 0 and lValue <= gStateVariables.Sour2_Bsize_MaxValue then
                    gStateVariables.Calc2_Lim_Low_Sour2[8] = lValue
                    lMemScratch.Calc2_Lim8_Low_Sour2 = lValue
                    gStateVariables.Calc2_Lim_Pass_Sour2[8] = lValue
                    lMemScratch.Calc2_Lim8_Pass_Sour2 = lValue
                else
                    gErrorQueue.Add(-222)
                end
            end
            -- CALCulate2:LIMit8:LOWer:SOURce2?
            gCurrentRoot.mQuery.mExecute = function ()
                PrintSource2(gStateVariables.Calc2_Lim_Low_Sour2[8])
            end
        
            -- CALCulate2:LIMit8:PASS:SOURce2 <NRf> | <NDN>
            gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT8"]["PASS"]["SOURCE2"]
            gCurrentRoot.mCommand.mParameters = gParserTable.mNDN
            gCurrentRoot.mCommand.mExecute = function (lParameters)
                local lValue = lParameters[1]
                if lValue >= 0 and lValue <= gStateVariables.Sour2_Bsize_MaxValue then
                    gStateVariables.Calc2_Lim_Low_Sour2[8] = lValue
                    lMemScratch.Calc2_Lim8_Low_Sour2 = lValue
                    gStateVariables.Calc2_Lim_Pass_Sour2[8] = lValue
                    lMemScratch.Calc2_Lim8_Pass_Sour2 = lValue
                else
                    gErrorQueue.Add(-222)
                end
            end
            -- CALCulate2:LIMit8:PASS:SOURce2?
            gCurrentRoot.mQuery.mExecute = function ()
                PrintSource2(gStateVariables.Calc2_Lim_Pass_Sour2[8])
            end
        end
        -- CALCulate2:LIMit8:STATe <b>
        gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT8"]["STATE"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mBoolean
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            gStateVariables.Calc2_Lim_Stat[8] = lParameters[1]
            lMemScratch.Calc2_Lim8_Stat = lParameters[1]
        end
        -- CALCulate2:LIMit8:STATe?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gResponseValues[gStateVariables.Calc2_Lim_Stat[8]])
        end
        
        -- CALCulate2:LIMit8:FAIL?
        gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT8"]["FAIL"]
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gResponseValues[gStateVariables.Calc2_Lim_Result[8]])
        end
        
        ----------------------- LIMit[9] -----------------------------------
        -- CALCulate2:LIMit9:UPPer[:DATA] <n>
        gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT9"]["UPPER"]["DATA"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mGeneralPositive
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lData = lParameters[1]
            if lData >= -9.999999E+20 and lData <= 9.999999E+20 then
                gStateVariables.Calc2_Lim_Upp[9] = lData
                lMemScratch.Calc2_Lim9_Upp = lData
            else
                gErrorQueue.Add(-222)
            end
        end
        -- CALCulate2:LIMit9:UPPer[:DATA]?
        gCurrentRoot.mQuery.mParameters = gParserTable.mGeneralPositiveQuery
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(lParameters[1] or gStateVariables.Calc2_Lim_Upp[9])
        end
        
        if gDigioSupport then
            -- CALCulate2:LIMit[9]:UPPer:SOURce2 <NRf> | <NDN>
            gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT9"]["UPPER"]["SOURCE2"]
            gCurrentRoot.mCommand.mParameters = gParserTable.mNDN
            gCurrentRoot.mCommand.mExecute = function (lParameters)
                local lValue = lParameters[1]
                if lValue >= 0 and lValue <= gStateVariables.Sour2_Bsize_MaxValue then
                    gStateVariables.Calc2_Lim_Upp_Sour2[9] = lValue
                    lMemScratch.Calc2_Lim9_Upp_Sour2 = lValue
                else
                    gErrorQueue.Add(-222)
                end
            end
            -- CALCulate2:LIMit[9]:UPPer:SOURce2?
            gCurrentRoot.mQuery.mExecute = function ()
                PrintSource2(gStateVariables.Calc2_Lim_Upp_Sour2[9])
            end
        end
        -- CALCulate2:LIMit9:LOWer[:DATA] <n>
        gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT9"]["LOWER"]["DATA"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mGeneralNegative
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lData = lParameters[1]
            if lData >= -9.999999E+20 and lData <= 9.999999E+20 then
                gStateVariables.Calc2_Lim_Low[9] = lData
                lMemScratch.Calc2_Lim9_Low = lData
            else
                gErrorQueue.Add(-222)
            end
        end
        -- CALCulate2:LIMit9:LOWer[:DATA]?
        gCurrentRoot.mQuery.mParameters = gParserTable.mGeneralNegativeQuery
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(lParameters[1] or gStateVariables.Calc2_Lim_Low[9])
        end
        
        if gDigioSupport then
            -- CALCulate2:LIMit9:LOWer:SOURce2 <NRf> | <NDN>
            gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT9"]["LOWER"]["SOURCE2"]
            gCurrentRoot.mCommand.mParameters = gParserTable.mNDN
            gCurrentRoot.mCommand.mExecute = function (lParameters)
                local lValue = lParameters[1]
                if lValue >= 0 and lValue <= gStateVariables.Sour2_Bsize_MaxValue then
                    gStateVariables.Calc2_Lim_Low_Sour2[9] = lValue
                    lMemScratch.Calc2_Lim9_Low_Sour2 = lValue
                    gStateVariables.Calc2_Lim_Pass_Sour2[9] = lValue
                    lMemScratch.Calc2_Lim9_Pass_Sour2 = lValue
                else
                    gErrorQueue.Add(-222)
                end
            end
            -- CALCulate2:LIMit9:LOWer:SOURce2?
            gCurrentRoot.mQuery.mExecute = function ()
                PrintSource2(gStateVariables.Calc2_Lim_Low_Sour2[9])
            end
        
            -- CALCulate2:LIMit9:PASS:SOURce2 <NRf> | <NDN>
            gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT9"]["PASS"]["SOURCE2"]
            gCurrentRoot.mCommand.mParameters = gParserTable.mNDN
            gCurrentRoot.mCommand.mExecute = function (lParameters)
                local lValue = lParameters[1]
                if lValue >= 0 and lValue <= gStateVariables.Sour2_Bsize_MaxValue then
                    gStateVariables.Calc2_Lim_Low_Sour2[9] = lValue
                    lMemScratch.Calc2_Lim9_Low_Sour2 = lValue
                    gStateVariables.Calc2_Lim_Pass_Sour2[9] = lValue
                    lMemScratch.Calc2_Lim9_Pass_Sour2 = lValue
                else
                    gErrorQueue.Add(-222)
                end
            end
            -- CALCulate2:LIMit9:PASS:SOURce2?
            gCurrentRoot.mQuery.mExecute = function ()
                PrintSource2(gStateVariables.Calc2_Lim_Pass_Sour2[9])
            end
        end
        -- CALCulate2:LIMit9:STATe <b>
        gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT9"]["STATE"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mBoolean
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            gStateVariables.Calc2_Lim_Stat[9] = lParameters[1]
            lMemScratch.Calc2_Lim9_Stat = lParameters[1]
        end
        -- CALCulate2:LIMit9:STATe?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gResponseValues[gStateVariables.Calc2_Lim_Stat[9]])
        end
        
        -- CALCulate2:LIMit9:FAIL?
        gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT9"]["FAIL"]
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gResponseValues[gStateVariables.Calc2_Lim_Result[9]])
        end
        
        ----------------------- LIMit[10] -----------------------------------
        -- CALCulate2:LIMit10:UPPer[:DATA] <n>
        gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT10"]["UPPER"]["DATA"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mGeneralPositive
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lData = lParameters[1]
            if lData >= -9.999999E+20 and lData <= 9.999999E+20 then
                gStateVariables.Calc2_Lim_Upp[10] = lData
                lMemScratch.Calc2_Lim10_Upp = lData
            else
                gErrorQueue.Add(-222)
            end
        end
        -- CALCulate2:LIMit10:UPPer[:DATA]?
        gCurrentRoot.mQuery.mParameters = gParserTable.mGeneralPositiveQuery
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(lParameters[1] or gStateVariables.Calc2_Lim_Upp[10])
        end
        
        if gDigioSupport then
            -- CALCulate2:LIMit[10]:UPPer:SOURce2 <NRf> | <NDN>
            gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT10"]["UPPER"]["SOURCE2"]
            gCurrentRoot.mCommand.mParameters = gParserTable.mNDN
            gCurrentRoot.mCommand.mExecute = function (lParameters)
                local lValue = lParameters[1]
                if lValue >= 0 and lValue <= gStateVariables.Sour2_Bsize_MaxValue then
                    gStateVariables.Calc2_Lim_Upp_Sour2[10] = lValue
                    lMemScratch.Calc2_Lim10_Upp_Sour2 = lValue
                else
                    gErrorQueue.Add(-222)
                end
            end
            -- CALCulate2:LIMit[10]:UPPer:SOURce2?
            gCurrentRoot.mQuery.mExecute = function ()
                PrintSource2(gStateVariables.Calc2_Lim_Upp_Sour2[10])
            end
        end
        
        -- CALCulate2:LIMit10:LOWer[:DATA] <n>
        gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT10"]["LOWER"]["DATA"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mGeneralNegative
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lData = lParameters[1]
            if lData >= -9.999999E+20 and lData <= 9.999999E+20 then
                gStateVariables.Calc2_Lim_Low[10] = lData
                lMemScratch.Calc2_Lim10_Low = lData
            else
                gErrorQueue.Add(-222)
            end
        end
        -- CALCulate2:LIMit10:LOWer[:DATA]?
        gCurrentRoot.mQuery.mParameters = gParserTable.mGeneralNegativeQuery
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(lParameters[1] or gStateVariables.Calc2_Lim_Low[10])
        end
        
        if gDigioSupport then
            -- CALCulate2:LIMit10:LOWer:SOURce2 <NRf> | <NDN>
            gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT10"]["LOWER"]["SOURCE2"]
            gCurrentRoot.mCommand.mParameters = gParserTable.mNDN
            gCurrentRoot.mCommand.mExecute = function (lParameters)
                local lValue = lParameters[1]
                if lValue >= 0 and lValue <= gStateVariables.Sour2_Bsize_MaxValue then
                    gStateVariables.Calc2_Lim_Low_Sour2[10] = lValue
                    lMemScratch.Calc2_Lim10_Low_Sour2 = lValue
                    gStateVariables.Calc2_Lim_Pass_Sour2[10] = lValue
                    lMemScratch.Calc2_Lim10_Pass_Sour2 = lValue
                else
                    gErrorQueue.Add(-222)
                end
            end
            -- CALCulate2:LIMit10:LOWer:SOURce2?
            gCurrentRoot.mQuery.mExecute = function ()
                PrintSource2(gStateVariables.Calc2_Lim_Low_Sour2[10])
            end
        
            -- CALCulate2:LIMit10:PASS:SOURce2 <NRf> | <NDN>
            gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT10"]["PASS"]["SOURCE2"]
            gCurrentRoot.mCommand.mParameters = gParserTable.mNDN
            gCurrentRoot.mCommand.mExecute = function (lParameters)
                local lValue = lParameters[1]
                if lValue >= 0 and lValue <= gStateVariables.Sour2_Bsize_MaxValue then
                    gStateVariables.Calc2_Lim_Low_Sour2[10] = lValue
                    lMemScratch.Calc2_Lim10_Low_Sour2 = lValue
                    gStateVariables.Calc2_Lim_Pass_Sour2[10] = lValue
                    lMemScratch.Calc2_Lim10_Pass_Sour2 = lValue
                else
                    gErrorQueue.Add(-222)
                end
            end
            -- CALCulate2:LIMit10:PASS:SOURce2?
            gCurrentRoot.mQuery.mExecute = function ()
                PrintSource2(gStateVariables.Calc2_Lim_Pass_Sour2[10])
            end
        end
        -- CALCulate2:LIMit10:STATe <b>
        gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT10"]["STATE"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mBoolean
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            gStateVariables.Calc2_Lim_Stat[10] = lParameters[1]
            lMemScratch.Calc2_Lim10_Stat = lParameters[1]
        end
        -- CALCulate2:LIMit10:STATe?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gResponseValues[gStateVariables.Calc2_Lim_Stat[10]])
        end
        
        -- CALCulate2:LIMit10:FAIL?
        gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT10"]["FAIL"]
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gResponseValues[gStateVariables.Calc2_Lim_Result[10]])
        end
        
        ----------------------- LIMit[11] -----------------------------------
        -- CALCulate2:LIMit11:UPPer[:DATA] <n>
        gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT11"]["UPPER"]["DATA"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mGeneralPositive
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lData = lParameters[1]
            if lData >= -9.999999E+20 and lData <= 9.999999E+20 then
                gStateVariables.Calc2_Lim_Upp[11] = lData
                lMemScratch.Calc2_Lim11_Upp = lData
            else
                gErrorQueue.Add(-222)
            end
        end
        -- CALCulate2:LIMit11:UPPer[:DATA]?
        gCurrentRoot.mQuery.mParameters = gParserTable.mGeneralPositiveQuery
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(lParameters[1] or gStateVariables.Calc2_Lim_Upp[11])
        end
        
        if gDigioSupport then
            -- CALCulate2:LIMit[11]:UPPer:SOURce2 <NRf> | <NDN>
            gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT11"]["UPPER"]["SOURCE2"]
            gCurrentRoot.mCommand.mParameters = gParserTable.mNDN
            gCurrentRoot.mCommand.mExecute = function (lParameters)
                local lValue = lParameters[1]
                if lValue >= 0 and lValue <= gStateVariables.Sour2_Bsize_MaxValue then
                    gStateVariables.Calc2_Lim_Upp_Sour2[11] = lValue
                    lMemScratch.Calc2_Lim11_Upp_Sour2 = lValue
                else
                    gErrorQueue.Add(-222)
                end
            end
            -- CALCulate2:LIMit[11]:UPPer:SOURce2?
            gCurrentRoot.mQuery.mExecute = function ()
                PrintSource2(gStateVariables.Calc2_Lim_Upp_Sour2[11])
            end
        end
        -- CALCulate2:LIMit11:LOWer[:DATA] <n>
        gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT11"]["LOWER"]["DATA"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mGeneralNegative
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lData = lParameters[1]
            if lData >= -9.999999E+20 and lData <= 9.999999E+20 then
                gStateVariables.Calc2_Lim_Low[11] = lData
                lMemScratch.Calc2_Lim11_Low = lData
            else
                gErrorQueue.Add(-222)
            end
        end
        -- CALCulate2:LIMit11:LOWer[:DATA]?
        gCurrentRoot.mQuery.mParameters = gParserTable.mGeneralNegativeQuery
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(lParameters[1] or gStateVariables.Calc2_Lim_Low[11])
        end
        
        if gDigioSupport then
            -- CALCulate2:LIMit11:LOWer:SOURce2 <NRf> | <NDN>
            gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT11"]["LOWER"]["SOURCE2"]
            gCurrentRoot.mCommand.mParameters = gParserTable.mNDN
            gCurrentRoot.mCommand.mExecute = function (lParameters)
                local lValue = lParameters[1]
                if lValue >= 0 and lValue <= gStateVariables.Sour2_Bsize_MaxValue then
                    gStateVariables.Calc2_Lim_Low_Sour2[11] = lValue
                    lMemScratch.Calc2_Lim11_Low_Sour2 = lValue
                    gStateVariables.Calc2_Lim_Pass_Sour2[11] = lValue
                    lMemScratch.Calc2_Lim11_Pass_Sour2 = lValue
                else
                    gErrorQueue.Add(-222)
                end
            end
            -- CALCulate2:LIMit11:LOWer:SOURce2?
            gCurrentRoot.mQuery.mExecute = function ()
                PrintSource2(gStateVariables.Calc2_Lim_Low_Sour2[11])
            end
        
            -- CALCulate2:LIMit11:PASS:SOURce2 <NRf> | <NDN>
            gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT11"]["PASS"]["SOURCE2"]
            gCurrentRoot.mCommand.mParameters = gParserTable.mNDN
            gCurrentRoot.mCommand.mExecute = function (lParameters)
                local lValue = lParameters[1]
                if lValue >= 0 and lValue <= gStateVariables.Sour2_Bsize_MaxValue then
                    gStateVariables.Calc2_Lim_Low_Sour2[11] = lValue
                    lMemScratch.Calc2_Lim11_Low_Sour2 = lValue
                    gStateVariables.Calc2_Lim_Pass_Sour2[11] = lValue
                    lMemScratch.Calc2_Lim11_Pass_Sour2 = lValue
                else
                    gErrorQueue.Add(-222)
                end
            end
            -- CALCulate2:LIMit11:PASS:SOURce2?
            gCurrentRoot.mQuery.mExecute = function ()
                PrintSource2(gStateVariables.Calc2_Lim_Pass_Sour2[11])
            end
        end
        -- CALCulate2:LIMit11:STATe <b>
        gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT11"]["STATE"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mBoolean
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            gStateVariables.Calc2_Lim_Stat[11] = lParameters[1]
            lMemScratch.Calc2_Lim11_Stat = lParameters[1]
        end
        -- CALCulate2:LIMit11:STATe?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gResponseValues[gStateVariables.Calc2_Lim_Stat[11]])
        end
        
        -- CALCulate2:LIMit11:FAIL?
        gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT11"]["FAIL"]
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gResponseValues[gStateVariables.Calc2_Lim_Result[11]])
        end
        
        ----------------------- LIMit[12] -----------------------------------
        -- CALCulate2:LIMit12:UPPer[:DATA] <n>
        gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT12"]["UPPER"]["DATA"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mGeneralPositive
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lData = lParameters[1]
            if lData >= -9.999999E+20 and lData <= 9.999999E+20 then
                gStateVariables.Calc2_Lim_Upp[12] = lData
                lMemScratch.Calc2_Lim12_Upp = lData
            else
                gErrorQueue.Add(-222)
            end
        end
        -- CALCulate2:LIMit12:UPPer[:DATA]?
        gCurrentRoot.mQuery.mParameters = gParserTable.mGeneralPositiveQuery
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(lParameters[1] or gStateVariables.Calc2_Lim_Upp[12])
        end
        
        if gDigioSupport then
            -- CALCulate2:LIMit[12]:UPPer:SOURce2 <NRf> | <NDN>
            gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT12"]["UPPER"]["SOURCE2"]
            gCurrentRoot.mCommand.mParameters = gParserTable.mNDN
            gCurrentRoot.mCommand.mExecute = function (lParameters)
                local lValue = lParameters[1]
                if lValue >= 0 and lValue <= gStateVariables.Sour2_Bsize_MaxValue then
                    gStateVariables.Calc2_Lim_Upp_Sour2[12] = lValue
                    lMemScratch.Calc2_Lim12_Upp_Sour2 = lValue
                else
                    gErrorQueue.Add(-222)
                end
            end
            -- CALCulate2:LIMit[12]:UPPer:SOURce2?
            gCurrentRoot.mQuery.mExecute = function ()
                PrintSource2(gStateVariables.Calc2_Lim_Upp_Sour2[12])
            end
        end
        -- CALCulate2:LIMit12:LOWer[:DATA] <n>
        gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT12"]["LOWER"]["DATA"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mGeneralNegative
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lData = lParameters[1]
            if lData >= -9.999999E+20 and lData <= 9.999999E+20 then
                gStateVariables.Calc2_Lim_Low[12] = lData
                lMemScratch.Calc2_Lim12_Low = lData
            else
                gErrorQueue.Add(-222)
            end
        end
        -- CALCulate2:LIMit12:LOWer[:DATA]?
        gCurrentRoot.mQuery.mParameters = gParserTable.mGeneralNegativeQuery
        gCurrentRoot.mQuery.mExecute = function (lParameters)
            Print(lParameters[1] or gStateVariables.Calc2_Lim_Low[12])
        end
        
        if gDigioSupport then
            -- CALCulate2:LIMit12:LOWer:SOURce2 <NRf> | <NDN>
            gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT12"]["LOWER"]["SOURCE2"]
            gCurrentRoot.mCommand.mParameters = gParserTable.mNDN
            gCurrentRoot.mCommand.mExecute = function (lParameters)
                local lValue = lParameters[1]
                if lValue >= 0 and lValue <= gStateVariables.Sour2_Bsize_MaxValue then
                    gStateVariables.Calc2_Lim_Low_Sour2[12] = lValue
                    lMemScratch.Calc2_Lim12_Low_Sour2 = lValue
                    gStateVariables.Calc2_Lim_Pass_Sour2[12] = lValue
                    lMemScratch.Calc2_Lim12_Pass_Sour2 = lValue
                else
                    gErrorQueue.Add(-222)
                end
            end
            -- CALCulate2:LIMit12:LOWer:SOURce2?
            gCurrentRoot.mQuery.mExecute = function ()
                PrintSource2(gStateVariables.Calc2_Lim_Low_Sour2[12])
            end
        
            -- CALCulate2:LIMit12:PASS:SOURce2 <NRf> | <NDN>
            gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT12"]["PASS"]["SOURCE2"]
            gCurrentRoot.mCommand.mParameters = gParserTable.mNDN
            gCurrentRoot.mCommand.mExecute = function (lParameters)
                local lValue = lParameters[1]
                if lValue >= 0 and lValue <= gStateVariables.Sour2_Bsize_MaxValue then
                    gStateVariables.Calc2_Lim_Low_Sour2[12] = lValue
                    lMemScratch.Calc2_Lim12_Low_Sour2 = lValue
                    gStateVariables.Calc2_Lim_Pass_Sour2[12] = lValue
                    lMemScratch.Calc2_Lim12_Pass_Sour2 = lValue
                else
                    gErrorQueue.Add(-222)
                end
            end
            -- CALCulate2:LIMit12:PASS:SOURce2?
            gCurrentRoot.mQuery.mExecute = function ()
                PrintSource2(gStateVariables.Calc2_Lim_Pass_Sour2[12])
            end
        end
        
        -- CALCulate2:LIMit12:STATe <b>
        gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT12"]["STATE"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mBoolean
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            gStateVariables.Calc2_Lim_Stat[12] = lParameters[1]
            lMemScratch.Calc2_Lim12_Stat = lParameters[1]
        end
        -- CALCulate2:LIMit12:STATe?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gResponseValues[gStateVariables.Calc2_Lim_Stat[12]])
        end
        
        -- CALCulate2:LIMit12:FAIL?
        gCurrentRoot = gCommandTree["CALCULATE2"]["LIMIT12"]["FAIL"]
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gResponseValues[gStateVariables.Calc2_Lim_Result[12]])
        end
        
        ----------------------- CLIMit -----------------------------------
        
        -- CALCulate2:CLIMits:BCONTrol <name>
        gCurrentRoot = gCommandTree["CALCULATE2"]["CLIMITS"]["BCONTROL"]
        gCurrentRoot.mCommand.mParameters =
        {
            {
                mParse = gParserTable.ParseParameterName,
                mNames =
                {
                    ["IMMEDIATE"]   = "IMM",
                    ["IMM"]         = "IMM",
                    ["END"]         = "END",
                }
            }
        }
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            gStateVariables.Calc2_Clim_Bcon = lParameters[1]
        end
        -- CALCulate2:CLIMits:BCONTrol?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gStateVariables.Calc2_Clim_Bcon)
        end
        
        -- CALCulate2:CLIMits:MODE <name>
        gCurrentRoot = gCommandTree["CALCULATE2"]["CLIMITS"]["MODE"]
        gCurrentRoot.mCommand.mParameters =
        {
            {
                mParse = gParserTable.ParseParameterName,
                mNames =
                {
                    ["GRADING"]     = "GRAD",
                    ["GRAD"]        = "GRAD",
                    ["SORTING"]     = "SORT",
                    ["SORT"]        = "SORT",
                }
            }
        }
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            gStateVariables.Calc2_Clim_Mode = lParameters[1]
        end
        -- CALCulate2:CLIMits:MODE?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gStateVariables.Calc2_Clim_Mode)
        end
        
        -- CALCulate2:CLIMits:CLEar:AUTO <b>
        gCurrentRoot = gCommandTree["CALCULATE2"]["CLIMITS"]["CLEAR"]["AUTO"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mBoolean
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            gStateVariables.Calc2_Clim_Cle_Auto = lParameters[1]
        end
        -- CALCulate2:CLIMits:CLEar:AUTO?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gResponseValues[gStateVariables.Calc2_Clim_Cle_Auto])
        end
        
        -- CALCulate2:CLIMits:CLEar[:IMMediate]
        gCurrentRoot = gCommandTree["CALCULATE2"]["CLIMITS"]["CLEAR"]["IMMEDIATE"]
        gCurrentRoot.mCommand.mExecute = function ()
            UpdateDigOut(gStateVariables.Sour2_Ttl_Lev)
        end
        
        if gDigioSupport then
            -- CALCulate2:CLIMits:PASS:SOURce2 <NRf> | <NDN>
            gCurrentRoot = gCommandTree["CALCULATE2"]["CLIMITS"]["PASS"]["SOURCE2"]
            gCurrentRoot.mCommand.mParameters = gParserTable.mNDN
            gCurrentRoot.mCommand.mExecute = function (lParameters)
                local lValue = lParameters[1]
                if lValue >= 0 and lValue <= gStateVariables.Sour2_Bsize_MaxValue then
                    gStateVariables.Calc2_Clim_Pass_Sour2 = lValue
                    lMemScratch.Calc2_Clim_Pass_Sour2 = lValue
                else
                    gErrorQueue.Add(-222)
                end
            end
            -- CALCulate2:CLIMits:PASS:SOURce2?
            gCurrentRoot.mQuery.mExecute = function ()
                PrintSource2(gStateVariables.Calc2_Clim_Pass_Sour2)
            end
        end
        
        -- CALCulate2:CLIMits:PASS:SMLocation <NRf> | NEXT
        gCurrentRoot = gCommandTree["CALCULATE2"]["CLIMITS"]["PASS"]["SMLOCATION"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mSMLocation
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lLocation = lParameters[1]
            if lLocation == "NEXT" or (lLocation > 0 and lLocation <= 100) then
                gStateVariables.Calc2_Clim_Pass_Sml = lLocation
                lMemScratch.Calc2_Clim_Pass_Sml = lLocation
            else
                gErrorQueue.Add(-222)
            end
        end
        -- CALCulate2:CLIMits:PASS:SMLocation?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(tostring(gStateVariables.Calc2_Clim_Pass_Sml))
        end
        
        if gDigioSupport then
            -- CALCulate2:CLIMits:FAIL:SOURce2 <NRf> | <NDN>
            gCurrentRoot = gCommandTree["CALCULATE2"]["CLIMITS"]["FAIL"]["SOURCE2"]
            gCurrentRoot.mCommand.mParameters = gParserTable.mNDN
            gCurrentRoot.mCommand.mExecute = function (lParameters)
                local lValue = lParameters[1]
                if lValue >= 0 and lValue <= gStateVariables.Sour2_Bsize_MaxValue then
                    gStateVariables.Calc2_Clim_Fail_Sour2 = lValue
                    lMemScratch.Calc2_Clim_Fail_Sour2 = lValue
                else
                    gErrorQueue.Add(-222)
                end
            end
            -- CALCulate2:CLIMits:FAIL:SOURce2?
            gCurrentRoot.mQuery.mExecute = function ()
                PrintSource2(gStateVariables.Calc2_Clim_Fail_Sour2)
            end
        end
        
        -- CALCulate2:CLIMits:FAIL:SMLocation <NRf> | NEXT
        gCurrentRoot = gCommandTree["CALCULATE2"]["CLIMITS"]["FAIL"]["SMLOCATION"]
        gCurrentRoot.mCommand.mParameters = gParserTable.mSMLocation
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            local lLocation = lParameters[1]
            if lLocation == "NEXT" or (lLocation > 0 and lLocation <= 100) then
                gStateVariables.Calc2_Clim_Fail_Sml = lLocation
                lMemScratch.Calc2_Clim_Fail_Sml = lLocation
            else
                gErrorQueue.Add(-222)
            end
        end
        -- CALCulate2:CLIMits:FAIL:SMLocation?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(tostring(gStateVariables.Calc2_Clim_Fail_Sml))
        end
        
        -----------------------------------------------------------------------
        -- CALCulate3 Subsystem
        -----------------------------------------------------------------------
        
        -- CALCulate3:FORMat <name>
        gCurrentRoot = gCommandTree["CALCULATE3"]["FORMAT"]
        gCurrentRoot.mCommand.mParameters =
        {
            {
                mParse = gParserTable.ParseParameterName,
                mNames =
                {
                    ["MEAN"]        = "MEAN",
                    ["SDEVIATION"]  = "SDEV",
                    ["SDEV"]        = "SDEV",
                    ["MAXIMUM"]     = "MAX",
                    ["MAX"]         = "MAX",
                    ["MINIMUM"]     = "MIN",
                    ["MIN"]         = "MIN",
                    ["PKPK"]        = "PKPK",
                }
            }
        }
        gCurrentRoot.mCommand.mExecute = function (lParameters)
            gStateVariables.Calc3_Form = lParameters[1]
        end
        -- CALCulate3:FOTMat?
        gCurrentRoot.mQuery.mExecute = function ()
            Print(gStateVariables.Calc3_Form)
        end
        
        local Mean = function (lCount, lValues)
            local lSum = 0
            local lN = 0
            for lIndex = 1, lCount do
                if lValues[lIndex] ~= gNan then
                    lSum = lSum + lValues[lIndex]
                    lN = lN + 1
                end
            end
            return lN > 0 and (lSum / lN) or gNan
        end
        local StdDev = function (lCount, lValues)
            local lSum = 0
            local lN = 0
            local lMean = Mean(lCount, lValues)
        
            if lMean == gNan then
                return gNan
            end
            for lIndex = 1, lCount do
                if lValues[lIndex] ~= gNan then
                    lSum = lSum + (lMean - lValues[lIndex])^2
                    if (lMean - lValues[lIndex]) ~= 0 then
                        lN = lN + 1
                    end
                end
            end
            return math.sqrt(lSum / lN)
        end
        local Min = function (lCount, lValues)
            local lMin
        
            for lIndex = 1, lCount do
                if lValues[lIndex] ~= gNan then
                    if lMin then
                        if lValues[lIndex] < lMin then
                            lMin = lValues[lIndex]
                        end
                    else
                        lMin = lValues[lIndex]
                    end
                end
            end
            return lMin or gNan
        end
        local Max = function (lCount, lValues)
            local lMax
        
            for lIndex = 1, lCount do
                if lValues[lIndex] ~= gNan then
                    if lMax then
                        if lValues[lIndex] > lMax then
                            lMax = lValues[lIndex]
                        end
                    else
                        lMax = lValues[lIndex]
                    end
                end
            end
            return lMax or gNan
        end
        
        -- CALCulate3:DATA?
        gCurrentRoot = gCommandTree["CALCULATE3"]["DATA"]
        gCurrentRoot.mQuery.mExecute = function ()
            if gTraceBuffer.mCount > 0 then
                if gStateVariables.Trac_Feed == "SENS1" then
                    local lVoltage
                    local lCurrent
                    local lResistance
        
                    if gStateVariables.Calc3_Form == "MEAN" then
                        lVoltage = Mean(gTraceBuffer.mCount, gTraceBuffer.mVoltage)
                        lCurrent = Mean(gTraceBuffer.mCount, gTraceBuffer.mCurrent)
                        lResistance = Mean(gTraceBuffer.mCount, gTraceBuffer.mResistance)
                    elseif gStateVariables.Calc3_Form == "SDEV" then
                        lVoltage = StdDev(gTraceBuffer.mCount, gTraceBuffer.mVoltage)
                        lCurrent = StdDev(gTraceBuffer.mCount, gTraceBuffer.mCurrent)
                        lResistance = StdDev(gTraceBuffer.mCount, gTraceBuffer.mResistance)
                    elseif gStateVariables.Calc3_Form == "MAX" then
                        lVoltage = Max(gTraceBuffer.mCount, gTraceBuffer.mVoltage)
                        lCurrent = Max(gTraceBuffer.mCount, gTraceBuffer.mCurrent)
                        lResistance = Max(gTraceBuffer.mCount, gTraceBuffer.mResistance)
                    elseif gStateVariables.Calc3_Form == "MIN" then
                        lVoltage = Min(gTraceBuffer.mCount, gTraceBuffer.mVoltage)
                        lCurrent = Min(gTraceBuffer.mCount, gTraceBuffer.mCurrent)
                        lResistance = Min(gTraceBuffer.mCount, gTraceBuffer.mResistance)
                    elseif gStateVariables.Calc3_Form == "PKPK" then
                        lVoltage = Max(gTraceBuffer.mCount, gTraceBuffer.mVoltage)
                        lCurrent = Max(gTraceBuffer.mCount, gTraceBuffer.mCurrent)
                        lResistance = Max(gTraceBuffer.mCount, gTraceBuffer.mResistance)
                        if lVoltage ~= gNan then
                            lVoltage = lVoltage - Min(gTraceBuffer.mCount, gTraceBuffer.mVoltage)
                        end
                        if lCurrent ~= gNan then
                            lCurrent = lCurrent - Min(gTraceBuffer.mCount, gTraceBuffer.mCurrent)
                        end
                        if lResistance ~= gNan then
                            lResistance = lResistance - Min(gTraceBuffer.mCount, gTraceBuffer.mResistance)
                        end
                    end
                    Print(lVoltage)
                    Print(",")
                    Print(lCurrent)
                    Print(",")
                    Print(lResistance)
                elseif gStateVariables.Trac_Feed == "CALC1" or gStateVariables.Trac_Feed == "CALC2" then
                    if gStateVariables.Calc3_Form == "MEAN" then
                        Print(Mean(gTraceBuffer.mCount, gTraceBuffer.mData))
                    elseif gStateVariables.Calc3_Form == "SDEV" then
                        Print(StdDev(gTraceBuffer.mCount, gTraceBuffer.mData))
                    elseif gStateVariables.Calc3_Form == "MAX" then
                        Print(Max(gTraceBuffer.mCount, gTraceBuffer.mData))
                    elseif gStateVariables.Calc3_Form == "MIN" then
                        Print(Min(gTraceBuffer.mCount, gTraceBuffer.mData))
                    elseif gStateVariables.Calc3_Form == "PKPK" then
                        local lValue = Max(gTraceBuffer.mCount, gTraceBuffer.mData)
                        if lValue ~= gNan then
                            lValue = lValue - Min(gTraceBuffer.mCount, gTraceBuffer.mData)
                        end
                        Print(lValue)
                    end
                end
            else
                gErrorQueue.Add(-230)
            end
        end
        
        -----------------------------------------------------------------------
        -- SCPI oriented measurement commands
        -----------------------------------------------------------------------
        -- configure the smu to a specific setup for measurements
        local configureForMeasurements = function ()
            gTrigger.count = 1
            gArm.count = 1
            gAccessors.mSetMeasureAutoZero(smua.AUTOZERO_AUTO)
            gStateVariables.Trig_Del = 0
            gStateVariables.Arm_Sour = "IMM"
            gStateVariables.Trig_Sour = "IMM"
            gStateVariables.Calc1_Stat = false
            gStateVariables.Calc2_Lim1_Stat = false
            gStateVariables.Trac_Cont = "NEV"
            for i = 2, 12 do
                if i ~= 4 then
                    gStateVariables.Calc2_Lim_Stat[i] = false
                end
            end
            gAccessors.mSetSourceOutput(1)
        end
        
        -- READ?
        -- supports current, voltage (custom, linear and log sweeps)
        gCurrentRoot = gCommandTree["READ"]
        gCurrentRoot.mQuery.mExecute = function ()
            --run Sweeps if any
            smua.abort()
            if gArm.count ~= 0 then
                if gAccessors.mGetSourceOutput() == 1 or gStateVariables.Sour_Cle_Auto_State then
                    gPrintEnable = true
                    if gStateVariables.Arm_Sour == "BUS" then
                        gErrorQueue.Add(-215)
                    else
                        Initiate()
                    end
                else
                    gErrorQueue.Add(803)
                end
            else
                gErrorQueue.Add(830)
            end
        end
        
        -- FETCH?
        gCurrentRoot = gCommandTree["FETCH"]
        gCurrentRoot.mQuery.mExecute = function ()
            if gArm.count ~= 0 then
                if gSampleBuffer.mCount > 0 then
                    PrintSampleBuffer(1, gSampleBuffer.mCount)
                else
                    gErrorQueue.Add(-230)
                end
            else
                gErrorQueue.Add(830)
            end
        end
        
        -- CONFigure:VOLTage[:DC]
        gCurrentRoot = gCommandTree["CONFIGURE"]["VOLTAGE"]["DC"]
        gCurrentRoot.mCommand.mExecute = function ()
            gStateVariables.Sens_Func.VOLT = true
            gStateVariables.Sens_Func.CURR = false
            gStateVariables.Sens_Func.RES = false
            gStateVariables.Sens_Func.ANY = true
            gAccessors.mSetMeasureAutoRangev(1)
            configureForMeasurements()
        end
        
        -- CONFigure:CURRent[:DC]
        gCurrentRoot = gCommandTree["CONFIGURE"]["CURRENT"]["DC"]
        gCurrentRoot.mCommand.mExecute = function ()
            gStateVariables.Sens_Func.VOLT = false
            gStateVariables.Sens_Func.CURR = true
            gStateVariables.Sens_Func.RES = false
            gStateVariables.Sens_Func.ANY = true
            gAccessors.mSetMeasureAutoRangei(1)
            configureForMeasurements()
        end
        
        -- CONFigure:RESistance
        gCurrentRoot = gCommandTree["CONFIGURE"]["RESISTANCE"]
        gCurrentRoot.mCommand.mExecute = function ()
            if gAccessors.mGetSourceFunc() == gDCAMPS then
                gStateVariables.Sens_Func.VOLT = false
                gStateVariables.Sens_Func.CURR = true
                gStateVariables.Sens_Func.RES = true
            else -- smua.OUTPUT_DCVOLTS
                gStateVariables.Sens_Func.VOLT = true
                gStateVariables.Sens_Func.CURR = false
                gStateVariables.Sens_Func.RES = true
            end
            gStateVariables.Sens_Func.ANY = true
            gAccessors.mSetMeasureAutoRangei(1)
            gAccessors.mSetMeasureAutoRangev(1)
            configureForMeasurements()
        end
        
        -- MEASure?
        gCurrentRoot = gCommandTree["MEASURE"]
        gCurrentRoot.mQuery.mExecute = function ()
            -- The order is important when no function is specified
            if gAccessors.mGetSourceFunc() == gDCAMPS then
                if gStateVariables.Sens_Func.RES then
                    gCommandTree.CONFIGURE.RESISTANCE.mCommand.mExecute()
                    gCommandTree.READ.mQuery.mExecute()
                elseif gStateVariables.Sens_Func.VOLT then
                    gCommandTree.CONFIGURE.VOLTAGE.mCommand.mExecute()
                    gCommandTree.READ.mQuery.mExecute()
                elseif gStateVariables.Sens_Func.CURR then
                    gCommandTree.CONFIGURE.CURRENT.mCommand.mExecute()
                    gCommandTree.READ.mQuery.mExecute()
                else
                    --gStateVariables.Sens_Func.VOLT then
                    gCommandTree.CONFIGURE.VOLTAGE.mCommand.mExecute()
                    gCommandTree.READ.mQuery.mExecute()
                end
            else -- smua.OUTPUT_DCVOLTS
                if gStateVariables.Sens_Func.RES then
                    gCommandTree.CONFIGURE.RESISTANCE.mCommand.mExecute()
                    gCommandTree.READ.mQuery.mExecute()
                elseif gStateVariables.Sens_Func.CURR then
                    gCommandTree.CONFIGURE.CURRENT.mCommand.mExecute()
                    gCommandTree.READ.mQuery.mExecute()
                elseif gStateVariables.Sens_Func.VOLT then
                    gCommandTree.CONFIGURE.VOLTAGE.mCommand.mExecute()
                    gCommandTree.READ.mQuery.mExecute()
                else
                    --gStateVariables.Sens_Func.CURR then
                    gCommandTree.CONFIGURE.CURRENT.mCommand.mExecute()
                    gCommandTree.READ.mQuery.mExecute()
                end
            end
        end
        
        -- MEASure:VOLTage[:DC]?
        gCurrentRoot = gCommandTree["MEASURE"]["VOLTAGE"]["DC"]
        gCurrentRoot.mQuery.mExecute = function ()
            gCommandTree.CONFIGURE.VOLTAGE.mCommand.mExecute()
            gCommandTree.READ.mQuery.mExecute()
        end
        
        -- MEASure:CURRent[:DC]?
        gCurrentRoot = gCommandTree["MEASURE"]["CURRENT"]["DC"]
        gCurrentRoot.mQuery.mExecute = function ()
            gCommandTree.CONFIGURE.CURRENT.mCommand.mExecute()
            gCommandTree.READ.mQuery.mExecute()
        end
        
        -- MEASure:RESistance?
        gCurrentRoot = gCommandTree["MEASURE"]["RESISTANCE"]
        gCurrentRoot.mQuery.mExecute = function ()
            gCommandTree.CONFIGURE.RESISTANCE.mCommand.mExecute()
            gCommandTree.READ.mQuery.mExecute()
        end
        
        -----------------------------------------------------------------------
        -- END of commands
        -----------------------------------------------------------------------
        gStateVariables.Disp_State = display.SMUA
        gStateVariables.Disp_Wind1_Text_Data = gDisplayVariables.mDisplayText1
        gStateVariables.Disp_Wind2_Text_Data = gDisplayVariables.mDisplayText2
        display.setcursor(1, 1)
        display.settext(gStateVariables.Disp_Wind1_Text_Data)
        display.setcursor(2, 1)
        display.settext(gStateVariables.Disp_Wind2_Text_Data)
        display.screen = gDisplayVariables.mDisplayScreen
        gStateVariables.Sens_Curr_Prot_Rsyn = false
        gStateVariables.Sens_Volt_Prot_Rsyn = false
        ------------------------------------------------------------------------------
        -- ResetDefaults()
        -- Sets the smu to 2400 reset defaults
        ------------------------------------------------------------------------------
        ResetScriptVariables = function()
        
            -- Calculate1 Subsystem
            gStateVariables.Calc1_Stat = false
            gStateVariables.Calc1_Selected = gMathCatalog["POWER"]
            gStateVariables.Calc1_Selected_Index = 1
            gStateVariables.Calc3_Form = "MEAN"
            gStateVariables.Calc2_Feed = "VOLT"
            gStateVariables.Calc2_Null_Offs = 0
            gStateVariables.Calc2_Null_Stat = false
            gStateVariables.Calc2_Lim1_Fail = "IN"
            gStateVariables.Calc2_Lim1_Sour2 = 15
            gStateVariables.Calc2_Lim1_Stat = false
            gStateVariables.Calc2_Lim1_Result = 0
            gStateVariables.Calc2_Lim_Upp[2] = 1
            gStateVariables.Calc2_Lim_Low[2] = -1
            gStateVariables.Calc2_Lim_Upp_Sour2[2] = 15
            gStateVariables.Calc2_Lim_Low_Sour2[2] = 15
            gStateVariables.Calc2_Lim_Pass_Sour2[2] = 15
            gStateVariables.Calc2_Lim_Stat[2] = false
            gStateVariables.Calc2_Lim_Result[2] = 0
            gStateVariables.Calc2_Lim_Upp[3] = 1
            gStateVariables.Calc2_Lim_Low[3] = -1
            gStateVariables.Calc2_Lim_Upp_Sour2[3] = 15
            gStateVariables.Calc2_Lim_Low_Sour2[3] = 15
            gStateVariables.Calc2_Lim_Pass_Sour2[3] = 15
            gStateVariables.Calc2_Lim_Stat[3] = false
            gStateVariables.Calc2_Lim_Result[3] = 0
            --gStateVariables.Calc2_Lim_Upp[4] = 1
            --gStateVariables.Calc2_Lim_Low[4] = -1
            --gStateVariables.Calc2_Lim_Upp_Sour2[4] = 15
            --gStateVariables.Calc2_Lim_Low_Sour2[4] = 15
            --gStateVariables.Calc2_Lim_Stat[4] = 0
            --gStateVariables.Calc2_Lim_Result[4] = 0
            gStateVariables.Calc2_Lim_Upp[5] = 1
            gStateVariables.Calc2_Lim_Low[5] = -1
            gStateVariables.Calc2_Lim_Upp_Sour2[5] = 15
            gStateVariables.Calc2_Lim_Low_Sour2[5] = 15
            gStateVariables.Calc2_Lim_Pass_Sour2[5] = 15
            gStateVariables.Calc2_Lim_Stat[5] = false
            gStateVariables.Calc2_Lim_Result[5] = 0
            gStateVariables.Calc2_Lim_Upp[6] = 1
            gStateVariables.Calc2_Lim_Low[6] = -1
            gStateVariables.Calc2_Lim_Upp_Sour2[6] = 15
            gStateVariables.Calc2_Lim_Low_Sour2[6] = 15
            gStateVariables.Calc2_Lim_Pass_Sour2[6] = 15
            gStateVariables.Calc2_Lim_Stat[6] = false
            gStateVariables.Calc2_Lim_Result[6] = 0
            gStateVariables.Calc2_Lim_Upp[7] = 1
            gStateVariables.Calc2_Lim_Low[7] = -1
            gStateVariables.Calc2_Lim_Upp_Sour2[7] = 15
            gStateVariables.Calc2_Lim_Low_Sour2[7] = 15
            gStateVariables.Calc2_Lim_Pass_Sour2[7] = 15
            gStateVariables.Calc2_Lim_Stat[7] = false
            gStateVariables.Calc2_Lim_Result[7] = 0
            gStateVariables.Calc2_Lim_Upp[8] = 1
            gStateVariables.Calc2_Lim_Low[8] = -1
            gStateVariables.Calc2_Lim_Upp_Sour2[8] = 15
            gStateVariables.Calc2_Lim_Low_Sour2[8] = 15
            gStateVariables.Calc2_Lim_Pass_Sour2[8] = 15
            gStateVariables.Calc2_Lim_Stat[8] = false
            gStateVariables.Calc2_Lim_Result[8] = 0
            gStateVariables.Calc2_Lim_Upp[9] = 1
            gStateVariables.Calc2_Lim_Low[9] = -1
            gStateVariables.Calc2_Lim_Upp_Sour2[9] = 15
            gStateVariables.Calc2_Lim_Low_Sour2[9] = 15
            gStateVariables.Calc2_Lim_Pass_Sour2[9] = 15
            gStateVariables.Calc2_Lim_Stat[9] = false
            gStateVariables.Calc2_Lim_Result[9] = 0
            gStateVariables.Calc2_Lim_Upp[10] = 1
            gStateVariables.Calc2_Lim_Low[10] = -1
            gStateVariables.Calc2_Lim_Upp_Sour2[10] = 15
            gStateVariables.Calc2_Lim_Low_Sour2[10] = 15
            gStateVariables.Calc2_Lim_Pass_Sour2[10] = 15
            gStateVariables.Calc2_Lim_Stat[10] = false
            gStateVariables.Calc2_Lim_Result[10] = 0
            gStateVariables.Calc2_Lim_Upp[11] = 1
            gStateVariables.Calc2_Lim_Low[11] = -1
            gStateVariables.Calc2_Lim_Upp_Sour2[11] = 15
            gStateVariables.Calc2_Lim_Low_Sour2[11] = 15
            gStateVariables.Calc2_Lim_Pass_Sour2[11] = 15
            gStateVariables.Calc2_Lim_Stat[11] = false
            gStateVariables.Calc2_Lim_Result[11] = 0
            gStateVariables.Calc2_Lim_Upp[12] = 1
            gStateVariables.Calc2_Lim_Low[12] = -1
            gStateVariables.Calc2_Lim_Upp_Sour2[12] = 15
            gStateVariables.Calc2_Lim_Low_Sour2[12] = 15
            gStateVariables.Calc2_Lim_Pass_Sour2[12] = 15
            gStateVariables.Calc2_Lim_Stat[12] = false
            gStateVariables.Calc2_Lim_Result[12] = 0
            gStateVariables.Calc2_Clim_Mode = "GRAD"
            gStateVariables.Calc2_Clim_Bcon = "IMM"
            gStateVariables.Calc2_Clim_Cle_Auto = true
            gStateVariables.Calc2_Clim_Pass_Sour2 = 15
            gStateVariables.Calc2_Clim_Pass_Sml = "NEXT"
            gStateVariables.Calc2_Clim_Fail_Sour2 = 15
            gStateVariables.Calc2_Clim_Fail_Sml = "NEXT"
        
            -- Display Subsystem
            gStateVariables.Disp_Enab = true
        
            --Format Subsystem
            lState = gStateVariables.Form_Elem_Sens1
            lState.VOLT = true
            lState.CURR = true
            lState.RES = true
            lState.TIME = true
            lState.STAT = true
            gStateVariables.Form_Data_Type = "ASC"
            gStateVariables.Form_Sreg = "ASC"
            lState = gStateVariables.Form_Elem_Calc
            lState.TIME = false
            lState.STAT = false
            lState.CALC = true
            gStateVariables.Form_Sour2 = "ASC"
        
        -- Output Subsystem
            gStateVariables.Outp_Smod = "NORM"
            gStateVariables.Outp_Interlock = 1
        -- Route Subsystem
            gStateVariables.Route_Term = "REAR"
        
        -- Sense Subsystem
            gStateVariables.Sens_Func_Conc = true
            gStateVariables.Sens_Func.VOLT = false
            gStateVariables.Sens_Func.CURR = true
            gStateVariables.Sens_Func.RES = false
            gStateVariables.Sens_Func.ANY = true
            gStateVariables.Sens_Curr_Prot = 100e-6
            gStateVariables.Sens_Volt_Prot = 20
            gStateVariables.Sens_Res_Mode = "MAN"
            gStateVariables.Sens_Res_Range = 2.1E+05
        
        -- Source Subsystem
            gStateVariables.Sour_Cle_Auto_State = false
            gStateVariables.Sour_Cle_Auto_Mode = "ALW"
            gStateVariables.Sour_Func_Shape = "DC"
            gStateVariables.Sour_Func_Mode = "VOLT"
            gStateVariables.Sour_Curr_Mode = "FIX"
            gStateVariables.Sour_Volt_Mode = "FIX"
            gStateVariables.Sour_Del = 0
            gStateVariables.Sour_Del_Auto = true
            gStateVariables.Sour_Volt_Trig_Ampl = 0
            gStateVariables.Sour_Curr_Trig_Ampl = 0
            gStateVariables.Sour_Swe_Rang = "BEST"
            gStateVariables.Sour_Swe_Spac = "LIN"
            gStateVariables.Sour_Curr_Start = 0
            gStateVariables.Sour_Curr_Stop = 0
            gStateVariables.Sour_Volt_Start = 0
            gStateVariables.Sour_Volt_Stop = 0
            gStateVariables.Sour_Curr_Cent = 0
            gStateVariables.Sour_Volt_Cent = 0
            gStateVariables.Sour_Curr_Span = 0
            gStateVariables.Sour_Volt_Span = 0
            gStateVariables.Sour_Volt_Step = 0
            --lState.VOLTAGE.POINTS = 2500
            gStateVariables.Sour_Curr_Step = 0
            --lState.CURRENT.POINTS = 2500
            gStateVariables.Sour_Swe_Poin = 2500
            gStateVariables.Sour_Swe_Dir = "UP"
            gStateVariables.Sour_Swe_Cab = "NEV"
            gStateVariables.Sour_List_Volt_Start = 1
            gStateVariables.Sour_List_Curr_Start = 1
            gStateVariables.Sour_Curr_Trig_Sfac = 1
            gStateVariables.Sour_Volt_Trig_Sfac = 1
            gStateVariables.Sour_Volt_Trig_Sfac_State = false
            gStateVariables.Sour_Curr_Trig_Sfac_State = false
        
            -- initialize source memory sweep scratch memory
            for k, v in pairs(lsourceMemInit) do
                lMemScratch[k] = v
            end
        
            gStateVariables.Sour_Mem_Poin = 1
            gStateVariables.Sour_Mem_Start = 1
        
            gStateVariables.Sour_Puls_Widt = 0.00015
            gStateVariables.Sour_Puls_Del = 0
        
            gStateVariables.Sour2_Ttl4_Mode = "EOT"
            gStateVariables.Sour2_Ttl4_Bst = false
            gStateVariables.Sour2_Ttl_Lev = 15
            gStateVariables.Sour2_Ttl_Act = 15
            gStateVariables.Sour2_Cle_Auto = false
            gStateVariables.Sour2_Cle_Del = 1e-5
        
        
        -- System Subsystem
            gStateVariables.Syst_Time_Res_Auto = false
        
        -- Trace Subsystem
        
        -- Trigger Subsystem
            gStateVariables.Trig_Del = 0
            gStateVariables.Arm_Sour = "IMM"
            gStateVariables.Trig_Sour = "IMM"
            gStateVariables.Arm_Tim = 0.1
            gStateVariables.Trig_Dir = "ACC"
            gStateVariables.Arm_Dir = "ACC"
            gStateVariables.Arm_Ilin = 1
            gStateVariables.Trig_Ilin = 2
            gStateVariables.Arm_Olin = 3
            gStateVariables.Trig_Olin = 4
            gStateVariables.Trig_Inp = "SOUR"
            gStateVariables.Trig_Outp.SOUR = false
            gStateVariables.Trig_Outp.DEL = false
            gStateVariables.Trig_Outp.SENS = false
            gStateVariables.Arm_Outp.TEX = false
            gStateVariables.Arm_Outp.TENT = false
        end
        
        ResetSmuSettings = function()
            -- override status register
            gRemoteCommStatus.override = 175
            
            -- Display Subsystem
            display.screen = gStateVariables.Disp_State
            display.smua.measure.func = display.MEASURE_DCAMPS
        
            -- Format Subsystem
            format.data = gAscii
            format.byteorder = format.NORMAL
            format.asciiprecision = 7
        
            -- Sense Subsystem
            --gAccessors.mSetMeasureNplc(1) -- set default NPLC to 1
            gAccessors.mSetSourceLimiti(100e-6) -- set default curernt limit
            gAccessors.mSetSourceLimitv(20) -- set default voltage limit
            gMeasure.lowrangei = 1e-6
            gSource.lowrangei = 1e-6
            gMeasure.lowrangev = 20e-3
            gMeasure.filter.count = 10 -- set default filter count to 10
            --gAccessors.mSetMeasureAutoRangei(smuX.AUTORANGE_ON)
            --gAccessors.mSetSourceAutoRangev(smuX.AUTORANGE_ON)
        
            -- Source Subsystem
            gAccessors.mSetSourceDelay(smua.DELAY_AUTO)
            --gAccessors.mSetSourceFunc(gDCVOLTS)
            --gAccessors.mSetSourceRangei(100e-6)
            --gAccessors.mSetSourceRangev(20)
            gAccessors.mSetSourceAutoRangei(1)
            gAccessors.mSetSourceAutoRangev(1)
        
            gTrigger.endsweep.action = smua.SOURCE_HOLD
        
            -- Sour2 Subsystem
            display.trigger.clear()
            trigger.clear()
        
            -- Sense Subsystem
            gTrigger.measure.action = smua.ENABLE
            
            -- Triggering
            gBlender1.orenable = true
            gTrigOutArm.orenable = true
            gTrigOutTrig.orenable = true
            gTrigOutBoth.orenable = true
            gBlender1.stimulus[1] = gTrigger.ARMED_EVENT_ID
            gBlender1.stimulus[2] = gTrigger.PULSE_COMPLETE_EVENT_ID
            gBlender2.stimulus[1] = gBlender1.EVENT_ID
            gTrigDelayTimer.stimulus = gBlender2.EVENT_ID
            gMeasureCompleteTimer.stimulus = gTrigger.MEASURE_COMPLETE_EVENT_ID
            gMeasureCompleteTimer.delay = 1e-6
        
            if gDigioSupport then
            -- set level of DIG output 1-4(2600 DIGIO 7-10) high
                for i = 0, 3 do
                    digio.writebit(gDigitalOut1Line + i, 1)
                end
            -- clear all the latched input triggers
                for N = 1, 4 do
                    gTriggerLines[N].clear()
                end
                for N = 10, 14 do
                    gTriggerLines[N].clear()
                end
        
                -- Clear the trigger output stimulus
                for N = 1, 4 do
                    gTriggerLines[N].stimulus = 0
                end
        
                gStartOfTest.mode = digio.TRIG_FALLING
                -- Setup lines used to emulate the TLink
                for lIndex = 1, 4 do
                    gTriggerLines[lIndex].mode = digio.TRIG_FALLING
                    gTriggerLines[lIndex].pulsewidth = 10e-6
                end
            end
            -- Clear 2600 error queue
            errorqueue.clear()
        end
        
        ResetDefaults = function ()
            ResetScriptVariables()
            ResetSmuSettings()
            --collectgarbage()
        end
        ------------------------------------------------------------------------------
        -- presetDefaults()
        -- Sets the smu to 2400 reset defaults
        ------------------------------------------------------------------------------
        presetDefaults = function ()
            format.byteorder = format.SWAPPED
        end
        ------------------------------------------------------------------------------
        -- Creates user defined buffers for used by the script
        Init.MakeBuffers = function ()
            gSMVoltageBuffer = smua.makebuffer(2500)
            gSMCurrentBuffer = smua.makebuffer(2500)
            gSMCurrentBuffer.appendmode = 1
            gSMVoltageBuffer.appendmode = 1
            gSMCurrentBuffer.collectsourcevalues = 1
            gSMVoltageBuffer.collectsourcevalues = 1
            gSMCurrentBuffer.collecttimestamps = 1
            gSMVoltageBuffer.collecttimestamps = 1
            gSMCurrentBuffer.timestampresolution = 1e-3
            gSMVoltageBuffer.timestampresolution = 1e-3
            gSMCurrentBuffer.fillcount = 0
            gSMCurrentBuffer.fillmode = smua.FILL_WINDOW
            gSMVoltageBuffer.fillcount = 0
            gSMVoltageBuffer.fillmode = smua.FILL_WINDOW
            gVoltageBuffer = smua.makebuffer(2500)
            gCurrentBuffer = smua.makebuffer(2500)
            gVoltageBuffer.appendmode = 0
            gCurrentBuffer.appendmode = 0
            gVoltageBuffer.collectsourcevalues = 1
            gCurrentBuffer.collectsourcevalues = 1
            gVoltageBuffer.collecttimestamps = 1
            gCurrentBuffer.collecttimestamps = 1
            gVoltageBuffer.timestampresolution = 1e-3
            gCurrentBuffer.timestampresolution = 1e-3
            gCurrentBuffer.fillcount = 0
            gCurrentBuffer.fillmode = smua.FILL_WINDOW
            gVoltageBuffer.fillcount = 0
            gVoltageBuffer.fillmode = smua.FILL_WINDOW
        end
        ------------------------------------------------------------------------------
        -- init memory variables
        Init.InitializeMemory = function ()
            local lMemorySlot
            --format.byteorder = format.NORMAL
            gStateVariables.Sour_List_Volt_Values = {0.0}
            gStateVariables.Sour_List_Volt_Max = 0
            gStateVariables.Sour_List_Curr_Values = {0.0}
            gStateVariables.Sour_List_Curr_Max = 0
            gStateVariables.Trac_Poin = 100
            gStateVariables.Trac_Feed = "SENS1"
            gStateVariables.Trac_Cont = "NEV"
            gStateVariables.Trac_Tst_Form = "ABS"
            -- Initialize all the source memory locations to the present setup
            for lIndex = 1, 100 do
                lMemorySlot = gMemLoc[lIndex]
                for lKey, lValue in pairs(lMemScratch) do
                    lMemorySlot[lKey] = lValue
                end
            end
            gStateVariables.Sour2_Bsize = 4
            gStateVariables.Sour2_Bsize_MaxValue = 15
        end
        ------------------------------------------------------------------------------
        --System memory init
        Init.SysMemInit = function ()
            local lMemorySlot
        
            gStateVariables.Trac_Poin = 100
            gStateVariables.Trac_Tst_Form = "ABS"
            gTraceBuffer.mCount = 0
            -- Reset Source lists
            gStateVariables.Sour_List_Volt_Values = {0.0}
            gStateVariables.Sour_List_Volt_Max = 0
            gStateVariables.Sour_List_Curr_Values = {0.0}
            gStateVariables.Sour_List_Curr_Max = 0
            -- Initialize all the source memory locations to the present setup
            for lIndex = 1, 100 do
                lMemorySlot = gMemLoc[lIndex]
                for lKey, lValue in pairs(lMemScratch) do
                    lMemorySlot[lKey] = lValue
                end
            end
            -- Initialize the setups to the current settings
            --[[
            for i = 1, 5 do
                setup.save(i)
            end
            --]]
            -- Delete math expressions here from calc1 subsystem
            for i = 5, 9 do
                if gMathCatalog[i] then
                    gMathCatalog[gMathCatalog[i]] = nil
                    gMathCatalog[i] = nil
                end
            end
            gStateVariables.Calc1_Stat = false
            gStateVariables.Calc1_Selected = gMathCatalog["POWER"]
            gStateVariables.Calc1_Selected.mTempUnits = gStateVariables.Calc1_Selected.mUnits
            gStateVariables.Calc1_Selected_Index = 1
            gStateVariables.Calc1_Undefined_Expression_Exists = false
            gMathCatalog["POWER"].mTempUnits = gMathCatalog["POWER"].mUnits
            gMathCatalog["OFFCOMPOHM"].mTempUnits = gMathCatalog["OFFCOMPOHM"].mUnits
            gMathCatalog["VOLTCOEF"].mTempUnits = gMathCatalog["VOLTCOEF"].mUnits
            gMathCatalog["VARALPHA"].mTempUnits = gMathCatalog["VARALPHA"].mUnits
        
        end
        ------------------------------------------------------------------------------
        -- Final initializations
        ------------------------------------------------------------------------------
        
        -- set Operation Status Register, Bit 11(10 on 2400) Idle state
        operStatus.mCondition = 1024
        operStatus.mEvent = 1024
        
        -- Standard event status Register, Bit 8(7 on 2400) PON
        standardStatus.mEvent = bit.bitand(status.standard.event, 128)
        
        -- Check for corrupted calibration constants
        if bit.bitand(status.questionable.calibration.condition, 2) == 2 then
            -- Questionable Event Register Bit 9(8 on 2400), Calibration summary
            StatusModel.SetCondition(quesStatus, 9)
        end
        
        gCurrentRoot = gCommandTree
        gSystemClockOffset = os.time()
        -- Initialize smu for 2400 defaults
        SetupNonVolatileExpressions()
        ResetScriptVariables()
        Init.InitializeMemory()
        Init.MakeBuffers()
        
        -- Check if the user string exist
        for lName in userstring.catalog() do
            if lName == "AutoRun2400" then
                gAutoRunEnable = true
                break
            end
        end
        
        -- Create entries in the user menu
        display.loadmenu.add("Run2400", "Engine2400()", display.DONT_SAVE)
        display.loadmenu.add("Configure2400", "Configure2400()", display.DONT_SAVE)
        
        -- if autorun2400 enabled then autorun Engine2400 on power up
        if gAutoRunEnable then
            Engine2400()
        end
        endscript
        '''
