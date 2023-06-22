#!/usr/bin/env python
import json
import pprint
import six
from datetime import datetime, timedelta

class manifold_alert:
    manifold_types = {
        'alert_time': 'str',
        'message': 'str',
        'device_from': 'manifold_device',
        'device_extra': 'list[manifold_device]',
        'unifi_alert_id': 'str',
        'unifi_alert_key': 'str',
        'at_company_id': 'str'
    }
   
    attribute_map = {
       'alert_time': 'time',
       'message': 'msg',
       'device_from': 'mainfold_device',
       'device_list': 'mainfold_device',
       'unifi_alert_id': '_id',
       'unifi_alert_key': 'key',
       'at_company_id': 'id'
   }
    def __init__(self, alert_time=None, message=None, device_from=None, device_extra=None, unifi_alert_id=None, unifi_alert_key=None, at_company_id=None ):
        self._alert_time = None
        self._message = None
        self._device_from = None
        self._device_extra = None
        self._unifi_alert_id = None
        self._unifi_alert_key = None
        self._at_company_id = None
        
        if alert_time is not None:
            self.alert_time = alert_time
        if message is not None:
            self.message = message
        if device_from is not None:
            self.device_from = device_from
        if device_extra is not None:
            self.device_extra = device_extra
        if unifi_alert_id is not None:
            self.unifi_alert_id = unifi_alert_id
        if unifi_alert_key is not None:
            self.unifi_alert_key = unifi_alert_key
        if at_company_id is not None:
            self.at_company_id = at_company_id

    @property
    def alert_time(self):
        return self._alert_time
    
    @alert_time.setter
    def alert_time(self, alert_time):
        self._alert_time = alert_time

    @property
    def message(self):
        return self._message
    
    @message.setter
    def message(self, message):
        self._message = message

    @property
    def device_from(self):
        return self._device_from
    
    @device_from.setter
    def device_from(self, device_from):
        self._device_from = device_from

    @property
    def device_extra(self):
        return self._device_extra
    
    @device_extra.setter
    def device_extra(self, device_extra):
        self._device_extra = device_extra

    @property
    def unifi_alert_id(self):
        return self._unifi_alert_id
    
    @unifi_alert_id.setter
    def unifi_alert_id(self, unifi_alert_id):
        self._unifi_alert_id = unifi_alert_id

    @property
    def unifi_alert_key(self):
        return self._unifi_alert_key
    
    @unifi_alert_key.setter
    def unifi_alert_key(self, unifi_alert_key):
        self._unifi_alert_key = unifi_alert_key
        
    @classmethod
    def from_unifi_dict(cls, data):
        return cls(
            datetime.fromtimestamp(data['time']/1000), 
            data['msg'],
            unifi_alert_id = data['_id'],
            unifi_alert_key = data['key'],
            )

    @classmethod
    def from_unifi_syslog_dict(cls, data):
        return cls(
            datetime.fromtimestamp(data['timestamp']/1000), 
            data['message'],
            unifi_alert_id = data['id'],
            unifi_alert_key = data['key']
            )

    def to_dict(self):
        """Returns the model properties as a dict"""
        result = {}

        for attr, _ in six.iteritems(self.manifold_types):
            value = getattr(self, attr)
            if isinstance(value, list):
                result[attr] = list(map(
                    lambda x: x.to_dict() if hasattr(x, "to_dict") else x,
                    value
                ))
            elif hasattr(value, "to_dict"):
                result[attr] = value.to_dict()
            elif isinstance(value, dict):
                result[attr] = dict(map(
                    lambda item: (item[0], item[1].to_dict())
                    if hasattr(item[1], "to_dict") else item,
                    value.items()
                ))
            else:
                result[attr] = value
        if issubclass(manifold_alert, dict):
            for key, value in self.items():
                result[key] = value

        return result


    def to_str(self):
        """Returns the string representation of the model"""
        return pprint.pformat(self.to_dict())

class manifold_device:
    manifold_types = {
        'hostname': 'str',
        'mac': 'str',
        'serial': 'str',
        'state': 'str',
        'at_id': 'str' 
    }
   
    attribute_map = {
       'hostname': 'hostname',
       'mac': 'mac',
       'serial': 'serial',
       'state': 'state',
       'at_id': 'id'
   }
    def __init__(self, mac=None, serial=None, hostname=None, state=None, at_id=None):
        self._hostname = None
        self._mac = None
        self._serial = None
        self._state = None
        self._at_id = None
        
        
        if hostname is not None:
            self.hostname = hostname
        if mac is not None:
            self.mac = mac
        if serial is not None:
            self.serial = serial
        if state is not None:
            self.state = state
        if at_id is not None:
            self.at_id = at_id


    @property
    def hostname(self):
        return self._hostname
    
    @hostname.setter
    def hostname(self, hotname):
        self._hostname = hostname

    @property
    def mac(self):
        return self._mac
    
    @mac.setter
    def mac(self, mac):
        self._mac = mac

    @property
    def serial(self):
        return self._serial
    
    @serial.setter
    def serial(self, serial):
        self._serial = serial

    @property
    def state(self):
        return self._state
    
    @state.setter
    def state(self, state):
        self._state = state

    @property
    def at_id(self):
        return self._at_id
    
    @at_id.setter
    def at_id(self, at_id):
        self._at_id = at_id

    @classmethod
    def from_unifi_dict(cls, data):
        return cls( 
            data['mac'], 
            data['serial'],
            state = data['state']
            )

    def to_dict(self):
        """Returns the model properties as a dict"""
        result = {}

        for attr, _ in six.iteritems(self.manifold_types):
            value = getattr(self, attr)
            if isinstance(value, list):
                result[attr] = list(map(
                    lambda x: x.to_dict() if hasattr(x, "to_dict") else x,
                    value
                ))
            elif hasattr(value, "to_dict"):
                result[attr] = value.to_dict()
            elif isinstance(value, dict):
                result[attr] = dict(map(
                    lambda item: (item[0], item[1].to_dict())
                    if hasattr(item[1], "to_dict") else item,
                    value.items()
                ))
            else:
                result[attr] = value
        if issubclass(manifold_alert, dict):
            for key, value in self.items():
                result[key] = value

        return result


    def to_str(self):
        """Returns the string representation of the model"""
        return pprint.pformat(self.to_dict())
