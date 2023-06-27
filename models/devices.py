#!/usr/bin/env python
import json
import pprint
import six
from datetime import datetime, timedelta

class Devices:
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
