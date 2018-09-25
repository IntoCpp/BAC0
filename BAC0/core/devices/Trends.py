#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015 by Christian Tremblay, P.Eng <christian.tremblay@servisys.com>
# Licensed under LGPLv3, see file LICENSE in this source tree.
#
'''
Points.py - Definition of points so operations on Read results are more convenient.
'''

#--- standard Python modules ---
from datetime import datetime
from collections import namedtuple
import time

#--- 3rd party modules ---
try:
    import pandas as pd
    from pandas.io import sql
    try:
        from pandas import Timestamp
    except ImportError:
        from pandas.lib import Timestamp
    _PANDAS = True
except ImportError:
    _PANDAS = False
    
from bacpypes.object import TrendLogObject

#--- this application's modules ---
from ...tasks.Poll import SimplePoll as Poll
from ...tasks.Match import Match, Match_Value
from ..io.IOExceptions import NoResponseFromController, UnknownPropertyError
from ..utils.notes import note_and_log


#------------------------------------------------------------------------------

class TrendLogProperties(object):
    """
    A container for trend properties
    """

    def __init__(self):
        self.device = None
        self.oid = None
        self.object_name = None
        self.description = ''
        self.log_device_object_property = None
        self.buffer_size = 0
        self.record_count = 0
        self.total_record_count = 0
        self.description = None
        self.statusFlags = None
        self.status_flags = {'in_alarm':False,
                             'fault':False,
                             'overridden':False,
                             'out_of_service':False}

        self._df = None

class TrendLog(TrendLogProperties):
    """
    BAC0 simplification of TrendLog Object
    """
    def __init__(self, OID, device=None):
        self.properties = TrendLogProperties()
        self.properties.device = device
        self.properties.oid = OID
        self.history = None
        try:
            self.properties.object_name,\
            self.properties.description,\
            self.properties.record_count,\
            self.properties.buffer_size,\
            self.properties.total_record_count,\
            self.properties.log_device_object_property,\
            self.properties.statusFlags = self.properties.device.properties.network.readMultiple('{addr} trendLog {oid} objectName description recordCount bufferSize totalRecordCount logDeviceObjectProperty statusFlags'.format(
                addr=self.properties.device.properties.address,
                oid=str(self.properties.oid)))
            
        except Exception:
            raise Exception('Problem reading trendLog informations')
        
    def read_log_buffer(self):
        try:
            _log_buffer = self.properties.device.properties.network.readRange('{} trendLog {} logBuffer'.format(
                self.properties.device.properties.address,
                str(self.properties.oid)))
            self.create_dataframe(_log_buffer)
        except Exception:
            raise Exception('Problem reading TrendLog')

    def create_dataframe(self,log_buffer):
        index = []
        logdatum = []
        status = []
        for each in log_buffer:
            year, month, day, dow = each.timestamp.date
            year = year + 1900
            hours, minutes, seconds, ms = each.timestamp.time
            index.append(pd.to_datetime('{}-{}-{} {}:{}:{}.{}'.format(year,month,day,hours,minutes,seconds,ms),format='%Y-%m-%d %H:%M:%S.%f'))
            logdatum.append(each.logDatum.dict_contents())
            status.append(each.statusFlags)

        df = pd.DataFrame({'index_ts':index,'logdatum':logdatum,'status':status})
        df = df.set_index('index_ts')
        df['choice'] = df['logdatum'].apply(lambda x: list(x.keys())[0])
        df['value'] = df['logdatum'].apply(lambda x: list(x.values())[0])

        self.properties._df = df
        self.history = df['value'].copy()
        
    
