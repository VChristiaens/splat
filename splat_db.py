# -*- coding: utf-8 -*-
from __future__ import print_function, division

"""
.. note::
         These are the database functions for SPLAT 
"""

import astropy
import base64
import copy
#from datetime import datetime
import csv
import glob
import os
import re
import requests
import splat
#from splat import SPLAT_PATH, SPLAT_URL, DB_SOURCES, DB_SPECTRA
import sys
#from scipy import stats
import numpy
from astropy.io import ascii, fits            # for reading in spreadsheet
from astropy.table import Column, Table, join, vstack           # for reading in table files
from astropy.time import Time            # for reading in table files
from astropy.coordinates import SkyCoord
from astropy import units as u            # standard units
from astroquery.simbad import Simbad
from astroquery.vizier import Vizier
#from PyQt4 import QtGui, QtCore
from shutil import copyfile

# Python 2->3 fix for input
try: input=raw_input
except NameError: pass

DB_FOLDER = '/db/'
DB_ORIGINAL_FILE = 'db_spexprism.txt'
DB_PHOTOMETRY_FILE = 'photometry_data.txt'
BIBFILE = 'biblibrary.bib'
TMPFILENAME = 'splattmpfile'

#SPLAT_URL = 'http://pono.ucsd.edu/~adam/splat/'
#DATA_FOLDER = '/reference/Spectra/'

#DB_SOURCES = fetchDatabase(DB_SOURCES_FILE)
#print(DB_SOURCES)
#DB_SPECTRA = fetchDatabase(DB_SPECTRA_FILE)

# change the command prompt
sys.ps1 = 'splat db> '

# WINDOW class for examining spreadsheets
#


def processModels(**kwargs):
    '''
    :Purpose: Generates a set of smoothed models and SEDs for an input model set; this is a function that requires 'superuser' access
    '''

    if splat.checkAccess() is not True:
        print('\nThis routine may only be run by SPLAT administrators\n')
        return

# ALLARD files
    if kwargs.get('model',' ').lower() == 'btsettl2015':
        basefolder = os.path.expanduser("~")+'/models/allard/cifist2015/BT-Settl_M-0.0a+0.0/'
        files = glob.glob(basefolder+'lte*.7')
        teff = [100.*float(f[len(basefolder)+3:len(basefolder)+8]) for f in files]
        logg = [float(f[len(basefolder)+9:len(basefolder)+12]) for f in files]
        z = [float(f[len(basefolder)+12:len(basefolder)+16]) for f in files]

# baseline spectrum for wavelength solution        
        ospex = splat.Spectrum(10001) 
#        uspex = splat.Spectrum(12160)      - need to make this file available before using

        for f in files:
# read in file
            print('\nReading in file {}'.format(f))
            data = ascii.read(f,format='tab')
            wave  = numpy.array([float(x[0][0:13])/1.e4 for x in data])
            flux = numpy.array([10.**(float(x[0][13:25].replace('D','e'))-8.) for x in data])

# generate SpeX formats using a baseline spectrum
# THIS IS A TEMPORARY SET UP  
            w = numpy.where(numpy.logical_and(wave >= 0.6,wave <= 2.5))
            sp = splat.Spectrum(wave=wave[w],flux=flux[w])
            wn = wave[numpy.where(numpy.logical_and(wave >= 1.6,wave <= 1.7))]
            sp.resolution = wn[1]/(wn[1]-wn[0])
            sp.smooth(resolution=200)
            s03 = sp.copy()






def bibTexParser(bib_tex,**kwargs):
    '''
    :Purpose:
        Parses a bibtex segment and returns a dictionary of parameter fields

    :Required parameters:
        :param bib_tex: String containing bibtex data in standard format

    :Optional parameters:
        None

    :Output:
        A dictionary containing the parsed bibtex information

    '''
    bib_dict = {"bib_tex": bib_tex}
    bib_tex.strip('\n')
    # get bib code
    begin = bib_tex.find('{')  
    end = bib_tex.find(',')
    bib_dict["bibcode"] = bib_tex[begin+1:end]
    bib_tex = bib_tex[end+1:]   # remove bib code line
    
    bib_tex =  bib_tex.split(',\n')  # this moght not always work for author lists
    
    for line in bib_tex:
        line = line.strip()
        line = line.replace('{','').replace('}','').replace('\"','').replace('\n','').replace('\t','') 
        line = line.split('=')
        line[0] = line[0].strip().lower()
        line[1] = line[1].strip()
        bib_dict[line[0]] = line[1]

# Journal massaging
    if 'journal' in list(bib_dict.keys()):
        if bib_dict['journal'] == '\\apj':
            bib_dict['journal'] = 'ApJ'
        elif bib_dict['journal'] == '\\apjs':
            bib_dict['journal'] = 'ApJS'
        elif bib_dict['journal'] == '\\aj':
            bib_dict['journal'] = 'AJ'
        elif bib_dict['journal'] == '\\araa':
            bib_dict['journal'] = 'AR&A'
        elif bib_dict['journal'] == '\\aap':
            bib_dict['journal'] = 'A&A'
        elif bib_dict['journal'] == '\\mnras':
            bib_dict['journal'] = 'MNRAS'
        elif bib_dict['journal'] == '\\pasp':
            bib_dict['journal'] = 'PASP'
        elif bib_dict['journal'] == '\\pnas':
            bib_dict['journal'] = 'PNAS'
        else:
            pass
    else: 
        bib_dict['journal'] = 'UNKNOWN'
        
    return bib_dict


def shortRef(bib_dict,**kwargs):
    '''
    :Purpose:
        Takes a bibtex dictionary and returns a short (in-line) version of the citation

    :Required parameters:
        :param bib_tex: Dictionary output from bibTexParser, else a bibcode that is fed into bibTexParser

    :Optional parameters:
        None

    :Output:
        A string of the format ``Burgasser, A. J., et al. (2006, ApJ, 710, 1142)``

    '''
    if type(bib_dict) is not dict:
        if type(bib_dict) is str:
            bib_dict = getBibTex(bib_dict,**kwargs)
        else:
            raise NameError('Input to shortRef is neither a bibcode nor a bibTex dictionary')

    authors = bib_dict['author'].split(' and ')
    if len(authors) == 1:
        output = '{}'.format(authors[0].replace('~',' '))
    elif len(authors) == 2:
        output = '{} & {}'.format(authors[0].replace('~',' '),authors[1].replace('~',' '))
#    elif len(a) == 3:
#        output = '{}, {} & {}'.format(a[0].replace('~',' '),a[1].replace('~',' '),a[2].replace('~',' '))
#    else:
#        output = '{}, {}, {}, et al.'.format(a[0].replace('~',' '),a[1].replace('~',' '),a[2].replace('~',' '))
    else:
        output = '{} et al.'.format(authors[0].replace('~',' '))

# fill in missing data
    if 'year' not in bib_dict.keys():
        bib_dict['year'] = ''
    if 'journal' not in bib_dict.keys():
        bib_dict['journal'] = ''
    if 'volume' not in bib_dict.keys():
        bib_dict['volume'] = ''
    if 'pages' not in bib_dict.keys():
        bib_dict['pages'] = ''

    return output+' ({}, {}, {}, {})'.format(bib_dict['year'],bib_dict['journal'],bib_dict['volume'],bib_dict['pages'])


def longRef(bib_dict,**kwargs):
    '''
    :Purpose:
        Takes a bibtex dictionary and returns a long (in-line) version of the citation

    :Required parameters:
        :param bib_tex: Dictionary output from bibTexParser, else a bibcode that is fed into bibTexParser

    :Optional parameters:
        None

    :Output:
        A string of the format ``Burgasser, A. J., Cruz, K. L., Cushing, M., et al. SpeX Spectroscopy of Unresolved Very Low Mass Binaries. 
        I. Identification of 17 Candidate Binaries Straddling the L Dwarf/T Dwarf Transition. ApJ 710, 1142 (2010)``

    '''
    if type(bib_dict) is not dict:
        if type(bib_dict) is str:
            bib_dict = getBibTex(bib_dict,**kwargs)
        else:
            raise NameError('Input to shortRef is neither a bibcode nor a bibTex dictionary')

    authors = bib_dict['Author'].split(' and ')
    if len(authors) == 1:
        output = '{}'.format(authors[0].replace('~',' '))
    elif len(authors) == 2:
        output = '{} & {}'.format(authors[0].replace('~',' '),authors[1].replace('~',' '))
    elif len(authors) == 3:
        output = '{}, {} & {}'.format(authors[0].replace('~',' '),authors[1].replace('~',' '),authors[2].replace('~',' '))
    else:
        output = '{}, {}, {}, et al'.format(authors[0].replace('~',' '),authors[1].replace('~',' '),authors[2].replace('~',' '))

# fill in missing data
    if 'year' not in bib_dict.keys():
        bib_dict['year'] = ''
    if 'title' not in bib_dict.keys():
        bib_dict['title'] = ''
    if 'journal' not in bib_dict.keys():
        bib_dict['journal'] = ''
    if 'volume' not in bib_dict.keys():
        bib_dict['volume'] = ''
    if 'pages' not in bib_dict.keys():
        bib_dict['pages'] = ''

    return output+'. {}. {}, {}, {} ({})'.format(bib_dict['title'],bib_dict['journal'],bib_dict['volume'],bib_dict['pages'],bib_dict['year'])



def getBibTex(bibcode,**kwargs):
    '''
    Purpose
        Takes a bibcode and returns a dictionary containing the bibtex information; looks either in internal SPLAT
            or user-supplied bibfile, or seeks online. If nothing found, gives a soft warning and returns False

    :Note:
        **Currently not functional**

    :Required parameters:
        :param bibcode: Bibcode string to look up (e.g., '2014ApJ...787..126L')

    :Optional parameters:
        :param biblibrary: Filename for biblibrary to use in place of SPLAT internal one
        :type string: optional, default = ''
        :param online: If True, go directly online; if False, do not try to go online 
        :type logical: optional, default = null

    :Output:
        - A dictionary containing the bibtex fields, or False if not found

    '''

# go online first if directed to do so
    if kwargs.get('online',False) and checkOnline():
        bib_tex = getBibTexOnline(bibcode)

# read locally first
    else:
        biblibrary = kwargs.get('biblibrary', splat.SPLAT_PATH+DB_FOLDER+BIBFILE)
# check the file
        if not os.path.exists(biblibrary):
            print('Could not find bibtex library {}'.format(biblibrary))
            biblibrary = splat.SPLAT_PATH+DB_FOLDER+BIBFILE

        if not os.path.exists(biblibrary):
            raise NameError('Could not find SPLAT main bibtext library {}; something is wrong'.format(biblibrary))


        with open(biblibrary, 'r') as bib_file:
            text = bib_file.read()
            #print re.search('@[A-Z]+{' + bib_code, bib_file)        
            in_lib = re.search('@[a-z]+{' + bibcode, text)
            if in_lib == None:  
                if kwargs.get('force',False): return False
                print('Bibcode {} not in bibtex library {}; checking online'.format(bibcode,biblibrary))
                bib_tex = getBibTexOnline(bibcode)
            else:
                begin = text.find(re.search('@[a-z]+{' + bibcode, text).group(0))
                text = text[begin:]
                end = text.find('\n@')
                bib_tex = text[:end]

    if bib_tex == False:
        return False
    else:
        return bibTexParser(bib_tex)


def getBibTexOnline(bibcode):
    '''
    Purpose
        Takes a bibcode and searches for the bibtex information online through NASA ADS; requires user to be online.
            If successful, returns full bibtex string block; otherwise False.

    :Required parameters:
        :param bibcode: Bibcode string to look up (e.g., '2014ApJ...787..126L')

    :Optional parameters:
        :param bibfile: Filename for bibfile to use in place of SPLAT internal one
        :type string: optional, default = ''
        :param online: If True, go directly online; if False, do not try to go online 
        :type logical: optional, default = null

    :Output:
        - A string block of the basic bibtex information

    '''
    if not checkOnline():
        return False

    url_begin = "http://adsabs.harvard.edu/cgi-bin/nph-bib_query?bibcode="
    url_end = "&data_type=BIBTEX"
    url = url_begin + bibcode + url_end
    bib_tex = requests.get(url).content
    
    # Check if content is in html which means bad bib_code was given
    if "<HTML>" in bib_tex:
        print('{} is not a valid online bib code.'.format(bibcode))
        return False       
        
    # Cut off extraneous info from website before the bibtex code
    else:
        begin = bib_tex.find('@')
        bib_tex = bib_tex[begin:]
        return bib_tex



def checkFile(filename,**kwargs):
    '''
    :Purpose: Checks if a spectrum file exists in the SPLAT's library.
    :param filename: A string containing the spectrum's filename.
    :Example:
       >>> import splat
       >>> spectrum1 = 'spex_prism_1315+2334_110404.fits'
       >>> print splat.checkFile(spectrum1)
       True
       >>> spectrum2 = 'fake_name.fits'
       >>> print splat.checkFile(spectrum2)
       False
    '''
    url = kwargs.get('url',splat.SPLAT_URL)+DATA_FOLDER
    return requests.get(url+filename).status_code == requests.codes.ok
#    flag = checkOnline()
#    if (flag):
#        try:
#            r = requests.get(url+filename)
#            open(os.path.basename(filename), 'wb').write(r.content)
#            open(os.path.basename(filename), 'wb').write(urllib2.urlopen(url+filename).read())
#        except:
#            flag = False
#    return flag


def checkAccess(**kwargs):
    '''
    :Purpose: Checks if user has access to unpublished spectra in SPLAT library.
    :Example:
       >>> import splat
       >>> print splat.checkAccess()
       True
    :Note: Must have the file .splat_access in your home directory with the correct passcode to use.
    '''
    access_file = '.splat_access'
    result = False

    try:
        home = os.path.expanduser("~")
        if home == None:
            home = './'
        bcode = requests.get(splat.SPLAT_URL+access_file).content
        lcode = base64.b64encode(open(home+'/'+access_file,'r').read().encode())
        if (bcode in lcode):        # changed to partial because of EOL variations
            result = True
    except:
        result = False

    if (kwargs.get('report','') != ''):
        if result == True:
            print('You have full access to all SPLAT data')
        else:
            print('You have access only to published data')
    return result


def checkLocal(inputfile):
    '''
    :Purpose: Checks if a file is present locally or within the SPLAT
                code directory
    :Example:
       >>> import splat
       >>> splat.checkLocal('splat.py')
       True  # found the code
       >>> splat.checkLocal('parameters.txt')
       False  # can't find this file
       >>> splat.checkLocal('SpectralModels/BTSettl08/parameters.txt')
       True  # found it
    '''
    if not os.path.exists(inputfile):
        if not os.path.exists(splat.SPLAT_PATH+inputfile):
            return ''
        else:
            return splat.SPLAT_PATH+inputfile
    else:
        return inputfile



def checkOnline(*args):
    '''
    :Purpose: Checks if SPLAT's URL is accessible from your machine--
                that is, checks if you and the host are online. Alternately
                checks if a given filename is present locally or online
    :Example:
       >>> import splat
       >>> splat.checkOnline()
       True  # SPLAT's URL was detected.
       >>> splat.checkOnline()
       False # SPLAT's URL was not detected.
       >>> splat.checkOnline('SpectralModels/BTSettl08/parameters.txt')
       '' # Could not find this online file.
    '''
    if (len(args) != 0):
        if 'http://' in args[0]:
            if requests.get(args[0]).status_code == requests.codes.ok:
                return args[0]
            return False
        else:
            if requests.get(splat.SPLAT_URL+args[0]).status_code == requests.codes.ok:
                return splat.SPLAT_URL+args[0]
            return False
    else:
        return requests.get(splat.SPLAT_URL).status_code == requests.codes.ok



def checkOnlineFile(*args):
    '''
    :Purpose: Checks if SPLAT's URL is accessible from your machine--
                that is, checks if you and the host are online. Alternately
                checks if a given filename is present locally or online
    :Example:
       >>> import splat
       >>> splat.checkOnlineFile('SpectralModels/BTSettl08/parameters.txt')
       '' # Could not find this online file.
       >>> splat.checkOnlineFile()
       '' # SPLAT's URL was not detected; you are not online.
    '''
    if (len(args) != 0):
        if 'http://' in args[0]:
            if requests.get(args[0]).status_code == requests.codes.ok:
                return args[0]
            return ''
        else:
            if requests.get(splat.SPLAT_URL+args[0]).status_code == requests.codes.ok:
                return splat.SPLAT_URL+args[0]
            return ''
    else:
        return requests.get(splat.SPLAT_URL).status_code == requests.codes.ok


def fetchDatabase(*args, **kwargs):
    '''
    :Purpose: Get the SpeX Database from either online repository or local drive
    '''
    filename = DB_ORIGINAL_FILE
    if len(args) > 0:
        filename = args[0]
    kwargs['filename'] = kwargs.get('filename',filename)
    kwargs['filename'] = kwargs.get('file',kwargs['filename'])
    kwargs['folder'] = kwargs.get('folder',DB_FOLDER)
    url = kwargs.get('url',splat.SPLAT_URL)+kwargs['folder']
    local = kwargs.get('local',True)
    online = kwargs.get('online',not local and checkOnline())
    local = not online
    kwargs['local'] = local
    kwargs['online'] = online
    kwargs['model'] = True
# determine format of file    
    delimiter = kwargs.get('delimiter','')
    fmt = kwargs.get('format','')
    fmt = kwargs.get('fmt',fmt)
    if delimiter == ',' or delimiter == 'comma' or delimiter == 'csv' or kwargs.get('comma',False) == True or ('.csv' in kwargs['filename']):
        delimiter = ','
        fmt = 'csv'
    if delimiter == '\t' or delimiter == 'tab' or kwargs.get('tab',False) == True or ('.txt' in kwargs['filename']):
        delimiter = '\t'
        fmt = 'tab'
    if fmt == '':
        raise NameError('\nCould not determine the file format of '+kwargs['filename']+'; please specify using format or delimiter keywords\n\n')


# check that folder/set is present either locally or online
# if not present locally but present online, switch to this mode
# if not present at either raise error
    folder = checkLocal(kwargs['folder'])
    if folder=='':
        folder = checkOnlineFile(kwargs['folder'])
        if folder=='':
            raise NameError('\nCould not find '+kwargs['folder']+' locally or on SPLAT website\n\n')
        else:
            kwargs['folder'] = folder
            kwargs['local'] = False
            kwargs['online'] = True
    else:
        kwargs['folder'] = folder

# locally:
    if kwargs['local']:
#        print('Reading local')
        infile = checkLocal(kwargs['filename'])
        if infile=='':
            infile = checkLocal(kwargs['folder']+'/'+kwargs['filename'])
        if infile=='':
            raise NameError('\nCould not find '+kwargs['filename']+' locally\n\n')
        else:
            try:
                data = ascii.read(infile, delimiter=delimiter,fill_values='-99.',format=fmt)
#                data = ascii.read(infile, delimiter='\t',fill_values='-99.',format='tab')
            except:
                raise NameError('\nCould not load {}: this may be a decoding error\n'.format(infile))


# check if file is present; if so, read it in, otherwise go to interpolated
# online:
    if kwargs['online']:
#        print('Reading online')
        infile = checkOnlineFile(kwargs['filename'])
        if infile=='':
            infile = checkOnlineFile(kwargs['folder']+'/'+kwargs['filename'])
        if infile=='':
            raise NameError('\nCould not find '+kwargs['filename']+' on the SPLAT website\n\n')
        try:
#            open(os.path.basename(TMPFILENAME), 'wb').write(urllib2.urlopen(url+infile).read())
            open(os.path.basename(TMPFILENAME), 'wb').write(requests.get(url+infile).content)
            kwargs['filename'] = os.path.basename(tmp)
            data = ascii.read(os.path.basename(TMPFILENAME), delimiter=delimiter,fill_values='-99.',format=fmt)
            os.remove(os.path.basename(TMPFILENAME))
        except:
            raise NameError('\nHaving a problem reading in '+kwargs['filename']+' on the SPLAT website\n\n')

    return data


def queryVizier(coordinate,**kwargs):
    return getPhotometry(coordinate,**kwargs)

def getPhotometry(coordinate,**kwargs):
    '''
    Purpose
        Downloads photometry for a source by coordinate using astroquery

    Required Inputs:
        :param: coordinate: Either an astropy SkyCoord or a variable that can be converted into a SkyCoord using `splat.properCoordinates()`_

    .. _`splat.properCoordinates()` : api.html#splat.properCoordinates
        
    Optional Inputs:
        :param radius: Search radius, nominally in arcseconds although this can be changed by passing an astropy.unit quantity (default = 30 arcseconds)
        :param catalog: Catalog to query, which can be set to the Vizier catalog identifier code or to one of the following preset catalogs:
            * '2MASS' (or set ``2MASS``=True): the 2MASS All-Sky Catalog of Point Sources (`Cutri et al. 2003 <http://adsabs.harvard.edu/abs/2003yCat.2246....0C>`_), Vizier id II/246
            * 'SDSS' (or set ``SDSS``=True): the The SDSS Photometric Catalog, Release 9 (`Adelman-McCarthy et al. 2012 <http://adsabs.harvard.edu/abs/2012ApJS..203...21A>`_), Vizier id V/139
            * 'WISE' (or set ``WISE``=True): the WISE All-Sky Data Release (`Cutri et al. 2012 <http://adsabs.harvard.edu/abs/2012yCat.2311....0C>`_), Vizier id II/311
            * 'ALLWISE' (or set ``ALLWISE``=True): the AllWISE Data Release (`Cutri et al. 2014 <http://adsabs.harvard.edu/abs/2014yCat.2328....0C>`_), Vizier id II/328
            * 'VISTA' (or set ``VISTA``=True): the VIKING catalogue data release 1 (`Edge et al. 2013 <http://adsabs.harvard.edu/abs/2013Msngr.154...32E>`_), Vizier id II/329
            * 'CFHTLAS' (or set ``CFHTLAS``=True): the CFHTLS Survey (T0007 release) by (`Hudelot et al. 2012 <http://adsabs.harvard.edu/abs/2012yCat.2317....0H>`_), Vizier id II/317
            * 'DENIS' (or set ``DENIS``=True): the DENIS DR3 (DENIS Consortium 2005), Vizier id B/denis/denis
            * 'UKIDSS' (or set ``UKIDSS``=True): the UKIDSS-DR8 LAS, GCS and DXS Surveys (`Lawrence et al. 2012 <http://adsabs.harvard.edu/abs/2007MNRAS.379.1599L>`_), Vizier id II/314
            * 'LEHPM' (or set ``LEHPM``=True): the Liverpool-Edinburgh High Proper Motion Catalogue (`Pokorny et al. 2004 <http://adsabs.harvard.edu/abs/2004A&A...421..763P>`_), Vizier id J/A+A/421/763
            * 'SIPS' (or set ``SIPS``=True): the Southern Infrared Proper Motion Survey (`Deacon et al 2005 <http://adsabs.harvard.edu/abs/2005A&A...435..363D>`_), Vizier id J/A+A/435/363
            * 'UCAC4' (or set ``UCAC4``=True): the UCAC4 Catalogue (`Zacharias et al. 2012 <http://adsabs.harvard.edu/abs/2012yCat.1322....0Z>`_), Vizier id I/322A
            * 'USNOB' (or set ``USNO``=True): the USNO-B1.0 Catalog (`Monet et al. 2003 <http://adsabs.harvard.edu/abs/2003AJ....125..984M>`_), Vizier id I/284
            * 'LSPM' (or set ``LSPM``=True): the LSPM-North Catalog (`Lepine et al. 2005 <http://adsabs.harvard.edu/abs/2005AJ....129.1483L>`_), Vizier id I/298
            * 'GAIA' (or set ``GAIA``=True): the GAIA DR1 Catalog (`Gaia Collaboration et al. 2016 <http://adsabs.harvard.edu/abs/2016yCat.1337....0G>`_), Vizier id I/337
        :param: sort: String specifying the parameter to sort the returned SIMBAD table by; by default this is the offset from the input coordinate (default = 'sep')
        :param: nearest: Set to True to return on the single nearest source to coordinate (default = False)
        :param: verbose: Give feedback (default = False)

    Output:
        An astropy Table instance that contains data from the Vizier query, or a blank Table if no sources are found

    Example:

    >>> import splat
    >>> from astropy import units as u
    >>> c = splat.properCoordinates('J053625-064302')
    >>> v = splat.querySimbad(c,catalog='SDSS',radius=15.*u.arcsec)
    >>> print(v)
      _r    _RAJ2000   _DEJ2000  mode q_mode  cl ... r_E_ g_J_ r_F_ i_N_  sep  
     arcs     deg        deg                     ... mag  mag  mag  mag   arcs 
    ------ ---------- ---------- ---- ------ --- ... ---- ---- ---- ---- ------
     7.860  84.105967  -6.715966    1          3 ...   --   --   --   --  7.860
    14.088  84.108113  -6.717206    1          6 ...   --   --   --   -- 14.088
    14.283  84.102528  -6.720843    1      +   6 ...   --   --   --   -- 14.283
    16.784  84.099524  -6.717878    1          3 ...   --   --   --   -- 16.784
    22.309  84.097988  -6.718049    1      +   6 ...   --   --   --   -- 22.309
    23.843  84.100079  -6.711999    1      +   6 ...   --   --   --   -- 23.843
    27.022  84.107504  -6.723965    1      +   3 ...   --   --   --   -- 27.022

    '''

# check if online
    if not checkOnline():
        print('\nYou are currently not online; cannot do a Vizier query')
        return Table()

# parameters
    radius = kwargs.get('radius',30.*u.arcsec)
    if not isinstance(radius,u.quantity.Quantity):
        radius*=u.arcsec
    verbose = kwargs.get('verbose',False)

# sort out what catalog to query
    catalog = kwargs.get('catalog','2MASS')
    if kwargs.get('2MASS',False) or kwargs.get('2mass',False) or catalog == '2MASS' or catalog == '2mass':
        catalog = u'II/246'
    if kwargs.get('SDSS',False) or kwargs.get('sdss',False) or catalog == 'SDSS' or catalog == 'sdss':
        catalog = u'V/139'
    if kwargs.get('WISE',False) or kwargs.get('wise',False) or catalog == 'WISE' or catalog == 'wise':
        catalog = u'II/311'
    if kwargs.get('ALLWISE',False) or kwargs.get('allwise',False) or catalog == 'ALLWISE' or catalog == 'allwise':
        catalog = u'II/328'
    if kwargs.get('VISTA',False) or kwargs.get('vista',False) or catalog == 'VISTA' or catalog == 'vista':
        catalog = u'II/329'
    if kwargs.get('CFHT',False) or kwargs.get('cfht',False) or kwargs.get('CFHTLAS',False) or kwargs.get('cfhtlas',False) or catalog == 'CFHT' or catalog == 'cfht':
        catalog = u'II/317'
    if kwargs.get('DENIS',False) or kwargs.get('denis',False) or catalog == 'DENIS' or catalog == 'denis':
        catalog = u'B/denis'
    if kwargs.get('UKIDSS',False) or kwargs.get('ukidss',False) or catalog == 'UKIDSS' or catalog == 'ukidss':
        catalog = u'II/314'
    if kwargs.get('LEHPM',False) or kwargs.get('lehpm',False) or catalog == 'LEHPM' or catalog == 'lehpm':
        catalog = u'J/A+A/421/763'
    if kwargs.get('SIPS',False) or kwargs.get('sips',False) or catalog == 'SIPS' or catalog == 'sips':
        catalog = u'J/A+A/435/363'
    if kwargs.get('UCAC',False) or kwargs.get('ucac',False) or kwargs.get('UCAC4',False) or kwargs.get('ucac4',False) or catalog == 'UCAC' or catalog == 'ucac':
        catalog = u'I/322A'
    if kwargs.get('USNO',False) or kwargs.get('usno',False) or kwargs.get('USNOB',False) or kwargs.get('usnob',False) or kwargs.get('USNOB1.0',False) or kwargs.get('usnob1.0',False) or catalog == 'USNO' or catalog == 'usno':
        catalog = u'I/284'
    if kwargs.get('LSPM',False) or kwargs.get('lspm',False) or kwargs.get('LSPM-NORTH',False) or kwargs.get('lspm-north',False) or kwargs.get('LSPM-N',False) or kwargs.get('lspm-n',False) or catalog == 'LSPM' or catalog == 'lspm':
        catalog = u'I/298'
    if kwargs.get('GAIA',False) or kwargs.get('gaia',False) or kwargs.get('GAIA-DR1',False):
        catalog = u'I/337'

# convert coordinate if necessary
    if not isinstance(coordinate,SkyCoord):
        try:
            c = splat.properCoordinates(coordinate)
        except:
            print('\n{} is not a proper coordinate'.format(coordinate))
            return numpy.nan
    else:
        c = copy.deepcopy(coordinate)

# search Vizier, sort by separation        
    v = Vizier(columns=["*", "+_r"], catalog=catalog)
    t_vizier = v.query_region(c,radius=radius)
    if len(t_vizier) > 0:
        tv=t_vizier[0]
    else:
        tv = t_vizier

# sorting
    if len(tv) > 1:
        tv['sep'] = tv['_r']
        sortparam = kwargs.get('sort','sep')
        if sortparam in list(tv.keys()):
            tv.sort(sortparam)
        else:
            if verbose:
                print('\nCannot find sorting keyword {}; try using {}\n'.format(sort,list(tv.keys())))

# return only nearest
    if kwargs.get('nearest',False) == True:
        while len(tv) > 1:
            tv.remove_row(1)

    return tv


def keySource(keys, **kwargs):
    '''
    :Purpose: Takes a source key and returns a table with the source information
    :param keys: source key or a list of source keys
    :Example:
    >>> import splat
    >>> print splat.keySource(10001)
        SOURCE_KEY           NAME              DESIGNATION    ... NOTE SELECT
        ---------- ------------------------ ----------------- ... ---- ------
             10001 SDSS J000013.54+255418.6 J00001354+2554180 ...        True
    >>> print splat.keySource([10105, 10623])
        SOURCE_KEY          NAME             DESIGNATION    ... NOTE SELECT
        ---------- ---------------------- ----------------- ... ---- ------
             10105 2MASSI J0103320+193536 J01033203+1935361 ...        True
             10623 SDSS J09002368+2539343 J09002368+2539343 ...        True
    >>> print splat.keySource(1000001)
        No sources found with source key 1000001
        False
    '''

# vectorize
    if isinstance(keys,list) == False:
        keys = [keys]

#    sdb = ascii.read(splat.SPLAT_PATH+DB_FOLDER+SOURCES_DB, delimiter='\t',fill_values='-99.',format='tab')
#    sdb = fetchDatabase(splat.SPLAT_PATH+DB_FOLDER+SOURCES_DB)
    sdb = copy.deepcopy(splat.DB_SOURCES)
    sdb['SELECT'] = [x in keys for x in sdb['SOURCE_KEY']]

    if sum(sdb['SELECT']) == 0.:
        print('No sources found with source key {}'.format(keys[0]))
        return False
    else:
        db = sdb[:][numpy.where(sdb['SELECT']==1)]
        return db


def keySpectrum(keys, **kwargs):
    '''
    :Purpose: Takes a spectrum key and returns a table with the spectrum and source information
    :param keys: spectrum key or a list of source keys
    :Example:
    >>> import splat
    >>> print splat.keySpectrum(10001)
        DATA_KEY SOURCE_KEY    DATA_FILE     ... COMPANION COMPANION_NAME NOTE_2
        -------- ---------- ---------------- ... --------- -------------- ------
           10001      10443 10001_10443.fits ...
    >>> print splat.keySpectrum([10123, 11298])
        DATA_KEY SOURCE_KEY    DATA_FILE     ... COMPANION COMPANION_NAME NOTE_2
        -------- ---------- ---------------- ... --------- -------------- ------
           11298      10118 11298_10118.fits ...
           10123      10145 10123_10145.fits ...
    >>> print splat.keySpectrum(1000001)
        No spectra found with spectrum key 1000001
        False
    '''

    verbose = kwargs.get('verbose',False)

# vectorize
    if isinstance(keys,list) == False:
        keys = [keys]

#    sdb = ascii.read(splat.SPLAT_PATH+DB_FOLDER+SPECTRA_DB, delimiter='\t',fill_values='-99.',format='tab')
#    sdb = fetchDatabase(splat.SPLAT_PATH+DB_FOLDER+SPECTRA_DB)
    sdb = copy.deepcopy(splat.DB_SPECTRA)
    sdb['SELECT'] = [x in keys for x in sdb['DATA_KEY']]

    if sum(sdb['SELECT']) == 0.:
        if verbose: print('No spectra found with spectrum key {}'.format(keys[0]))
        return False
    else:
#        s2db = ascii.read(splat.SPLAT_PATH+DB_FOLDER+SOURCES_DB, delimiter='\t',fill_values='-99.',format='tab')
#        s2db = fetchDatabase(splat.SPLAT_PATH+DB_FOLDER+SOURCES_DB)
        s2db = copy.deepcopy(splat.DB_SOURCES)
        db = join(sdb[:][numpy.where(sdb['SELECT']==1)],s2db,keys='SOURCE_KEY')
        return db



def searchLibrary(*args, **kwargs):
    '''
    :Purpose: Search the SpeX database to extract the key reference for that Spectrum

    :param optional name: search by source name (e.g., ``name = 'Gliese 570D'``)
    :param optional shortname: search be short name (e.g. ``shortname = 'J1457-2124'``)
    :param optional designation: search by full designation (e.g., ``designation = 'J11040127+1959217'``)
    :param optional coordinate: search around a coordinate by a radius specified by radius keyword (e.g., ``coordinate = [180.,+30.], radius = 10.``)
    :param radius: search radius in arcseconds for coordinate search
    :type radius: optional, default = 10
    :param optional spt: search by SpeX spectral type; single value is exact, two-element array gives range (e.g., ``spt = 'M7'`` or ``spt = [24,39]``)
    :param optional spex_spt: same as ``spt``
    :param optional opt_spt: same as ``spt`` for literature optical spectral types
    :param optional nir_spt: same as ``spt`` for literature NIR spectral types
    :param optional jmag, hmag, kmag: select based on faint limit or range of J, H or Ks magnitudes (e.g., ``jmag = [12,15]``)
    :param optional snr: search on minimum or range of S/N ratios (e.g., ``snr = 30.`` or ``snr = [50.,100.]``)
    :param optional subdwarf, young, binary, spbinary, red, blue, giant, wd, standard: classes to search on (e.g., ``young = True``)
    :param logic: search logic, can be ``and`` or ``or``
    :type logic: optional, default = 'and'
    :param combine: same as logic
    :type combine: optional, default = 'and'
    :param optional date: search by date (e.g., ``date = '20040322'``) or range of dates (e.g., ``date=[20040301,20040330]``)
    :param optional reference: search by list of references (bibcodes) (e.g., ``reference = '2011ApJS..197...19K'``)
    :param sort: sort results based on Right Ascension
    :type sort: optional, default = True
    :param list: if True, return just a list of the data files (can be done with searchLibrary as well)
    :type list: optional, default = False
    :param lucky: if True, return one randomly selected spectrum from the selected sample
    :type lucky: optional, default = False


    :param output: returns desired output of selected results
    :type output: optional, default = 'all'
    :param logic: search logic, can be and`` or ``or``
    :type logic: optional, default = 'and'
    :param combine: same as logic
    :type combine: optional, default = 'and'
    :Example:
    >>> import splat
    >>> print SearchLibrary(shortname = '2213-2136')
        DATA_KEY SOURCE_KEY    DATA_FILE     ... SHORTNAME  SELECT_2
        -------- ---------- ---------------- ... ---------- --------
           11590      11586 11590_11586.fits ... J2213-2136      1.0
           11127      11586 11127_11586.fits ... J2213-2136      1.0
           10697      11586 10697_11586.fits ... J2213-2136      1.0
           10489      11586 10489_11586.fits ... J2213-2136      1.0
    >>> print SearchLibrary(shortname = '2213-2136', output = 'OBSERVATION_DATE')
        OBSERVATION_DATE
        ----------------
                20110908
                20080829
                20060902
                20051017

    .. note:: Note that this is currently only and AND search - need to figure out how to a full SQL style search
    '''

# program parameters
    ref = kwargs.get('output','all')
    radius = kwargs.get('radius',10.)      # search radius in arcseconds
    classes = ['YOUNG','SUBDWARF','BINARY','SPBINARY','RED','BLUE','GIANT','WD','STANDARD','COMPANION']
    verbose = kwargs.get('verbose',False)

# logic of search
    logic = 'and'         # default combination
    logic = kwargs.get('combine',logic).lower()
    logic = kwargs.get('logic',logic).lower()
    if (logic != 'and' and logic != 'or'):
        raise ValueError('\nLogical operator '+logic+' not supported\n\n')

# read in source database and add in shortnames and skycoords
#    source_db = ascii.read(splat.SPLAT_PATH+DB_FOLDER+SOURCES_DB, delimiter='\t', fill_values='-99.', format='tab')
#    source_db = fetchDatabase(SOURCES_DB)
    source_db = copy.deepcopy(splat.DB_SOURCES)
    if 'SHORTNAME' not in source_db.keys():
        source_db['SHORTNAME'] = [splat.designationToShortName(x) for x in source_db['DESIGNATION']]

# first search by source parameters
    source_db['SELECT'] = numpy.zeros(len(source_db['RA']))
    count = 0.

# search by source key
    idkey = kwargs.get('sourcekey',False)
    idkey = kwargs.get('source',idkey)
    idkey = kwargs.get('idkey',idkey)
    idkey = kwargs.get('id',idkey)
    if idkey != False:
        if not isinstance(idkey,list):
            idkey = [idkey]
        if isinstance(idkey[0],str):
            idkey = [int(i) for i in idkey]
        for s in idkey:
            source_db['SELECT'][numpy.where(source_db['SOURCE_KEY'] == s)] += 1
        count+=1.
# search by name
    if kwargs.get('name',False) != False:
        nm = kwargs['name']
        if isinstance(nm,str):
            nm = [nm]
        for n in nm:
            source_db['SELECT'][numpy.where(source_db['NAME'] == n)] += 1
        count+=1.
# search by shortname
    if kwargs.get('shortname',False) != False:
        sname = kwargs['shortname']
        if isinstance(sname,str):
            sname = [sname]
        for sn in sname:
            if sn[0].lower() != 'j':
                sn = 'J'+sn
            source_db['SELECT'][numpy.where(source_db['SHORTNAME'] == sn)] += 1
        count+=1.
# exclude by shortname
    sname = kwargs.get('excludesource',False)
    sname = kwargs.get('excludeshortname',sname)
    if sname != False and len(sname) > 0:
        if isinstance(sname,str):
            sname = [sname]
        for sn in sname:
            if sn[0].lower() != 'j':
                sn = 'J'+sn
#            t = numpy.sum(source_db['SELECT'][numpy.where(source_db['SHORTNAME'] != sn)])
            source_db['SELECT'][numpy.where(source_db['SHORTNAME'] != sn)] += 1
#            if numpy.sum(source_db['SELECT'][numpy.where(source_db['SHORTNAME'] != sn)]) > t:
#                print('rejected '+sn)
        count+=1.
# search by reference list
    if kwargs.get('reference',False) != False:
        refer = kwargs['reference']
        if isinstance(ref,str):
            refer = [refer]
        for r in refer:
            source_db['SELECT'][numpy.where(source_db['DISCOVERY_REFERENCE'] == r)] += 1
        count+=1.
# search by designation
    if kwargs.get('designation',False) != False:
        desig = kwargs['designation']
        if isinstance(desig,str):
            desig = [desig]
        for d in desig:
            source_db['SELECT'][numpy.where(source_db['DESIGNATION'] == d)] += 1
        count+=1.
# search by coordinate - NOTE: THIS IS VERY SLOW RIGHT NOW
    if kwargs.get('coordinate',False) != False:
        print('\nWarning, search by coordinates may take a few minutes\n')
        coord = kwargs['coordinate']
        if isinstance(coord,SkyCoord):
            cc = coord
        else:
            cc = splat.properCoordinates(coord)
# calculate skycoords
        if 'SKYCOORD' not in source_db.keys():
            s = []
            for i in numpy.arange(len(source_db['RA'])):
                try:        # to deal with a blank string
                    s.append(SkyCoord(ra=float(source_db['RA'][i])*u.degree,dec=float(source_db['DEC'][i])*u.degree,frame='icrs'))
                except:
                    s.append(SkyCoord(ra=numpy.nan*u.degree,dec=numpy.nan*u.degree,frame='icrs'))
#                if numpy.mod(i,len(source_db['RA'])/10.) < 1 and i != 0:
#                    print('\b{:.0f}%...'.format(100*i/len(source_db['RA'])))
            source_db['SKYCOORD'] = s
#        print('measuring separations')
#        source_db['SEPARATION'] = [cc.separation(source_db['SKYCOORDS'][i]).arcsecond for i in numpy.arange(len(source_db['SKYCOORDS']))]
        source_db['SEPARATION'] = [cc.separation(c).arcsecond for c in source_db['SKYCOORD']]
#        print('done')
        source_db['SELECT'][numpy.where(source_db['SEPARATION'] <= radius)] += 1
        count+=1.
#        print(count,numpy.max(source_db['SELECT']))

# search by spectral type
    spt_range = kwargs.get('spt_range',False)
    spt_range = kwargs.get('spt',spt_range)
    spt_type = kwargs.get('spt_type','LIT_TYPE')
    if spt_range != False:
        if spt_type not in ['LIT_TYPE','SPEX_TYPE','OPT_TYPE','NIR_TYPE']:
            spt_type = 'LIT_TYPE'
        if not isinstance(spt_range,list):        # one value = only this type
            spt_range = [spt_range,spt_range]
        if isinstance(spt_range[0],str):          # convert to numerical spt
            spt_range = [splat.typeToNum(spt_range[0]),splat.typeToNum(spt_range[1])]
        source_db['SPTN'] = [splat.typeToNum(x) for x in source_db[spt_type]]
        source_db['SELECT'][numpy.where(numpy.logical_and(source_db['SPTN'] >= spt_range[0],source_db['SPTN'] <= spt_range[1]))] += 1
        count+=1.

# search by magnitude range
    if kwargs.get('jmag',False) != False:
        mag = kwargs['jmag']
        if not isinstance(mag,list):        # one value = faint limit
            mag = [0,mag]
        source_db['JMAGN'] = [float('0'+x) for x in source_db['J_2MASS']]
        source_db['SELECT'][numpy.where(numpy.logical_and(source_db['JMAGN'] >= mag[0],source_db['JMAGN'] <= mag[1]))] += 1
        count+=1.
    if kwargs.get('hmag',False) != False:
        mag = kwargs['hmag']
        if not isinstance(mag,list):        # one value = faint limit
            mag = [0,mag]
        source_db['HMAGN'] = [float('0'+x) for x in source_db['H_2MASS']]
        source_db['SELECT'][numpy.where(numpy.logical_and(source_db['HMAGN'] >= mag[0],source_db['HMAGN'] <= mag[1]))] += 1
        count+=1.
    if kwargs.get('kmag',False) != False:
        mag = kwargs['kmag']
        if not isinstance(mag,list):        # one value = faint limit
            mag = [0,mag]
        source_db['KMAGN'] = [float('0'+x) for x in source_db['KS_2MASS']]
        source_db['SELECT'][numpy.where(numpy.logical_and(source_db['KMAGN'] >= mag[0],source_db['KMAGN'] <= mag[1]))] += 1
        count+=1.

# young
    if (kwargs.get('young','') != ''):
        source_db['YOUNG'] = [i != '' for i in source_db['GRAVITY_CLASS_OPTICAL']] or [i != '' for i in source_db['GRAVITY_CLASS_NIR']]
        source_db['SELECT'][numpy.where(source_db['YOUNG'] == kwargs.get('young'))] += 1
        count+=1.

# specific gravity class
    flag = kwargs.get('gravity_class','')
    flag = kwargs.get('gravity',flag)
    if (flag != ''):
        source_db['SELECT'][numpy.where(source_db['GRAVITY_CLASS_OPTICAL'] == flag)] += 1
        source_db['SELECT'][numpy.where(source_db['GRAVITY_CLASS_NIR'] == flag)] += 1
        count+=1.

# specific cluster
    if (kwargs.get('cluster','') != '' and isinstance(kwargs.get('cluster'),str)):
        source_db['CLUSTER_FLAG'] = [i.lower() == kwargs.get('cluster').lower() for i in source_db['CLUSTER']]
        source_db['SELECT'][numpy.where(source_db['CLUSTER_FLAG'] == True)] += 1
        count+=1.

# giant
    if (kwargs.get('giant','') != ''):
#        kwargs['vlm'] = False
        source_db['GIANT'] = [i != '' for i in source_db['LUMINOSITY_CLASS']]
        source_db['SELECT'][numpy.where(source_db['GIANT'] == kwargs.get('giant'))] += 1
        count+=1.

# luminosity class
    if (kwargs.get('giant_class','') != ''):
        if 'GIANT' not in source_db.keys():
            source_db['GIANT'] = [i != '' for i in source_db['LUMINOSITY_CLASS']]
        source_db['GIANT_FLAG'] = [i.lower() == kwargs.get('giant_class').lower() for i in source_db['GIANT']]
        source_db['SELECT'][numpy.where(source_db['GIANT_FLAG'] == True)] += 1
        count+=1.

# subdwarf
    if (kwargs.get('subdwarf','') != ''):
        source_db['SUBDWARF'] = [i != '' for i in source_db['METALLICITY_CLASS']]
        source_db['SELECT'][numpy.where(source_db['SUBDWARF'] == kwargs.get('subdwarf'))] += 1
        count+=1.

# metallicity class
    if (kwargs.get('subdwarf_class','') != ''):
        source_db['SD_FLAG'] = [i.lower() == kwargs.get('subdwarf_class').lower() for i in source_db['METALLICITY_CLASS']]
        source_db['SELECT'][numpy.where(source_db['SD_FLAG'] == True)] += 1
        count+=1.

# red - THIS NEEDS TO BE CHANGED
    if (kwargs.get('red','') != ''):
        source_db['RED'] = ['red' in i for i in source_db['LIBRARY']]
        source_db['SELECT'][numpy.where(source_db['RED'] == kwargs.get('red'))] += 1
        count+=1.

# blue - THIS NEEDS TO BE CHANGED
    if (kwargs.get('blue','') != ''):
        source_db['BLUE'] = ['blue' in i for i in source_db['LIBRARY']]
        source_db['SELECT'][numpy.where(source_db['BLUE'] == kwargs.get('blue'))] += 1
        count+=1.

# binaries
    if (kwargs.get('binary','') != ''):
        source_db['BINARY_FLAG'] = [i == 'Y' for i in source_db['BINARY']]
        source_db['SELECT'][numpy.where(source_db['BINARY_FLAG'] == kwargs.get('binary'))] += 1
        count+=1.

# spectral binaries
    if (kwargs.get('sbinary','') != ''):
        source_db['SBINARY_FLAG'] = [i == 'Y' for i in source_db['SBINARY']]
        source_db['SELECT'][numpy.where(source_db['SBINARY_FLAG'] == kwargs.get('sbinary'))] += 1
        count+=1.

# companions
    if (kwargs.get('companion','') != ''):
        source_db['COMPANION_FLAG'] = [i != '' for i in source_db['COMPANION_NAME']]
        source_db['SELECT'][numpy.where(source_db['COMPANION_FLAG'] == kwargs.get('companion'))] += 1
        count+=1.

# white dwarfs
    if (kwargs.get('wd','') != ''):
        kwargs['vlm'] = False
        source_db['WHITEDWARF'] = [i == 'WD' for i in source_db['OBJECT_TYPE']]
        source_db['SELECT'][numpy.where(source_db['WHITEDWARF'] == kwargs.get('wd'))] += 1
        count+=1.

# galaxies
    if (kwargs.get('galaxy','') != ''):
        kwargs['vlm'] = False
        source_db['GALAXY'] = [i == 'GAL' for i in source_db['OBJECT_TYPE']]
        source_db['SELECT'][numpy.where(source_db['GALAXY'] == kwargs.get('galaxy'))] += 1
        count+=1.

# carbon stars
    if (kwargs.get('carbon','') != ''):
        kwargs['vlm'] = False
        source_db['CARBON'] = [i == 'C' for i in source_db['OBJECT_TYPE']]
        source_db['SELECT'][numpy.where(source_db['CARBON'] == kwargs.get('carbon'))] += 1
        count+=1.

# peculiars
    if (kwargs.get('peculiar','') != ''):
#        kwargs['vlm'] = False
        source_db['PECULIAR'] = ['p' in i for i in source_db['LIT_TYPE']]
        source_db['SELECT'][numpy.where(source_db['PECULIAR'] == kwargs.get('peculiar'))] += 1
        count+=1.

# VLM dwarfs
    if (kwargs.get('vlm','') != ''):
        if (kwargs.get('vlm') == True):
            source_db['SELECT'][numpy.where(source_db['OBJECT_TYPE'] == 'VLM')] += 1
            count+=1.
        if (kwargs.get('vlm') == False):
            source_db['SELECT'][numpy.where(source_db['OBJECT_TYPE'] != 'VLM')] += 1
            count+=1.

# select source keys
    if (count > 0):
        if (logic == 'and'):
            source_db['SELECT'] = numpy.floor(source_db['SELECT']/count)
        elif (logic == 'or'):
            source_db['SELECT'] = numpy.ceil(source_db['SELECT']/count)

        source_keys = source_db['SOURCE_KEY'][numpy.where(source_db['SELECT']==1)]
# no selection made on sources - choose everything
    else:
        source_keys = source_db['SOURCE_KEY']

#    print(count,numpy.max(source_db['SELECT']),len(source_db[:][numpy.where(source_db['SELECT']==1)]),len(source_keys))


# read in spectral database
#    spectral_db = ascii.read(splat.SPLAT_PATH+DB_FOLDER+SPECTRA_DB, delimiter='\t',fill_values='-99.',format='tab')
#    spectral_db = fetchDatabase(splat.SPLAT_PATH+DB_FOLDER+SPECTRA_DB)
    spectral_db = copy.deepcopy(splat.DB_SPECTRA)
# having to force dtype here so SELECT remains an integer
    spectral_db['SELECT'] = Table.Column(numpy.zeros(len(spectral_db['DATA_KEY'])),dtype=int)
    count = 0.

    spectral_db['SOURCE_SELECT'] = [x in source_keys for x in spectral_db['SOURCE_KEY']]
#    print(spectral_db['SOURCE_KEY'][numpy.where(spectral_db['SOURCE_SELECT']==True)])

# search by filename
    file = kwargs.get('file','')
    file = kwargs.get('filename',file)
    if (file != ''):
        if isinstance(file,str):
            file = [file]
        for f in file:
            spectral_db['SELECT'][numpy.where(spectral_db['DATA_FILE'] == f)] += 1
        count+=1.

# exclude by data key
    if kwargs.get('excludekey',False) != False:
        exkey = kwargs['excludekey']
        if len(exkey) > 0:
            if isinstance(exkey,str):
                exkey = [exkey]
            for f in exkey:
                spectral_db['SELECT'][numpy.where(spectral_db['DATA_KEY'] != f)] += 1
            count+=1.

# exclude by filename
    if kwargs.get('excludefile',False) != False:
        file = kwargs['excludefile']
        if len(file) > 0:
            if isinstance(file,str):
                file = [file]
            for f in file:
                spectral_db['SELECT'][numpy.where(spectral_db['DATA_FILE'] != f)] += 1
            count+=1.

# search by observation date range
    if kwargs.get('date',False) != False:
        date = kwargs['date']
        if isinstance(date,str) or isinstance(date,long) or isinstance(date,float) or isinstance(date,int):
            date = [float(date),float(date)]
        elif isinstance(date,list):
            date = [float(date[0]),float(date[-1])]
        else:
            raise ValueError('\nCould not parse date input {}\n\n'.format(date))
        spectral_db['DATEN'] = [float(x) for x in spectral_db['OBSERVATION_DATE']]
        spectral_db['SELECT'][numpy.where(numpy.logical_and(spectral_db['DATEN'] >= date[0],spectral_db['DATEN'] <= date[1]))] += 1
        count+=1.

# search by S/N range
    if kwargs.get('snr',False) != False:
        snr = kwargs['snr']
        if not isinstance(snr,list):        # one value = minimum S/N
            snr = [float(snr),1.e9]
        spectral_db['SNRN'] = [float('0'+x) for x in spectral_db['MEDIAN_SNR']]
        spectral_db['SELECT'][numpy.where(numpy.logical_and(spectral_db['SNRN'] >= snr[0],spectral_db['SNRN'] <= snr[1]))] += 1
        count+=1.

# combine selection logically
    if (count > 0):
        if (logic == 'and'):
            spectral_db['SELECT'] = numpy.floor(spectral_db['SELECT']/count)
        else:
            spectral_db['SELECT'] = numpy.ceil(spectral_db['SELECT']/count)

    else:
        spectral_db['SELECT'] = numpy.ones(len(spectral_db['DATA_KEY']))


# limit access to public data for most users
#    print(count,numpy.max(spectral_db['SOURCE_SELECT']),numpy.max(spectral_db['SELECT']))
#    print(len(spectral_db[:][numpy.where(spectral_db['SELECT']==1)]))
#    print(len(spectral_db[:][numpy.where(spectral_db['SOURCE_SELECT']==True)]))
#    print(len(spectral_db[:][numpy.where(numpy.logical_and(spectral_db['SELECT']==1,spectral_db['SOURCE_SELECT']==True))]))
    if (not splat.checkAccess() or kwargs.get('published',False) or kwargs.get('public',False)):
        spectral_db['SELECT'][numpy.where(spectral_db['PUBLISHED'] != 'Y')] = 0.

#    print(spectral_db['SOURCE_KEY'][numpy.where(spectral_db['SELECT']==1)])
#    print(spectral_db['SOURCE_KEY'][numpy.where(spectral_db['SOURCE_SELECT']==True)])

# no matches
#    print(count,numpy.max(spectral_db['SOURCE_SELECT']),numpy.max(spectral_db['SELECT']))
#    print(len(spectral_db[:][numpy.where(spectral_db['SELECT']==1)]))
#    print(len(spectral_db[:][numpy.where(spectral_db['SOURCE_SELECT']==True)]))
#    print(len(spectral_db[:][numpy.where(numpy.logical_and(spectral_db['SELECT']==1,spectral_db['SOURCE_SELECT']==True))]))
    if len(spectral_db[:][numpy.where(numpy.logical_and(spectral_db['SELECT']==1,spectral_db['SOURCE_SELECT']==True))]) == 0:
        if verbose: print('No spectra in the SPL database match the selection criteria')
        return Table()
    else:

# merge databases
#        print(numpy.sum(spectral_db['SELECT']), numpy.sum(spectral_db['SOURCE_SELECT']))
#        print(spectral_db[:][numpy.where(spectral_db['SELECT']==1)])
#        print(spectral_db['SELECT'][numpy.where(spectral_db['SOURCE_SELECT']==True)])
#        print(len(spectral_db[:][numpy.where(numpy.logical_and(spectral_db['SELECT']==1,spectral_db['SOURCE_SELECT']==True))]))
        db = join(spectral_db[:][numpy.where(numpy.logical_and(spectral_db['SELECT']==1,spectral_db['SOURCE_SELECT']==True))],source_db,keys='SOURCE_KEY')

        if (ref == 'all'):
            return db
        else:
            return db[ref]


def querySimbad(variable,**kwargs):
    '''
    Purpose
        Queries Simbad using astroquery to grab information about a source

    Required Inputs:
        :param: variable: Either an astropy SkyCoord object containing position of a source, a variable that can be converted into a SkyCoord using `splat.properCoordinates()`_, or a string name for a source.

    .. _`splat.properCoordinates()` : api.html#splat.properCoordinates
        
    Optional Inputs:
        :param: radius: Search radius, nominally in arcseconds although can be set by assigning and astropy.unit value (default = 30 arcseconds)
        :param: sort: String specifying the parameter to sort the returned SIMBAD table by; by default this is the offset from the input coordinate (default = 'sep')
        :param: reject_type: Set to string or list of strings to filter out object types not desired. Useful for crowded fields (default = None)
        :param: nearest: Set to True to return on the single nearest source to coordinate (default = False)
        :param: iscoordinate: Specifies that input is a coordinate of some kind (default = False)
        :param: isname: Specifies that input is a name of some kind (default = False)
        :param: clean: Set to True to clean the SIMBAD output and reassign to a predefined set of parameters (default = True)
        :param: verbose: Give lots of feedback (default = False)

    Output:
        An astropy Table instance that contains data from the SIMBAD search, or a blank Table if no sources found

    Example:

    >>> import splat
    >>> from astropy import units as u
    >>> c = splat.properCoordinates('J053625-064302')
    >>> q = splat.querySimbad(c,radius=15.*u.arcsec,reject_type='**')
    >>> print(q)
              NAME          OBJECT_TYPE     OFFSET    ... K_2MASS K_2MASS_E
    ----------------------- ----------- ------------- ... ------- ---------
               BD-06  1253B        Star  4.8443894429 ...                  
                [SST2010] 3        Star 5.74624887682 ...   18.36       0.1
                BD-06  1253         Ae* 7.74205447776 ...   5.947     0.024
               BD-06  1253A          ** 7.75783861347 ...                  
    2MASS J05362590-0643020     brownD* 13.4818185612 ...  12.772     0.026
    2MASS J05362577-0642541        Star  13.983717577 ...                  

    '''

# check that online
    if not checkOnline():
        print('\nYou are currently not online; cannot do a SIMBAD query')
        return Table()

# parameters 
    radius = kwargs.get('radius',30.*u.arcsec)
    if not isinstance(radius,u.quantity.Quantity):
        radius*=u.arcsec
    verbose = kwargs.get('verbose',False)
    coordFlag = kwargs.get('iscoordinate',False)
    nameFlag = kwargs.get('isname',False)

# check if this is a coordinate query
    if isinstance(variable,SkyCoord):
        c = copy.deepcopy(variable)
        coordFlag = True
    elif not nameFlag:
        try:
            c = splat.properCoordinates(variable)
            coordFlag = True
# this is probably a name
        except:
            nameFlag = True
    else:
        if isinstance(variable,unicode):
            c = variable.decode()
        else:
            c = str(variable)

# prep Simbad search
    sb = Simbad()
    votfields = ['otype','parallax','sptype','propermotions','rot','rvz_radvel','rvz_error',\
    'rvz_bibcode','fluxdata(B)','fluxdata(V)','fluxdata(R)','fluxdata(I)','fluxdata(g)','fluxdata(r)',\
    'fluxdata(i)','fluxdata(z)','fluxdata(J)','fluxdata(H)','fluxdata(K)']
    for v in votfields:
        sb.add_votable_fields(v)

# search SIMBAD by coordinate
    if coordFlag:
        t_sim = sb.query_region(c,radius=radius)
        if not isinstance(t_sim,Table):
            if verbose:
                print('\nNo sources found; returning empty Table\n')
            return Table()

# if more than one source, sort the results by separation
        sep = [c.separation(SkyCoord(str(t_sim['RA'][lp]),str(t_sim['DEC'][lp]),unit=(u.hourangle,u.degree))).arcsecond for lp in numpy.arange(len(t_sim))]
        t_sim['sep'] = sep

# search SIMBAD by name
    elif nameFlag:
        t_sim = sb.query_object(c,radius=radius)
        t_sim['sep'] = numpy.zeros(len(t_sim['RA']))

    else:
        raise ValueError('problem!')

# sort results by separation by default
    if kwargs.get('sort','sep') in list(t_sim.keys()):
        t_sim.sort(kwargs.get('sort','sep'))
    else:
        if verbose:
            print('\nCannot sort by {}; try keywords {}\n'.format(kwargs.get('sort','sep'),list(t_sim.keys())))


# reject object types not wanted
    if kwargs.get('reject_type',False) != False:
        rej = kwargs['reject_type']
        if not isinstance(rej,list):
            rej = [rej]
        for r in rej:
            w = numpy.array([str(r) not in str(o) for o in t_sim['OTYPE']])
            if len(w) > 0:
                t_sim = t_sim[w]

# trim to single source if nearest flag is set
    if coordFlag and kwargs.get('nearest',False):
        while len(t_sim)>1:
            t_sim.remove_row(1) 

# clean up the columns    
    if kwargs.get('clean',True) == True and len(t_sim) > 0:
        t_src = Table()
        if not isinstance(t_sim['MAIN_ID'][0],str):
            t_src['NAME'] = [x.decode().replace('  ',' ') for x in t_sim['MAIN_ID']]
        else: 
            t_src['NAME'] = t_sim['MAIN_ID']
        if not isinstance(t_sim['OTYPE'][0],str):
            t_src['OBJECT_TYPE'] = [x.decode().replace('  ',' ') for x in t_sim['OTYPE']]
        else:
            t_src['OBJECT_TYPE'] = t_sim['OTYPE']
        t_src['OFFSET'] = t_sim['sep']
        if not isinstance(t_sim['SP_TYPE'][0],str):
            t_src['LIT_SPT'] = [x.decode().replace(' ','') for x in t_sim['SP_TYPE']]
        else:
            t_src['LIT_SPT'] = t_sim['SP_TYPE']
        if not isinstance(t_sim['SP_BIBCODE'][0],str):
            t_src['LIT_SPT_REF'] = [x.decode() for x in t_sim['SP_BIBCODE']]
        else: 
            t_src['LIT_SPT_REF'] = t_sim['SP_BIBCODE']
        t_src['DESIGNATION'] = ['J{}{}'.format(t_sim['RA'][i],t_sim['DEC'][i]).replace(' ','').replace('.','') for i in range(len(t_sim))] 
        t_src['RA'] = numpy.zeros(len(t_sim))
        t_src['DEC'] = numpy.zeros(len(t_sim))
        for i in range(len(t_sim)):
            c2 = splat.properCoordinates(t_src['DESIGNATION'][i])
            t_src['RA'][i] = c2.ra.value
            t_src['DEC'][i] = c2.dec.value
        t_src['PARALLAX'] = [str(p).replace('--','') for p in t_sim['PLX_VALUE']]
        t_src['PARALLAX_E'] = [str(p).replace('--','') for p in t_sim['PLX_ERROR']]
        if not isinstance(t_sim['PLX_BIBCODE'][0],str):
            t_src['PARALLEX_REF'] = [x.decode() for x in t_sim['PLX_BIBCODE']]
        else:
            t_src['PARALLEX_REF'] = t_sim['PLX_BIBCODE']
        t_src['MU_RA'] = [str(p).replace('--','') for p in t_sim['PMRA']]
        t_src['MU_DEC'] = [str(p).replace('--','') for p in t_sim['PMDEC']]
        t_src['MU'] = numpy.zeros(len(t_sim))
        for i in range(len(t_sim)):
            if t_src['MU_RA'][i] != '':
                t_src['MU'][i] = (float(t_src['MU_RA'][i])**2+float(t_src['MU_DEC'][i])**2)**0.5
        t_src['MU_E'] = [str(p).replace('--','') for p in t_sim['PM_ERR_MAJA']]
        if not isinstance(t_sim['PM_BIBCODE'][0],str):
            t_src['MU_REF'] = [x.decode() for x in t_sim['PM_BIBCODE']]
        else:
            t_src['MU_REF'] = t_sim['PM_BIBCODE']
        t_src['RV'] = [str(p).replace('--','') for p in t_sim['RVZ_RADVEL']]
        t_src['RV_E'] = [str(p).replace('--','') for p in t_sim['RVZ_ERROR']]
        if not isinstance(t_sim['RVZ_BIBCODE'][0],str):
            t_src['RV_REF'] = [x.decode() for x in t_sim['RVZ_BIBCODE']]
        else:
            t_src['RV_REF'] = t_sim['RVZ_BIBCODE']
        t_src['VSINI'] = [str(p).replace('--','') for p in t_sim['ROT_Vsini']]
        t_src['VSINI_E'] = [str(p).replace('--','') for p in t_sim['ROT_err']]
        if not isinstance(t_sim['ROT_bibcode'][0],str):
            t_src['VSINI_REF'] = [x.decode() for x in t_sim['ROT_bibcode']]
        else:
            t_src['VSINI_REF'] = t_sim['ROT_bibcode']
        t_src['J_2MASS'] = [str(p).replace('--','') for p in t_sim['FLUX_J']]
        t_src['J_2MASS_E'] = [str(p).replace('--','') for p in t_sim['FLUX_ERROR_J']]
        t_src['H_2MASS'] = [str(p).replace('--','') for p in t_sim['FLUX_H']]
        t_src['H_2MASS_E'] = [str(p).replace('--','') for p in t_sim['FLUX_ERROR_H']]
        t_src['K_2MASS'] = [str(p).replace('--','') for p in t_sim['FLUX_K']]
        t_src['K_2MASS_E'] = [str(p).replace('--','') for p in t_sim['FLUX_ERROR_K']]
    else:
        t_src = t_sim.copy()

    return t_src



def _querySimbad2(t_src,**kwargs):
    '''
    Purpose
        Internal function that queries Simbad and populates data for source table.

    :Note:
        **this program is in beta testing; bugs/errors are likely**

    :Required parameters:
        :param table: an astropy Table object, requires the presence of DESIGNATION column

    :Optional parameters:
        :param simbad_radius = 30 arcseconds: circular radius to search for sources (note: must be an angular quantity)
        :param export = '': filename to which to export resulting table to; if equal to a null string then no expoer is made. Note that a populated table is returned in either case
        :param closest = False: return only the closest source to given coordinate
    '''    
# parameters 
    simbad_radius = kwargs.get('simbad_radius',30.*u.arcsec)
    verbose = kwargs.get('verbose',True)
# checks
    if 'DESIGNATION' not in t_src.keys():
        raise NameError('\nDESIGNATION column is required for input table to querySimbad\n')
    if 'SIMBAD_SEP' not in t_src.keys():
        t_src['SIMBAD_SEP'] = Column(numpy.zeros(len(t_src)),dtype='float')
# must be online
    if not checkOnline():
        print('\nYou are currently not online so cannot query Simbad\n')
        return t_src

# if necessary, populate columns that are expected for source database
    for c in splat.DB_SOURCES.keys():
        if c not in t_src.keys():
            t_src[c] = Column([' '*50 for des in t_src['DESIGNATION']],dtype='str')

# prep Simbad search
    sb = Simbad()
    votfields = ['otype','parallax','sptype','propermotions','rot','rvz_radvel','rvz_error',\
    'rvz_bibcode','fluxdata(B)','fluxdata(V)','fluxdata(R)','fluxdata(I)','fluxdata(g)','fluxdata(r)',\
    'fluxdata(i)','fluxdata(z)','fluxdata(J)','fluxdata(H)','fluxdata(K)']
    for v in votfields:
        sb.add_votable_fields(v)

# search by source
    for i,des in enumerate(t_src['DESIGNATION']):
        print(i,des)
        c = splat.designationToCoordinate(des)
        try:
            t_sim = sb.query_region(c,radius=simbad_radius)
        except:
            t_sim = None
# source found in query
        if isinstance(t_sim,Table):
# many sources found
#            if len(t_sim) >= 1:      # take the closest position
            if verbose:
                print('\nSource {} Designation = {} {} match(es)'.format(i+1,des,len(t_sim)))
                print(t_sim)

            sep = [c.separation(SkyCoord(str(t_sim['RA'][lp]),str(t_sim['DEC'][lp]),unit=(u.hourangle,u.degree))).arcsecond for lp in numpy.arange(len(t_sim))]
            t_sim['sep'] = sep
            t_sim.sort('sep')
            if len(t_sim) > 1:
                while len(t_sim)>1:
                    t_sim.remove_row(1) 
# one source found
#            else:
#                t_sim['sep'] = [c.separation(SkyCoord(str(t_sim['RA'][0]),str(t_sim['DEC'][0]),unit=(u.hourangle,u.degree))).arcsecond]

# fill in information
            t_src['SIMBAD_NAME'][i] = t_sim['MAIN_ID'][0]
            t_src['NAME'][i] = t_src['SIMBAD_NAME'][i]
            t_src['SIMBAD_OTYPE'][i] = t_sim['OTYPE'][0]
            if not isinstance(t_sim['SP_TYPE'][0],str):
                t_sim['SP_TYPE'][0] = t_sim['SP_TYPE'][0].decode()
            spt = t_sim['SP_TYPE'][0]
            spt.replace(' ','').replace('--','')
            t_src['SIMBAD_SPT'][i] = spt
            t_src['SIMBAD_SPT_REF'][i] = t_sim['SP_BIBCODE'][0]
            t_src['SIMBAD_SEP'][i] = t_sim['sep'][0]
            if spt != '':
                t_src['LIT_TYPE'][i] = t_src['SIMBAD_SPT'][i]
                t_src['LIT_TYPE_REF'][i] = t_src['SIMBAD_SPT_REF'][i]
            t_src['DESIGNATION'][i] = 'J{}{}'.format(t_sim['RA'][0],t_sim['DEC'][0]).replace(' ','').replace('.','')
            coord = splat.properCoordinates(t_src['DESIGNATION'][i])
            t_src['RA'][i] = coord.ra.value
            t_src['DEC'][i] = coord.dec.value
            t_src['OBJECT_TYPE'][i] = 'VLM'
            if 'I' in t_sim['SP_TYPE'][0] and 'V' not in t_sim['SP_TYPE'][0]:
                t_src['LUMINOSITY_CLASS'][i] = 'I{}'.format(t_sim['SP_TYPE'][0].split('I',1)[1])
                t_src['OBJECT_TYPE'][i] = 'GIANT'
            if 'VI' in t_sim['SP_TYPE'][0] or 'sd' in t_sim['SP_TYPE'][0]:
                t_src['METALLICITY_CLASS'][i] = '{}sd'.format(t_sim['SP_TYPE'][0].split('sd',1)[0])
            t_src['PARALLAX'][i] = str(t_sim['PLX_VALUE'][0]).replace('--','')
            t_src['PARALLAX_E'][i] = str(t_sim['PLX_ERROR'][0]).replace('--','')
            if isinstance(t_sim['PLX_BIBCODE'][0],str):
                t_src['PARALLEX_REF'][i] = str(t_sim['PLX_BIBCODE'][0]).replace('--','')
            else:
                t_src['PARALLEX_REF'][i] = t_sim['PLX_BIBCODE'][0].decode()
            t_src['MU_RA'][i] = str(t_sim['PMRA'][0]).replace('--','')
            t_src['MU_DEC'][i] = str(t_sim['PMDEC'][0]).replace('--','')
#                try:            # this is in case MU is not present
            t_src['MU'][i] = (float('{}0'.format(t_src['MU_RA'][i]))**2+float('{}0'.format(t_src['MU_DEC'][i]))**2)**0.5
            t_src['MU_E'][i] = str(t_sim['PM_ERR_MAJA'][0]).replace('--','')
#                except:
#                    pass
            t_src['MU_REF'][i] = t_sim['PM_BIBCODE'][0]
            t_src['RV'][i] = str(t_sim['RVZ_RADVEL'][0]).replace('--','')
            t_src['RV_E'][i] = str(t_sim['RVZ_ERROR'][0]).replace('--','')
            t_src['RV_REF'][i] = t_sim['RVZ_BIBCODE'][0]
            t_src['VSINI'][i] = str(t_sim['ROT_Vsini'][0]).replace('--','')
            t_src['VSINI_E'][i] = str(t_sim['ROT_err'][0]).replace('--','')
            t_src['VSINI_REF'][i] = t_sim['ROT_bibcode'][0]
            if isinstance(t_sim['FLUX_J'][0],str):
                t_src['J_2MASS'][i] = t_sim['FLUX_J'][0].replace('--','')
            else:
                t_src['J_2MASS'][i] = t_sim['FLUX_J'][0]
            if isinstance(t_sim['FLUX_ERROR_J'][0],str):
                t_src['J_2MASS_E'][i] = t_sim['FLUX_ERROR_J'][0].replace('--','')
            else:
                t_src['J_2MASS_E'][i] = t_sim['FLUX_ERROR_J'][0]
            if isinstance(t_sim['FLUX_H'][0],str):
                t_src['H_2MASS'][i] = t_sim['FLUX_H'][0].replace('--','')
            else:
                t_src['H_2MASS'][i] = t_sim['FLUX_H'][0]
            if isinstance(t_sim['FLUX_ERROR_H'][0],str):
                t_src['H_2MASS_E'][i] = t_sim['FLUX_ERROR_H'][0].replace('--','')
            else:
                t_src['H_2MASS_E'][i] = t_sim['FLUX_ERROR_H'][0]
            if isinstance(t_sim['FLUX_K'][0],str):
                t_src['KS_2MASS'][i] = t_sim['FLUX_K'][0].replace('--','')
            else:
                t_src['KS_2MASS'][i] = t_sim['FLUX_K'][0]
            if isinstance(t_sim['FLUX_ERROR_K'][0],str):
                t_src['KS_2MASS_E'][i] = t_sim['FLUX_ERROR_K'][0].replace('--','')
            else:
                t_src['KS_2MASS_E'][i] = t_sim['FLUX_ERROR_K'][0]

    return




def importSpectra(*args,**kwargs):
    '''
    Purpose
        imports a set of spectra into the SPLAT library; requires manager access.

    :Note:
        **this program is in beta testing; bugs/errors are likely**

    :Optional parameters:
        :param data_folder = "./": Full path to folder containing data; by default this is the current directory
        :param review_folder = "./review/": Full path to folder in which review materials will be kept; by default a new folder ``review`` will be created inside the data_folder
        :param spreadsheet = "": Filename for a spreadsheet (ascii, tab- or comma-delimited) listing the input spectra, one per row. At least one column must be named ``filename`` or ``file`` that contains the name of the data file; the following columns are also recommended:

            * ``designation``: source desigation; e.g., ``J15420830-2621138`` (strongly recommended)
            * ``ra`` and ``dec``: Right Ascension and declination in decimal format (only needed if no designation column provided)
            * ``name``: source name, designation will be used if not provided
            * ``type``, ``opt_type``, ``nir_type``: spectral type of source (string); ``type`` will default to ``lit_type``
            * ``date`` or ``observation_date``: date of observation in format YYYYMMDD
            * ``slit``: slit width used (for computing resolution)
            * ``airmass``: airmass of observation
            * ``observer``: last name of primary observer
            * ``data_reference``: bibcode of data reference

    :Output:
        - Source DB update file: spreadsheet containing update to source_data.txt, saved in review folder as source_data.txt
        - Spectral DB update file: spreadsheet containing update to spectral_data.txt, saved locally as UPDATE_spectral_data.txt
        - Photometry DB update file: spreadsheet containing update to photometry_data.txt, saved locally as UPDATE_photometry_data.txt

    '''
# check user access
    if splat.checkAccess() == False:
        print('\nSpectra may only be imported into library by designated manager or while online; please email {}'.format(splat.SPLAT_EMAIL))
        return

# check online
#    if splat.checkOnline() == False:
#        print('\nWarning! You are not currently online so you will not be able to retrieve SIMBAD and Vizier data\n')

# set up optional inputs
    simbad_radius = kwargs.get('simbad_radius',60.*u.arcsec)
    if isinstance(simbad_radius,u.quantity.Quantity) == False:
        simbad_radius*=u.arcsec

    vizier_radius = kwargs.get('vizier_radius',30.*u.arcsec)
    if isinstance(vizier_radius,u.quantity.Quantity) == False:
        vizier_radius*=u.arcsec

    data_folder = kwargs.get('data_folder','./')
    data_folder = kwargs.get('dfolder',data_folder)
    data_folder = kwargs.get('folder',data_folder)
    if data_folder[-1] != '/':
        data_folder+='/'
    review_folder = kwargs.get('review_folder','{}/review/'.format(data_folder))
    review_folder = kwargs.get('rfolder',review_folder)
    if review_folder[-1] != '/':
        review_folder+='/'
    spreadsheet = kwargs.get('spreadsheet','')
    spreadsheet = kwargs.get('sheet',spreadsheet)
    spreadsheet = kwargs.get('entry',spreadsheet)
    instrument = kwargs.get('instrument','uSpeX prism')
    verbose = kwargs.get('verbose',True)

# make sure relevant files and folders are in place
    if not os.path.exists(review_folder):
        try:
            os.makedirs(review_folder)
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise
#        raise NameError('\nCannot find review folder {}'.format(review_folder))
    if not os.path.exists(data_folder):
        raise NameError('\nCannot find data folder {}'.format(data_folder))
    if not os.path.exists('{}/published'.format(review_folder)):
        try:
            os.makedirs('{}/published'.format(review_folder))
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise
    if not os.path.exists('{}/unpublished'.format(review_folder)):
        try:
            os.makedirs('{}/unpublished'.format(review_folder))
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise

# if spreadsheet is given, use this to generate list of files
    if spreadsheet != '':
        try:
            t_input = fetchDatabase(spreadsheet)        
        except:
            try:
                t_input = fetchDatabase(data_folder+spreadsheet)        
            except:
                raise NameError('\nCould not find spreadsheet {} in local or data directories\n'.format(spreadsheet))
        tkeys = list(t_input.keys())
        if 'FILENAME' in tkeys:
            files = t_input['FILENAME']
        elif 'FILE' in tkeys:
            files = t_input['FILE']
        elif 'FILES' in tkeys:
            files = t_input['FILES']
        else:
            raise NameError('\nSpreadsheet {} does not have a column named filename; aborting\n'.format(spreadsheet))
        if data_folder not in files[0]:
            files = [data_folder+f for f in files]

# otherwise search for *.fits and *.txt files in data folder
    else:
        files = glob.glob(data_folder+'*.fits')+glob.glob(data_folder+'*.txt')
        if len(files) == 0:
            raise NameError('\nNo spectral files in {}\n'.format(data_folder))

# prep tables containing information
    t_spec = Table()
    for c in splat.DB_SPECTRA.keys():
        t_spec[c] = Column([' '*200 for f in files],dtype='str')
    t_src = Table()
    for c in splat.DB_SOURCES.keys():
        t_src[c] = Column([' '*200 for f in files],dtype='str')
    source_id0 = numpy.max(splat.DB_SOURCES['SOURCE_KEY'])
    spectrum_id0 = numpy.max(splat.DB_SPECTRA['DATA_KEY'])

# read in files into Spectrum objects
    if verbose:
        print('\nReading in {} files from {}'.format(len(files),data_folder))
#    splist = []
    t_spec['DATA_FILE'] = Column(files,dtype='str')
    t_spec['SPECTRUM'] = [splat.Spectrum(filename=f) for f in files]
    t_spec['INSTRUMENT'] = [instrument for f in files]
#    for f in files:
#        splist.append()

# populate spec array
    if verbose:
        print('\nGenerating initial input tables')
    t_spec['SOURCE_KEY'] = Column(numpy.arange(len(files))+source_id0+1,dtype='int')
    t_spec['DATA_KEY'] = Column(numpy.arange(len(files))+spectrum_id0+1,dtype='int')
#    t_spec['SPECTRUM'] = [sp for sp in splist]
    t_spec['QUALITY_FLAG'] = Column(['OK' for f in t_spec['DATA_FILE']],dtype='str')
    t_spec['PUBLISHED'] = Column(['N' for f in t_spec['DATA_FILE']],dtype='str')
#  measurements
    t_spec['MEDIAN_SNR'] = Column([sp.computeSN() for sp in t_spec['SPECTRUM']],dtype='float')
    t_spec['SPEX_TYPE'] = Column([splat.classifyByStandard(sp,string=True,method='kirkpatrick')[0] for sp in t_spec['SPECTRUM']],dtype='str')
    t_spec['SPEX_GRAVITY_CLASSIFICATION'] = Column([splat.classifyGravity(sp,string=True) for sp in t_spec['SPECTRUM']],dtype='str')
# populate spectral data table from fits file header
    for i,sp in enumerate(t_spec['SPECTRUM']):
        if 'DATE_OBS' in sp.header:
            t_spec['OBSERVATION_DATE'][i] = sp.header['DATE_OBS'].replace('-','')
            t_spec['JULIAN_DATE'][i] = Time(sp.header['DATE_OBS']).mjd
        if 'DATE' in sp.header:
            t_spec['OBSERVATION_DATE'][i] = sp.header['DATE'].replace('-','')
            t_spec['JULIAN_DATE'][i] = Time(sp.header['DATE']).mjd
        if 'TIME_OBS' in sp.header:
            t_spec['OBSERVATION_TIME'][i] = sp.header['TIME_OBS'].replace(':',' ')
        if 'MJD_OBS' in sp.header:
            t_spec['JULIAN_DATE'][i] = sp.header['MJD_OBS']
        if 'OBSERVER' in sp.header:
            t_spec['OBSERVER'][i] = sp.header['OBSERVER']
        if 'RESOLUTION' in sp.header:
            t_spec['RESOLUTION'][i] = sp.header['RESOLUTION']
        elif 'RES' in sp.header:
            t_spec['RESOLUTION'][i] = sp.header['RES']
        elif 'SLITW' in sp.header:
            t_spec['RESOLUTION'][i] = 200.*0.3/sp.header['SLITW']       # this is for new spex
        if 'AIRMASS' in sp.header:
            t_spec['AIRMASS'][i] = sp.header['AIRMASS']
        if 'VERSION' in sp.header:
            v = sp.header['VERSION']
            t_spec['REDUCTION_SPEXTOOL_VERSION'][i] = 'v{}'.format(v.split('v')[-1])
# populate spectral data table from spreadsheet 
    if spreadsheet != '':
#        if 'FILENAME' in tkeys:
#            t_spec['DATA_FILE'] = t_input['FILENAME']
        if 'DATE' in tkeys:
            t_spec['OBSERVATION_DATE'] = [splat.properDate(str(a),output='YYYYMMDD') for a in t_input['DATE']]
#            for a in t_input['DATE']:
#                print(a,splat.properDate(str(a)),Time(splat.properDate(str(a),output='YYYY-MM-DD')),Time(splat.properDate(str(a),output='YYYY-MM-DD')).mjd)
            t_spec['JULIAN_DATE'] = [Time(splat.properDate(str(a),output='YYYY-MM-DD')).mjd for a in t_input['DATE']]
        if 'RESOLUTION' in tkeys:
            t_spec['RESOLUTION'] = [r for r in t_input['RESOLUTION']]
        if 'SLIT' in tkeys:
            t_spec['RESOLUTION'] = [150.*0.5/float(s) for s in t_input['SLIT']]
        if 'AIRMASS' in tkeys:
            t_spec['AIRMASS'] = t_input['AIRMASS']
        if 'OBSERVER' in tkeys:
            t_spec['OBSERVER'] = t_input['OBSERVER']
        if 'DATA_REFERENCE' in tkeys:
            t_spec['DATA_REFERENCE'] = t_input['DATA_REFERENCE']
            for i,ref in enumerate(t_spec['DATA_REFERENCE']):
                if ref != '':
                    t_spec['PUBLISHED'][i] = 'Y'

#    for c in splist[0].header.keys():
#        if c != 'HISTORY':
#            print('{} {}'.format(c,splist[0].header[c]))

    t_src['SOURCE_KEY'] = t_spec['SOURCE_KEY']
    t_src['GRAVITY_CLASS_NIR'] = t_spec['SPEX_GRAVITY_CLASSIFICATION']
    t_src['GRAVITY_CLASS_NIR_REF'] = Column(['SPL' for sp in t_spec['SPECTRUM']],dtype='str')
    t_spec['COMPARISON_SPECTRUM'] = [splat.SPEX_STDS[spt] for spt in t_spec['SPEX_TYPE']]
    t_spec['COMPARISON_TEXT'] = [' '*200 for spt in t_spec['SPEX_TYPE']]
    for i,spt in enumerate(t_spec['SPEX_TYPE']):
        t_spec['COMPARISON_TEXT'][i] = '{} standard'.format(spt)

# determine coordinates as best as possible
    for i,sp in enumerate(t_spec['SPECTRUM']):
#        if i == 0:
#            for k in list(sp.header.keys()):
#                print(k,sp.header[k])
        if 'TCS_RA' in sp.header.keys() and 'TCS_DEC' in sp.header.keys():
            sp.header['RA'] = sp.header['TCS_RA']
            sp.header['DEC'] = sp.header['TCS_DEC']
            sp.header['RA'] = sp.header['RA'].replace('+','')
        if t_src['DESIGNATION'][i].strip() == '' and sp.header['RA'] != '' and sp.header['DEC'] != '':
            t_src['DESIGNATION'][i] = 'J{}+{}'.format(sp.header['RA'].replace('+',''),sp.header['DEC']).replace(':','').replace('.','').replace('+-','-').replace('++','+').replace('J+','J').replace(' ','')
#            print('DETERMINED DESIGNATION {} FROM RA/DEC'.format(t_src['DESIGNATION'][i]))
        if t_src['RA'][i].strip() == '' and t_src['DESIGNATION'][i].strip() != '':
            coord = splat.properCoordinates(t_src['DESIGNATION'][i])
            t_src['RA'][i] = coord.ra.value
            t_src['DEC'][i] = coord.dec.value
#            print('DETERMINED RA/DEC FROM DESIGNATION {}'.format(t_src['DESIGNATION'][i]))
#    print(t_src['DESIGNATION'],t_src['RA'],t_src['DEC'])
# populate source data table from spreadsheet
    if spreadsheet != '':
        if 'DESIGNATION' in tkeys:
            t_src['DESIGNATION'] = t_input['DESIGNATION']
            t_src['NAME'] = t_src['DESIGNATION']
#            coord = [splat.properCoordinates(s) for s in t_src['DESIGNATION']]
#            t_src['RA'] = [c.ra.value for c in coord]
#            t_src['DEC'] = [c.dec.value for c in coord]
        if 'NAME' in tkeys:
            t_src['NAME'] = t_input['NAME']
        if 'RA' in tkeys and 'DEC' in tkeys:
            if splat.isNumber(t_input['RA'][0]):
                t_src['RA'] = t_input['RA']
                t_src['DEC'] = t_input['DEC']
        if 'TYPE' in tkeys:
            t_src['LIT_TYPE'] = t_input['TYPE']
        if 'OPT_TYPE' in tkeys:
            t_src['OPT_TYPE'] = t_input['OPT_TYPE']
        if 'NIR_TYPE' in tkeys:
            t_src['NIR_TYPE'] = t_input['NIR_TYPE']

#    for c in splat.DB_SOURCES.keys():
#        if c not in t_src.keys():
#            t_src[c] = Column([' '*50 for sp in splist],dtype='str')        # force string

# transfer spectral types
    for i,t in enumerate(t_src['NIR_TYPE']):
        if t.replace(' ','') == '':
            t_src['NIR_TYPE'][i] = t_spec['SPEX_TYPE'][i]
            t_src['NIR_TYPE_REF'][i] = 'SPL'
        if t_src['LIT_TYPE'][i].replace(' ','') == '':
            t_src['LIT_TYPE'][i] = t_spec['SPEX_TYPE'][i]
            t_src['LIT_TYPE_REF'][i] = 'SPL'


# now do a SIMBAD search for sources based on coordinates
    if kwargs.get('nosimbad',False) == False:
        if verbose:
            print('\nSIMBAD search')
        _querySimbad2(t_src,simbad_radius=simbad_radius)


# fill in missing 2MASS photometry with Vizier query
    if kwargs.get('novizier',False) == False:
        if verbose:
            print('\n2MASS photometry from Vizier')

        if not checkOnline():
            if verbose:
                print('\nCould not perform Vizier search, you are not online')
        else:
            for i,jmag in enumerate(t_src['J_2MASS']):
                if float('{}0'.format(jmag.replace('--',''))) == 0.0:
                    t_vizier = splat.getPhotometry(splat.properCoordinates(t_src['DESIGNATION'][i]),radius=vizier_radius,catalog='2MASS')

        # multiple sources; choose the closest
                    if len(t_vizier) > 0:
                        t_vizier.sort('_r')
        #                print(len(t_vizier),t_vizier.keys())
        #                while len(t_vizier)>1:
        #                    t_vizier.remove_row(1) 
                        if verbose:
                            print('\n{}'.format(t_src['DESIGNATION'][i]))
                            print(t_vizier)
                        t_src['DESIGNATION'][i] = 'J{}'.format(t_vizier['_2MASS'][0])
                        t_src['J_2MASS'][i] = str(t_vizier['Jmag'][0]).replace('--','')
                        t_src['J_2MASS_E'][i] = str(t_vizier['e_Jmag'][0]).replace('--','')
                        t_src['H_2MASS'][i] = str(t_vizier['Hmag'][0]).replace('--','')
                        t_src['H_2MASS_E'][i] = str(t_vizier['e_Hmag'][0]).replace('--','')
                        t_src['KS_2MASS'][i] = str(t_vizier['Kmag'][0]).replace('--','')
                        t_src['KS_2MASS_E'][i] = str(t_vizier['e_Kmag'][0]).replace('--','')

    # add in distance if spectral type and magnitude are known
    for i,spt in enumerate(t_src['LIT_TYPE']):
        if spt.replace(' ','') != '' and float('{}0'.format(str(t_src['J_2MASS'][i]).replace('--',''))) != 0.0:
    #            print(spt,t_src['J_2MASS'][i],t_src['J_2MASS_E'][i])
            dist = splat.estimateDistance(spt=spt,filter='2MASS J',mag=float(t_src['J_2MASS'][i]))
            if not numpy.isnan(dist[0]):
                t_src['DISTANCE_PHOT'][i] = dist[0]
                t_src['DISTANCE_PHOT_E'][i] = dist[1]
                t_src['DISTANCE'][i] = dist[0]
                t_src['DISTANCE_E'][i] = dist[1]
        if float('{}0'.format(str(t_src['PARALLAX'][i]).replace('--',''))) != 0.0 and float('{}0'.format(str(t_src['PARALLAX_E'][i]).replace('--',''))) != 0.0 :
            t_src['DISTANCE'][i] = 1000./float(t_src['PARALLAX'][i])
            t_src['DISTANCE_E'][i] = float(t_src['DISTANCE'][i])*float(t_src['PARALLAX_E'][i])/float(t_src['PARALLAX'][i])
    # compute vtan
        if float('{}0'.format(str(t_src['MU'][i]).replace('--',''))) != 0.0 and float('{}0'.format(str(t_src['DISTANCE'][i]).replace('--',''))) != 0.0:
            t_src['VTAN'][i] = 4.74*float(t_src['DISTANCE'][i])*float(t_src['MU'][i])/1000.

    # clear up zeros
        if float('{}0'.format(str(t_src['J_2MASS'][i]).replace('--',''))) == 0.0:
            t_src['J_2MASS'][i] = ''
            t_src['J_2MASS_E'][i] = ''
        if float('{}0'.format(str(t_src['H_2MASS'][i]).replace('--',''))) == 0.0:
            t_src['H_2MASS'][i] = ''
            t_src['H_2MASS_E'][i] = ''
        if float('{}0'.format(str(t_src['KS_2MASS'][i]).replace('--',''))) == 0.0:
            t_src['KS_2MASS'][i] = ''
            t_src['KS_2MASS_E'][i] = ''
        if float('{}0'.format(str(t_src['PARALLAX'][i]).replace('--',''))) == 0.0:
            t_src['PARALLAX'][i] = ''
            t_src['PARALLAX_E'][i] = ''
        if float('{}0'.format(str(t_src['MU'][i]).replace('--',''))) == 0.0:
            t_src['MU'][i] = ''
            t_src['MU_E'][i] = ''
            t_src['MU_RA'][i] = ''
            t_src['MU_DEC'][i] = ''
        if float('{}0'.format(str(t_src['RV'][i]).replace('--',''))) == 0.0:
            t_src['RV'][i] = ''
            t_src['RV_E'][i] = ''
        if float('{}0'.format(str(t_src['VSINI'][i]).replace('--',''))) == 0.0:
            t_src['VSINI'][i] = ''
            t_src['VSINI_E'][i] = ''
        if float('{}0'.format(str(t_src['SIMBAD_SEP'][i]).replace('--',''))) == 0.0:
            t_src['SIMBAD_SEP'][i] = ''
        if t_src['GRAVITY_CLASS_NIR'][i] == '':
            t_src['GRAVITY_CLASS_NIR_REF'][i] = ''

    # compute J-K excess and color extremity
        if spt.replace(' ','') != '' and float('{}0'.format(str(t_src['J_2MASS'][i]).replace('--',''))) != 0.0 and float('{}0'.format(str(t_src['KS_2MASS'][i]).replace('--',''))) != 0.0:
            t_src['JK_EXCESS'][i] = float(t_src['J_2MASS'][i])-float(t_src['KS_2MASS'][i])-splat.typeToColor(spt,'J-K')[0]
            if t_src['JK_EXCESS'][i] == numpy.nan or t_src['JK_EXCESS'][i] == '' or t_src['JK_EXCESS'][i] == 'nan':
                t_src['JK_EXCESS'][i] = ''
            elif float(t_src['JK_EXCESS'][i]) > 0.3:
                t_src['COLOR_EXTREMITY'][i] == 'RED'
            elif float(t_src['JK_EXCESS'][i]) < -0.3:
                t_src['COLOR_EXTREMITY'][i] == 'BLUE'
            else:
                pass


# check for previous entries
    t_src['SHORTNAME'] = [splat.designationToShortName(d) for d in t_src['DESIGNATION']]
    splat.DB_SOURCES['SHORTNAME'] = [splat.designationToShortName(d) for d in splat.DB_SOURCES['DESIGNATION']]
    for i,des in enumerate(t_src['DESIGNATION']):

# check if shortnames line up
        if t_src['SHORTNAME'][i] in splat.DB_SOURCES['SHORTNAME']:
            for c in list(t_src.keys()):
                t_src[c][i] = splat.DB_SOURCES[c][numpy.where(splat.DB_SOURCES['SHORTNAME'] == t_src['SHORTNAME'][i])][0]
            t_spec['SOURCE_KEY'][i] = t_src['SOURCE_KEY'][i]

# check if SIMBAD names line up
        elif t_src['SIMBAD_NAME'][i] != '' and t_src['SIMBAD_NAME'][i] in splat.DB_SOURCES['SIMBAD_NAME']:
            for c in t_src.keys():
                if t_src[c][i] == '':
                    t_src[c][i] = splat.DB_SOURCES[c][numpy.where(splat.DB_SOURCES['SIMBAD_NAME'] == t_src['SIMBAD_NAME'][i])][0]
            t_spec['SOURCE_KEY'][i] = t_src['SOURCE_KEY'][i]

        else:
            pass

# check to see if prior spectrum was taken on the same date (possible redundancy)
        matchlib = searchLibrary(idkey=t_src['SOURCE_KEY'][i],date=t_spec['OBSERVATION_DATE'][i])
# previous observation on this date found - retain in case this is a better spectrum
        if len(matchlib) > 0.:
            mkey = matchlib['DATA_KEY'][0]
            if verbose:
                print('Previous spectrum found in library for data key {}'.format(mkey))
            t_spec['COMPARISON_SPECTRUM'][i] = splat.Spectrum(int(mkey))
            t_spec['COMPARISON_TEXT'][i] = 'repeat spectrum: {}'.format(mkey)
            print(t_spec['COMPARISON_TEXT'][i])
# no previous observation on this date - retain the spectrum with the highest S/N
        else:
            matchlib = splat.searchLibrary(idkey=t_src['SOURCE_KEY'][i])
            if len(matchlib) > 0:
                matchlib.sort('MEDIAN_SNR')
                matchlib.reverse()
                t_spec['COMPARISON_SPECTRUM'][i] = splat.Spectrum(int(matchlib['DATA_KEY'][0]))
                t_spec['COMPARISON_TEXT'][i] = 'alternate spectrum: {} taken on {}'.format(matchlib['DATA_KEY'][0],matchlib['OBSERVATION_DATE'][0])
                print(matchlib['DATA_KEY'][0])
                print(t_spec['COMPARISON_TEXT'][i])


# generate check plots
    legend = []
    for i,sp in enumerate(t_spec['SPECTRUM']):
        legend.extend(['Data Key: {} Source Key: {}\n{}'.format(t_spec['DATA_KEY'][i],t_spec['SOURCE_KEY'][i],t_spec['SPECTRUM'][i].name),'{} {}'.format(t_spec['COMPARISON_SPECTRUM'][i].name,t_spec['COMPARISON_TEXT'][i])])
    for s in t_spec['COMPARISON_SPECTRUM']: print(s)
    splat.plotBatch([s for s in t_spec['SPECTRUM']],comparisons=[s for s in t_spec['COMPARISON_SPECTRUM']],normalize=True,output=review_folder+'/review_plots.pdf',legend=legend,noise=True,telluric=True)


# output database updates
    if 'SHORTNAME' in t_src.keys():
        t_src.remove_column('SHORTNAME')
    if 'SELECT' in t_src.keys():
        t_src.remove_column('SELECT')
    if 'SELECT' in t_spec.keys():
        t_spec.remove_column('SELECT')   
    if 'SOURCE_SELECT' in t_spec.keys():
        t_spec.remove_column('SOURCE_SELECT')
    if 'SPECTRUM' in t_spec.keys():
        t_spec.remove_column('SPECTRUM')
    if 'COMPARISON_SPECTRUM' in t_spec.keys():
        t_spec.remove_column('COMPARISON_SPECTRUM')
    if 'COMPARISON_TEXT' in t_spec.keys():
        t_spec.remove_column('COMPARISON_TEXT')
#    for i in numpy.arange(len(t_spec['NOTE'])):
#        t_spec['NOTE'][i] = compdict[str(t_spec['DATA_KEY'][i])]['comparison_type']
    t_src.write(review_folder+'/source_update.csv',format='ascii.csv')
    t_spec.write(review_folder+'/spectrum_update.csv',format='ascii.csv')

# open up windows to review spreadsheets
# NOTE: WOULD LIKE TO MAKE THIS AUTOMATICALLY OPEN FILE
#    app = QtGui.QApplication(sys.argv)
#    window = Window(10, 5)
#    window.resize(640, 480)
#    window.show()
#    app.exec_()

    print('\nSpectral plots and update speadsheets now available in {}'.format(review_folder))
    response = input('Please review and edit, and press any key when you are finished...\n')


# NEXT STEP - MOVE FILES TO APPROPRIATE PLACES, UPDATE MAIN DATABASES
# source db
    t_src = fetchDatabase(review_folder+'/source_update.csv',csv=True)
#    if 'SIMBAD_SEP' in t_src.keys():
#        t_src.remove_column('SIMBAD_SEP')

    for col in t_src.colnames:
        tmp = t_src[col].astype(splat.DB_SOURCES[col].dtype)
        t_src.replace_column(col,tmp)
    t_merge = vstack([splat.DB_SOURCES,t_src])
    t_merge.sort('SOURCE_KEY')
    if 'SHORTNAME' in t_merge.keys():
        t_merge.remove_column('SHORTNAME')
    if 'SELECT' in t_merge.keys():
        t_merge.remove_column('SELECT')
    t_merge.write(review_folder+splat.DB_SOURCES_FILE,format='ascii.tab')

# spectrum db
    t_spec = fetchDatabase(review_folder+'spectrum_update.csv',csv=True)

# move files
    for i,file in enumerate(t_spec['DATA_FILE']):
        t_spec['DATA_FILE'][i] = '{}_{}.fits'.format(t_spec['DATA_KEY'][i],t_spec['SOURCE_KEY'][i])
        print(file[-4:],t_spec['DATA_FILE'][i])
        if file[-4:] == 'fits':
            if t_spec['PUBLISHED'][i] == 'Y':
                copyfile(file,'{}/published/{}'.format(review_folder,t_spec['DATA_FILE'][i]))
#                if verbose:
#                    print('Moved {} to {}/published/'.format(t_spec['DATA_FILE'][i],review_folder))
            else:
                copyfile(file,'{}/unpublished/{}'.format(review_folder,t_spec['DATA_FILE'][i]))
#                if verbose:
#                    print('Moved {} to {}/unpublished/'.format(t_spec['DATA_FILE'][i],review_folder))
        else:
            print(data_folder+file)
            sp = splat.Spectrum(file=file)
            if t_spec['PUBLISHED'][i] == 'Y':
                sp.export('{}/published/{}'.format(review_folder,t_spec['DATA_FILE'][i]))
#                if verbose:
#                    print('Moved {} to {}/published/'.format(t_spec['DATA_FILE'][i],review_folder))
            else:
                sp.export('{}/unpublished/{}'.format(review_folder,t_spec['DATA_FILE'][i]))
#                if verbose:
#                    print('Moved {} to {}/unpublished/'.format(t_spec['DATA_FILE'][i],review_folder))

# merge and export
    for col in t_spec.colnames:
#        print(col,splat.DB_SPECTRA[col].dtype)
        tmp = t_spec[col].astype(splat.DB_SPECTRA[col].dtype)
        t_spec.replace_column(col,tmp)
    t_merge = vstack([splat.DB_SPECTRA,t_spec])
    t_merge.sort('DATA_KEY')
    if 'SHORTNAME' in t_merge.keys():
        t_merge.remove_column('SHORTNAME')
    if 'SELECT' in t_merge.keys():
        t_merge.remove_column('SELECT')
    if 'SOURCE_SELECT' in t_merge.keys():
        t_merge.remove_column('SOURCE_SELECT')
    if 'DATEN' in t_merge.keys():
        t_merge.remove_column('DATEN')
    t_merge.write(review_folder+splat.DB_SPECTRA_FILE,format='ascii.tab')

    if verbose:
        print('\nDatabases updated; be sure to move these from {} to {}{}'.format(review_folder,splat.SPLAT_PATH,splat.DB_FOLDER))
        print('and to move spectral files from {}/published and {}/unpublished/\n'.format(review_folder,review_folder))

    return


###############################################################################
###################### TESTING FUNCTIONS #####################################
###############################################################################

def test_baseline():
    basefolder = '/Users/adam/projects/splat/exercises/ex9/'
    sp = splat.getSpectrum(shortname='1047+2124')[0]        # T6.5 radio emitter
    spt,spt_e = splat.classifyByStandard(sp,spt=['T2','T8'])
    teff,teff_e = splat.typeToTeff(spt)
    sp.fluxCalibrate('MKO J',splat.typeToMag(spt,'MKO J')[0],absolute=True)
    table = splat.modelFitMCMC(sp, mask_standard=True, initial_guess=[teff, 5.3, 0.], zstep=0.1, nsamples=100,savestep=0,filebase=basefolder+'fit1047',verbose=True)


def test_ingest(folder='./',**kwargs):
    importSpectra(data_folder=folder,**kwargs)

def test_combine():
# source db
    data_folder = '/Users/adam/projects/splat/adddata/daniella/spex_prism_160218/'
    review_folder = '/Users/adam/projects/splat/adddata/review/'
    t_src = fetchDatabase(review_folder+'source_update.csv',csv=True)
# convert all t_src columns to the same format in DB_SOURCES
    for col in t_src.colnames:
        tmp = t_src[col].astype(splat.DB_SOURCES[col].dtype)
        t_src.replace_column(col,tmp)
    t_merge = vstack([splat.DB_SOURCES,t_src])
    t_merge.sort('SOURCE_KEY')
    t_merge.write(review_folder+splat.DB_SOURCES_FILE,format='ascii.tab')

# spectrum db
    t_spec = fetchDatabase(review_folder+'spectrum_update.csv',csv=True)
# move files
# WARNING - ASSUMING THESE ARE FITS; NEED A FIX IF THEY ARE NOT
# COULD JUST READ IN TO SPECTRUM OBJECT AND OUTPUT AS FITS FILE
    for i,file in enumerate(t_spec['DATA_FILE']):
        t_spec['DATA_FILE'][i] = '{}_{}.fits'.format(t_spec['DATA_KEY'][i],t_spec['SOURCE_KEY'][i])
        if t_spec['PUBLISHED'][i] == 'Y':
            copyfile(data_folder+file,'{}/published/{}'.format(review_folder,t_spec['DATA_FILE'][i]))
            print('Moved {} to {}/published/'.format(t_spec['DATA_FILE'][i],review_folder))
        else:
            copyfile(data_folder+file,'{}/unpublished/{}'.format(review_folder,t_spec['DATA_FILE'][i]))
            print('Moved {} to {}/unpublished/'.format(t_spec['DATA_FILE'][i],review_folder))
# convert all t_src columns to the same format in DB_SOURCES
    for col in t_spec.colnames:
        tmp = t_spec[col].astype(splat.DB_SPECTRA[col].dtype)
        t_spec.replace_column(col,tmp)
    t_merge = vstack([splat.DB_SPECTRA,t_spec])
    t_merge.sort('DATA_KEY')
    t_merge.write(review_folder+splat.DB_SPECTRA_FILE,format='ascii.tab')
    print('\nDatabases updated; be sure to move these from {} to {}{}'.format(review_folder,splat.SPLAT_PATH,splat.DB_FOLDER))
    print('and to move spectral files from {}/published and {}/unpublished/\n'.format(review_folder,review_folder))


def test_missingbibs():
    bibs=[]
    dbsk = ['DISCOVERY_REFERENCE','OPT_TYPE_REF','NIR_TYPE_REF','LIT_TYPE_REF','GRAVITY_CLASS_OPTICAL_REF','GRAVITY_CLASS_NIR_REF','CLUSTER_REF','BINARY_REF','SBINARY_REF','COMPANION_REF','SIMBAD_SPT_REF','PARALLEX_REF','MU_REF','RV_REF','VSINI_REF']
    for k in dbsk:
        for b in splat.DB_SOURCES[k]:
            if b not in bibs and b != '':
                if getBibTex(b,force=True) == False:
                    bibs.append(b)
    dbsk = ['DATA_REFERENCE']
    for k in dbsk:
        for b in splat.DB_SPECTRA[k]:
            if b not in bibs and b != '':
                if getBibTex(b,force=True) == False:
                    bibs.append(b)
    if len(bibs) > 0:
        print('\nRetrieve the following from http://adsabs.harvard.edu/bib_abs.html and put into {}\n'.format(DB_FOLDER+BIBFILE))
        bibs.sort()
        for b in bibs: print(b)
    return

# main testing of program
if __name__ == '__main__':
#    dfolder = '/Users/adam/projects/splat/adddata/tobeadded/simp/prism/'
#    test_ingest(dfolder,spreadsheet=dfolder+'input.csv')
    test_missingbibs()

