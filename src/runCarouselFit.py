""" Control file to run simple carousel analysis and return
    attenuation correction function. Based on IDL code by Anthony
    Evershed.

    This is the command line interface which is executed by:
       python ../src/runCarouselFit.py
    within the "test" directory. The location is important since the
    code assumes that spectral data is available in the "spectra"
    subdirectory which is currently in test.
    Most of the fitting operations are implemented in the file carouselUtils.py.
"""
import sys
import os.path
import logging
import timeit
import numpy as np
import itertools as it
from numpy.polynomial.polynomial import polyval
#from carouselUtils import *
import carouselUtils as cu
try:
    import matplotlib.pyplot as plt
except ImportError:
    sys.exit("Error: cant find matplotlib")
import pdb

markerErr = it.cycle((',', '+', '.', 'o', '*'))

def getAtt(dw,dcu,dal,dti,dcsi,me):
    """ test function to evaluate attenuation """
    cuatt = np.zeros(me)
    alatt = np.zeros(me)
    watt = np.zeros(me)
    csiatt = np.zeros(me)
    tiatt = np.zeros(me)
    cuatt[0:me-1] = cuAtten.getMu()[0:me-1]
    tiatt[0:me-1] = tiAtten.getMu()[0:me-1]
    alatt[0:me-1] = alAtten.getMu()[0:me-1]
    watt[0:me-1] = wAtten.getMu()[0:me-1]
    csiatt[0:me-1] = csiAtten.getMu()[0:me-1]
    at_se = se*np.exp(-cuatt*dcu-watt*dw-alatt*dal)*xe*(1-np.exp(-csiatt*dcsi))
    return at_se


def loadAll(string):
    """ read both the carousel definition file and the data file with the
        calibration data """
    global carouselData, carouselCal, xSpec
    if len(string)<3:
        print "syntax: load <cardef> <carrun>"
        return
    
    carouselData = cu.carousel(string[1])
    if not carouselData.isValid():
        print "** failed to load carousel data"
        return
    carouselCal = cu.carouselCalibrationData(string[2], carouselData)
    if not carouselCal.isValid():
        print "** failed to load calibration data"
        return
    xSpec = cu.specData(carouselCal.targetMat, carouselCal.voltage, carouselCal.angle)
    if not xSpec.isValid():
        sys.exit("** failed to load spectrum")

 
def showImg(string):
    """ plot the n calibration images on one plot; user must kill
        window to continue"""
    if carouselCal == None:
        print "must load data first"
        return
    try:
        width = carouselCal.width
    except:
        print "** must read calibration data first"
        return
    plt.figure(FIG_IMG)
    carouselCal.plotCalData(False, width)
    plt.show(block=False)


def showSpec(string):
    """ plot spectra of source along with filtered spectra and response spectra.
        Note that these just use input data, not fitted data.
    """
    if carouselCal == None:
        print "must load data first"
        return
    if xSpec.valid:
        plt.figure(FIG_SPEC)
        yval = np.zeros(xSpec.getS().size)
        norm = np.sum(xSpec.getS())
        yval = xSpec.getS()/norm
        plt.plot(xSpec.getE(), yval,label='raw')
        if carouselCal.filterCount>0:
            n = len(xSpec.getS())
            attSpec = np.copy(yval)*norm
            for i in range(carouselCal.filterCount):
                attSpec = attSpec*np.exp(-carouselCal.filterAtten[i].getMu()[0:n]*carouselCal.filterWidth[i])
                #print "attn0-1=",carouselCal.filterAtten[i].getMu()[0:9]
                #print "width=",carouselCal.filterWidth[i]
            norma = np.sum(attSpec)
            attSpec = attSpec/norma
            plt.plot(xSpec.getE(),attSpec,label='filtered')
            meanE = np.sum(attSpec*xSpec.getE())
            dev2 = np.sum(attSpec*xSpec.getE()*xSpec.getE()) - meanE*meanE
            print "For filtered spectrum:"
            print "mean E =",meanE," std dev = ",np.sqrt(dev2)," total atten ratio = ",norm/norma
            dE = xSpec.getE()[1]-xSpec.getE()[0]
            nmean = int(meanE/dE)
            print " atten ratio at mean energy = ",xSpec.getS()[nmean]/(attSpec[nmean]*norma)
            detWid =carouselCal.detectorWidth
            attDet = detWid*carouselCal.detectorAtten.getMu()[:len(attSpec)]
            resSpec = attSpec*xSpec.getE()*(1.-np.exp(-attDet))
            resSpec = resSpec/np.sum(resSpec)
            plt.plot(xSpec.getE(),resSpec,label='response')
        if len(string) > 1 and string[1] == 'log':
            plt.yscale('log')
        #else:
        #    print "string=",string
        plt.legend()
        plt.xlabel('KeV')
        plt.ylabel('S(E) (normalised)')
        plt.draw()
        plt.show(block=False)
    else:
        print "must load data first"
        
def quitCarousel(string):
    """ exit the command level """
    sys.exit("quit called")

def showAtt(string):
    """ 1D plots of attenuation of sample n"""
    if carouselCal == None:
        print "must load data first"
        return
    defline=400
    plt.figure(FIG_ATT1D)
    if len(string)>1:
        try:
            samp = int(string[1])
        except:
            print "failed to read sample value"
            return
        if len(string)>2:
            try:
                defline = int(string[2])
            except:
                print "failed to read line number"
        if samp > -1 and samp < carouselCal.samples and defline > -1 and defline < carouselCal.lines:
            z = carouselCal.getImage(samp)
            plt.plot(z[defline,:])
            plt.xlabel("Column number at line "+str(defline))
            plt.ylabel("attenuation")
            plt.draw()
            plt.show(block=False)
        else:
            print "sample number out of range"
    else:
        for i in range(carouselCal.samples):
            z = carouselCal.getImage(i)
            plt.plot(z[defline,:])
        plt.xlabel("Column number at line "+str(defline))
        plt.ylabel("attenuation")
        plt.draw()
        plt.show(block=False)
    return

def showCor(string):
    """ plot the fitted correction curve from the polynomial data """
    if not 'xtab' in globals():
        print "No correction data available; run fitatt first"
        return
    if len(string)==1:
        linevals = [ 0, int((len(xtab)-1)/2), len(xtab)-1 ]
    else:
        linevals = []
        for i in range(len(string)-1):
            try:
                lineno=int(string[i+1])
            except:
                print "Bad integer value: ",string[i+1]
                return
            if lineno>=0 and lineno<=len(xtab):
                linevals.append(lineno)
            else:
                print "skipping out of range value: ",lineno
    print "lines=",linevals
    #print ytab[::30]
    #for line in linevals:
    #    xvals = polyval( xtab[0,:], polyfit[line,::-1])
    #    print "pv=",polyfit[line,::-1]
    #    print xvals[::30]
    #    print " "
    mymax=np.max(xtab[:,-1])
    xval = np.linspace(0.0,mymax,num=300)
    plt.figure(FIG_COR)
    for line in linevals:
        yval = polyval( xval,polyfit[line,::-1])
        plt.plot(xtab[line,:],ytab,xval,yval,':')
        plt.xlabel('Observed log attenuation ratio')
        plt.ylabel('Effective single energy log attenuation ratio')
    # add the x=y line for comparison with circles for fit points
    nsamp = len(carouselData.mask)-1
    xarr = np.zeros(nsamp)
    count = 0
    for i in range(nsamp):
        if not carouselData.mask[i]:
            xarr[count] = carouselCal.getAvAtten(linevals[0],i)
            count = count+1
            #print "mask ",i,"t",carouselCal.getAvAtten(linevals[0],i)
    plt.plot([0.0,mymax],[0.0,mymax],'r--')
    plt.plot(xarr,xarr,'ro')
    plt.draw()
    plt.show(block=False)

def setFilters(string):
    try:
        if carouselCal.isValid():
            #print "have carouselCal - str: ",string
            if len(string) == 3:
                #print "try and set ",string[1:]
                try:
                    mat = string[1]
                    val = float(string[2])
                except:
                    print "** Bad values"
                    return
                for i in range(carouselCal.filterCount):
                    if carouselCal.filterMaterial[i] == mat:
                        carouselCal.filterWidth[i] = val
                        print "set ",mat," filter width to ",val
                        return
            else:
                print "filter, width:"
                for i in range(carouselCal.filterCount):
                    print carouselCal.filterMaterial[i], ",", carouselCal.filterWidth[i]
    except:
        print "no carousel data file loaded"

def calcAtt(string):
    print "Not implemented"
    pass

def setSamplesToFit(string):
    """ set or print the number of samples to be fitted to"""
    if carouselCal == None:
        print "must load data first"
        return
    if len(string) > 1:
        try:
            samples = int(string[1])
        except:
            print "must give integer"
            return
        if samples>0:
            # should not be two values here
            carouselCal.samples=samples
            carouselData.numSamples = samples+1 # this includes the "null" sample, which is not read
    print "samples set to ",carouselCal.samples
        

def fitAtt(string):
    """ Check necessary data has been set then fit model to carousel data.
        Finally generate curves for attenuation over each line using the
        correction material (corMat/corEn) and then fit a polynomial to this for
        correction purposes.
        """
    global carouselData, carouselCal, xSpec, debug, vary
    global res,xtab,ytab,polyfit
    if carouselData == None or carouselCal == None:
        print "must load data first"
        return
    if not carouselData.valid or not carouselCal.valid:
        print "data not correctly loaded"
        return
    defMat = "Cu"
    fit = cu.fitData(carouselData, carouselCal, defMat)
    fit.verbose = debug
    if debug:
        np.seterr(over='warn',invalid='warn')
    else:
        np.seterr(over='ignore',invalid='ignore')

    x = np.zeros(4+np.sum(vary))
    if len(string) == 5:
        print "Fitting variables: ",np.sum(vary)+4
        # The fit function consists of 3 polynomial expressions in the
        # the line number, plus a possible polynomial in the energy.
        # Initial values for the zero order terms are
        # given here, the higher terms (if any) are set to zero.
        offset = vary[0]
        x[offset] = float(string[2])
        offset = offset+1+vary[1]
        x[offset] = float(string[3])
        offset = offset+1+vary[2]
        x[offset] = float(string[4])
        nlines = int(string[1])
    elif len(string) == 2:
        nlines = int(string[1])
        if len(res) == len(x):
            x = res
        else:
            print "Using zero initial guess"   
    else:
        print "wrong number of args: need fitatt nlines x1 x2 x3"
        print "where nlines=number of lines to fit and x1/2/3 are initial values"
        print "for the unknowns: target width, ln(detector width), filter width"
        return
    if nlines < 1 or nlines > carouselCal.lines:
        print "fit lines out of range, must be 1 to ",carouselCal.lines
        return
    fit.vary_target = vary[0]
    fit.vary_detector = vary[1]
    fit.vary_filter = vary[2]
    fit.vary_energy = vary[3]
    t0 = timeit.default_timer()
    res,cov,infodict,mesg,ier = fit.dofit(nlines,x)
    tim = timeit.default_timer()-t0
    print "time=",tim
    print "dofit returned: "
    print " best fit values = ",res
    if ier>0 and ier<5:
        print " ier = ",ier
    else:
        print "** Fit failed: ier=",ier
        print "   message=",mesg
    print " iterations = ",infodict["nfev"]
    # measure error
    samples = carouselCal.samples
    ofile = open('fit.log','w')
    ofile.write('time={0:12.6f}\n'.format(tim))
    ofile.write('dofit returned: ')
    ofile.write(' best fit values = \n')
    ofile.write(str(res)+'\n')
    ofile.write(' ier = {0:5d}\n'.format(ier))
    ofile.write(' iterations = {0:5d}\n'.format(infodict["nfev"]))
    ofile.write(' cov = ')
    ofile.write(str(cov)+'\n')
    ofile.write(' mesg = '+mesg+'\n')
    rfile = open('param.log','w')
    rfile.write('fit input: lines={0:5d}\n'.format(nlines))
    rfile.write('guess: ')
    rfile.write(str(x))
    rfile.write('\n')
    rfile.write('solution: ')
    rfile.write(str(res))
    rfile.write('\n')
    sumtot=0.
    summax=0.
    #if debug:
    #    pdb.set_trace()

    # calcualte the attenuation(corEn) vs attenuation(observed) and return
    # polynomial fit to these curves for each line.
    xtab,ytab,polyfit = fit.linesPolyFit(res,corMat,corEn,300,12.0)
    # find average and max error for each line
    rfile.write('polyfits '+str(polyfit.shape[0])+" "+str(polyfit.shape[1])+"\n")
    lsumsq = []
    avatt = np.zeros((2,samples))
    count = 0
    for line in range(nlines):
        sumsq = 0.
        for sample in range(samples):
            if carouselData.mask[sample]:
                continue
            sumsq += (fit.atten[line,sample] - carouselCal.getAvAtten(line,sample) ) ** 2
            if line==0:
                avatt[0,sample] = carouselCal.getAvAtten(line,sample)
                avatt[1,sample] = fit.atten[line,sample]
        ofile.write(' {0:5d}  {1:12.6f}\n'.format(line,sumsq))
        lsumsq.append(sumsq)
        sumtot += sumsq
        if sumsq>summax:
            summax = sumsq
        if debug:
            print "Line: ",line," ave error:",sumsq
        # save poly data to param.log
        rfile.write('{0:5d} '.format(line)+str(polyfit[line,:])+'\n')
    # write data in binary file
    bfile = open("polyfit.npz","wb")
    np.save(bfile,polyfit)
    bfile.close()
    #
    print "average error: ",sumtot/nlines
    print "max error: ",summax
    rfile.write("average error: {0:12.6f}\nmax error: {1:12.6f}\n".format(sumtot/nlines,summax))
    plt.figure(FIG_ERR)
    plt.plot(lsumsq)
    plt.xlabel('line number')
    plt.ylabel('mean sq error')
    plt.draw()
    plt.show(block=False)
    #
    plt.figure(FIG_ATTCOMP)
    plt.subplot(211)
    plt.plot(avatt[0,:],'bx')
    mark = markerErr.next()
    plt.plot(avatt[1,:],marker=mark)
    plt.xlabel('sample number')
    plt.ylabel('log(I0/I)')
    plt.subplot(212)
    plt.plot(avatt[0,:]-avatt[1,:],marker=mark)
    plt.ylabel('err log(I0/I)')
    plt.draw()
    plt.show(block=False)
    ofile.close()
    rfile.close()


def setWidth(words):
    """ set the half width of area along row to be averaged"""
    if len(words)>1:
        try:
            width = float(words[1])
            carouselCal.width = width
        except:
            print "load carousel data before setting width"
            return
    else:
        try:
            print "width= ",carouselCal.width, " (No. of pixels about centre of line to average)"
        except:
            print "width not set until carousel data loaded"


def showCalConf(string):
    """ prints out some calibration data"""
    try:
        filterCount = carouselCal.filterCount
    except NameError:
        print "** must read calibration data first"
        return
    print "filter count = ", filterCount
    print "filter  material width    density   fittable"
    for i in range(filterCount):
        print  '{0:4d}     {1:7s} {2:7f} {3:7f}'.format(i,
               carouselCal.filterMaterial[i],
               carouselCal.filterWidth[i], carouselCal.filterDensity[i])
    print "Detector:"
    print '         {0:7s} {1:7f} {2:7f}'.format(
               carouselCal.detectorMaterial,
               carouselCal.detectorWidth, carouselCal.detectorDensity)
    print "Source filter:"
    print '         {0:7s} {1:7f} {2:7f}'.format(carouselCal.targetMat,
               0.0, carouselCal.targetDensity)
    print "Voltage=",  carouselCal.voltage, " angle=", carouselCal.angle

def setVary(strlst):
    """ define polynomial order of parameters to fit """
    global vary
    if len(strlst)==1:
        print "Control order of polynomial used for fitting across lines"
        print " - 3 widths are fitted for target, detector and filter"
        print " - Experimental is to set energy dependence away from linear"
        print "settings:"
        print "target: ",vary[0]
        print "detector: ",vary[1]
        print "filter: ",vary[2]
        print "energy dependence: ",vary[3]
        return
    if len(strlst)==3:
        try:
            np = int(strlst[2])
        except:
            print "** failed to read np"
            np = 0
        if strlst[1]=="target":
            vary[0] = np
        elif strlst[1]=="detector":
            vary[1] = np
        elif strlst[1]=="filter":
            vary[2] = np
        elif strlst[1]=="energy":
            vary[3] = np
        else:
            print "Not recognised: ",strlst[1]
    else:
        print "syntax: vary [target|detector|filter|energy n]"

def debugToggle(cmd):
    """ toggle debug """
    global debug
    debug = not debug
    print "debug set to ",debug
    

def helpCar(cmd, string):
    """ just print list of commands"""
    print "Carousel calibration utility"
    print " "
    print "cmds:"
    for i in cmd:
        print "  ", i
    print " "
    print "To execute script file use: read <filename>"
    print " "
    print "The required input is a set of images of test pieces imaged at the exact same"
    print "Xray settings as the sample. These may be in a carousel or a crown device. The"
    print "details of each test item (material/density/thickness) must be provided in a"
    print "file in './carouselData'. Using these images a fit is made to the effective"
    print "energy response function of the Xray source/detector. Using this fit a correction"
    print "curve can be determined to map from observed attenuation to true attenuation of the"
    print "dominant Xray material of the sample. This will be inaccurate on samples with muliple"
    print "material types in them. The output is a file of polynomial fits giving the corrections"
    print "which can be used in the python program 'applyTransForm.py'"
    print " "

def setCorMat(words):
    """ Input the name of the material that will be the target of the attenuation correction
        e.g. Calcium hydroxyapatite which might be defined in a file cahypa.txt, precalculated
        using the program xcom. Without arguments, list current setting, if any."""
    global corMat,corEn
    if len(words)>2:
        name = words[1]
        try:
            corEn = float(words[2])
        except:
            print "failed to read energy value"
            return
    else:
        if corMat.name != "":
            print "corMat is set to ",corMat.name," and energy ",corEn,"KeV"
        else:
            print "corMat is not set"
        return
    name = words[1]
    print "reading correction material definition from file: ",name
    try:
        corMat = cu.materialAtt(name,1.0)
    except:
        print "error reading material type"
    
def mask(words):
    """ show or set a mask array which is used to define if some of the sample data
        is not to be used in the fit. e.g. "mask 7" will mean sample 7 is omitted
        from the fit. "mask off" will restore all samples to the fit.
    """
    global carouselData, carouselCal
    if carouselData== None:
        print "must load data first"
        return
    if len(words) == 1:
        print "Mask = ",carouselData.mask
    elif words[1] == "off":
        carouselData.mask.fill(False)
    else:
        try:
            for i in range(len(words)-1):
                num = int(words[i+1])
                if num > 0:
                     carouselData.mask[num-1] = True
                elif num < 0:
                     carouselData.mask[-num-1] = False
                else:
                     print "Warning: label 0 ignored"
        except:
            print "Error: bad value in list"
        
def transform(words):
    """ TEST code to try and fix up RCaH data; this is only a fudge; must get right data
        in first place, Assume we have "I" data and want log(I0/I) values, where I0 is a
        guess provided by the user.
    """
    global carouselData, carouselCal
    if len(words)<2:
        print "Must provide I0 value"
        return
    I0 = float(words[1])
    nsamp = len(carouselData.mask)-1
    for i in range(nsamp):
        z = carouselCal.getImage(i)
        zerocount = sum(sum(z<=0))
        if zerocount>0:
            print "zeros for sample ",i," are ",zerocount
        z[z<=0] = 1e-4
        z = np.log(z)
        z = np.log(I0) - z
        carouselCal.getImage(i)[:,:] = z
        #carouselCal.getImage(nsamp)[:,:] = - np.log(carouselCal.getImage(nsamp)[:,:])
        # np.log(I0)

##def applyCorrection(words):
##    """ Apply the fitted correction polnomials to a data file. Here we assume a raw file
##        input of 32 bit floats. First arg is filename. If 2nd argument present it is taken
##        to be I0 for transform data-> ln ( I0/data )
##    """
##    global carouselData, carouselCal
##    if carouselData== None:
##        print "must load data first"
##        return
##    if len(words)<2:
##        print "Must provide file name"
##        return
##    if len(words)==3:
##        I0 = float(words[2])
##    else:
##        I0 = 0
##    nsamp = carouselCal.nsamp
##    rows = carouselCal.rows
##    lines = carouselCal.lines
##    if os.path.isfile(imageFile):
##        with open(imageFile, 'rb') as fl:
##            image = np.fromfile(fl, dtype = "float32",
##                                       count = rows*lines*nsamp).reshape(nsamp, lines, rows)
##        else:
##            print "Image file not found!: ", imageFile
##            return
##    if I0>0:
##        image = log(I0) - np.log( image )
#    for line in range(lines):
#        yval = polyval( image,polyfit[line,::-1])
    

        

# Set of commands that are implemented and the corresponding function names.
# Additional commands and functions can be added here.
cmd_switch = { "load":loadAll,
               "showimg":showImg,
               "showspec":showSpec,
               "showconf":showCalConf,
               "showatt":showAtt,
               "showcor":showCor,
               "setfilters":setFilters,
               "setwidth":setWidth,
               "calcatt":calcAtt,
               "fitatt":fitAtt,
               "vary":setVary,
               "setcormat":setCorMat,
               "debug":debugToggle,
               "fitsamples":setSamplesToFit,
               "mask":mask,
               "quit":quitCarousel,
               "help":helpCar,
               "transform":transform,
               }

# set figures to use for different plots
FIG_COR = "Correction"
FIG_ATT1D = "CarouselLines"
FIG_SPEC = "Spectra"
FIG_IMG = "CarouselImages"
FIG_ERR = "ErrorInFit"
FIG_ATTCOMP = "ObservedVsFittedAtten"
# simple command line loop to allow loading of data and run
# of fitting code.

global carouselData, carouselCal
carouselData = None
carouselCal = None

if __name__ == "__main__":
    logging.basicConfig(level = logging.WARNING)
    nargs = len(sys.argv)
    debug = False
    carouselCal = None

    print " "
    print " *** Carousel data fitting program ***"
    print " "
    print " Code based on algorithms developed at Queen Mary University"
    print " of London by Graham Davis, Anthony Evershed et al"
    print " This implementation by Ron Fowler at STFC"
    print " contact ronald.fowler@stfc.ac.uk"
    print " Funded by the CCPi project"
    print " "
    # set the polynomial order of the fitting variables. Variables are
    # function of line number.
    vary = np.zeros(4,dtype='int')
    vary[3] = -1
    # set an object for the material to which attenuation is to be corrected to; this is null until the user provides one
    corMat = cu.materialAtt("",1.0)
    # command loop
    filein = False
    while True:
        try:
            if filein:
                cmd = infile.readline().strip()
                if cmd=='':
                    filein = False
                    infile.close()
                    continue
                print " bhc: ",cmd
            else:
                cmd = raw_input("bhc: ").strip()
        except EOFError as ex:
            sys.exit("EOF")
        words = cmd.split(" ")
        try:
            if words[0] == "help":
                cmd_switch[words[0]](cmd_switch, words)
            elif words[0] == "read":
                if len(words)>1 and os.path.isfile(words[1]):
                    rfile = words[1]
                    infile = open(rfile,'r')
                    filein = True
                else:
                    print "Error - syntax: read file"
                    continue
            elif words[0] == "#":
                continue
            else:
                cmd_switch[words[0]](words)
        except SystemExit as ex:
            sys.exit("quit")
        except KeyError as ex:
            if not ( words[0] == "" ):
                print "** command not found: ", words[0]
        except:
            print "** internal error: ", sys.exc_info()[0]
            raise
        
