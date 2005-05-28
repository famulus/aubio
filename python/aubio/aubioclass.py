from aubiowrapper import *

class fvec:
    def __init__(self,size,chan):
        self.vec = new_fvec(size,chan)
    def __call__(self):
        return self.vec
    def __del__(self):
        del_fvec(self())
    def get(self,pos,chan):
        return fvec_read_sample(self(),chan,pos)
    def set(self,value,pos,chan):
        return fvec_write_sample(self(),value,chan,pos)
    def channel(self,chan):
        return fvec_get_channel(self(),chan)
    def data(self):
        return fvec_get_data(self())

class cvec:
    def __init__(self,size,chan):
        self.vec = new_cvec(size,chan)
    def __call__(self):
        return self.vec
    def __del__(self):
        del_cvec(self())

class sndfile:
    def __init__(self,filename,model=None):
        if (model!=None):
            self.file = new_file_wo(model.file,filename)
        else:
            self.file = new_file_ro(filename)
    def __del__(self):
        del_file(self.file)
    def info(self):
        file_info(self.file)
    def samplerate(self):
        return aubio_file_samplerate(self.file)
    def channels(self):
        return aubio_file_channels(self.file)
    def read(self,nfram,vecread):
        return file_read(self.file,nfram,vecread())
    def write(self,nfram,vecwrite):
        return file_write(self.file,nfram,vecwrite())

class pvoc:
    def __init__(self,buf,hop,chan):
        self.pv = new_aubio_pvoc(buf,hop,chan)
    def __del__(self):
        del_aubio_pvoc(self.pv)
    def do(self,tf,tc):
        aubio_pvoc_do(self.pv,tf(),tc())
    def rdo(self,tc,tf):
        aubio_pvoc_rdo(self.pv,tc(),tf())

class onsetdetection:
    """ class for aubio_onsetdetection """
    def __init__(self,type,buf,chan):
        self.od = new_aubio_onsetdetection(type,buf,chan)
    def do(self,tc,tf):
        aubio_onsetdetection(self.od,tc(),tf())
    def __del__(self):
        aubio_onsetdetection_free(self.od)

class peakpick:
    """ class for aubio_peakpicker """
    def __init__(self,threshold=0.1):
        self.pp = new_aubio_peakpicker(threshold)
    def do(self,fv):
        return aubio_peakpick_pimrt(fv(),self.pp)
    def __del__(self):
        del_aubio_peakpicker(self.pp)

class onsetpick:
    """ superclass for aubio_pvoc + aubio_onsetdetection + aubio_peakpicker """
    def __init__(self,bufsize,hopsize,channels,myvec,threshold,mode='dual'):
        self.myfft    = cvec(bufsize,channels)
        self.pv       = pvoc(bufsize,hopsize,channels)
        if mode in [complexdomain,hfc,phase,energy,specdiff]  :
                self.myod     = onsetdetection(mode,bufsize,channels)
                self.myonset  = fvec(1,channels)
        else: 
                self.myod     = onsetdetection(hfc,bufsize,channels)
                self.myod2    = onsetdetection(complexdomain,bufsize,channels)
                self.myonset  = fvec(1,channels)
                self.myonset2 = fvec(1,channels)
        self.mode     = mode
        self.pp       = peakpick(float(threshold))

    def do(self,myvec): 
        self.pv.do(myvec,self.myfft)
        self.myod.do(self.myfft,self.myonset)
        if self.mode == 'dual':
                self.myod2.do(self.myfft,self.myonset2)
                self.myonset.set(self.myonset.get(0,0)*self.myonset2.get(0,0),0,0)
        return self.pp.do(self.myonset),self.myonset.get(0,0)

def getonsetsfunc(filein,threshold,silence,bufsize=1024,hopsize=512,mode='dual'):
        #bufsize   = 1024
        #hopsize   = bufsize/2
        frameread = 0
        filei     = sndfile(filein)
        channels  = filei.channels()
        myvec     = fvec(hopsize,channels)
        readsize  = filei.read(hopsize,myvec)
        opick     = onsetpick(bufsize,hopsize,channels,myvec,threshold,mode=mode)
        mylist    = list()
        #ovalist   = [0., 0., 0., 0., 0., 0.]
        ovalist   = [0., 0., 0., 0., 0.]
        ofunclist = []
        while(readsize):
                readsize = filei.read(hopsize,myvec)
                isonset,val = opick.do(myvec)
                if (aubio_silence_detection(myvec(),silence)):
                        isonset=0
                ovalist.append(val)
                ovalist.pop(0)
                ofunclist.append(val)
                if (isonset == 1):
                        i=len(ovalist)-1
                        # find local minima before peak 
                        while ovalist[i-1] < ovalist[i] and i > 0:
                                i -= 1
                        now = (frameread+1-i)
                        if now > 0 :
                                mylist.append(now)
                        else:
                                now = 0
                                mylist.append(now)
                frameread += 1
        return mylist, ofunclist


def getonsetscausal(filein,threshold,silence,bufsize=1024,hopsize=512,mode='dual'):
        frameread = 0
        filei     = sndfile(filein)
        channels  = filei.channels()
        myvec     = fvec(hopsize,channels)
        readsize  = filei.read(hopsize,myvec)
        opick     = onsetpick(bufsize,hopsize,channels,myvec,threshold,mode=mode)
        mylist    = list()
        while(readsize):
                readsize = filei.read(hopsize,myvec)
                isonset,val = opick.do(myvec)
                if (aubio_silence_detection(myvec(),silence)):
                        isonset=0
                if (isonset == 1):
                        now = frameread
                        if now > 0 :
                                mylist.append(now)
                        else:
                                now = 0
                                mylist.append(now)
                frameread += 1
        return mylist

def getonsets(filein,threshold=0.2,silence=-70.,bufsize=1024,hopsize=512,mode='dual'):
        frameread = 0
        filei     = sndfile(filein)
        channels  = filei.channels()
        samplerate= filei.samplerate()
        myvec     = fvec(hopsize,channels)
        readsize  = filei.read(hopsize,myvec)
        opick     = onsetpick(bufsize,hopsize,channels,myvec,threshold,mode=mode)
        mylist    = list()
        #ovalist   = [0., 0., 0., 0., 0., 0.]
        ovalist   = [0., 0., 0., 0., 0.]
        while(readsize):
                readsize = filei.read(hopsize,myvec)
                isonset,val = opick.do(myvec)
                if (aubio_silence_detection(myvec(),silence)):
                        isonset=0
                ovalist.append(val)
                ovalist.pop(0)
                if (isonset == 1):
                        i=len(ovalist)-1
                        # find local minima before peak 
                        while ovalist[i-1] < ovalist[i] and i > 0:
                                i -= 1
                        now = (frameread+1-i)
                        if now > 0 :
                                mylist.append(now)
                        else:
                                now = 0
                                mylist.append(now)
                frameread += 1
        return mylist

class pitchpick:
    def __init__(self,bufsize,hopsize,channels,myvec,srate):
        self.myfft    = cvec(bufsize,channels)
        self.pv       = pvoc(bufsize,hopsize,channels)
        self.pitchp   = new_aubio_pitchmcomb(bufsize,channels)
        self.filt     = filter(srate,"adsgn")

    def do(self,myvec): 
        #self.filt.do(myvec)
        #self.filt.do(myvec)
        self.pv.do(myvec,self.myfft)
        return aubio_pitchmcomb_detect(self.pitchp,self.myfft())

class filter:
    def __init__(self,srate,type=None):
        if (type=="adsgn"):
            self.filter = new_aubio_adsgn_filter(srate)
    def __del__(self):
        #del_aubio_filter(self.filter)
        pass
    def do(self,myvec):
        aubio_filter_do(self.filter,myvec())