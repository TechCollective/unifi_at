#!/usr/bin/env python
import json
import pprint
import six
from datetime import datetime, timedelta

class Autotask_Ticket_Params:
    types = {
        'id': 'str',
        'title': 'str',
        'companyID': 'str',
        'issueType': 'str',
        'subIssueType': 'str',
        'status': 'str',
        'queueID': 'str',
        'source': 'str',
        'description': 'str',
        'configurationItemID': 'str',
        'contractID': 'str',
        'createDate': 'str',
        'dueDateTime': 'str',
        'priority': 'str',
        'ticketCategory': 'str',
        'ticketNumber': 'str',
        'ticketType': 'str'
    }
   
    attribute_map = {
        'id': 'id',
        'title': 'title',
        'companyID': 'companyID',
        'issueType': 'issueType',
        'subIssueType': 'subIssueType',
        'status': 'status',
        'queueID': 'queueID',
        'source': 'source',
        'description': 'description',
        'configurationItemID': 'configurationItemID',
        'contractID': 'contractID',
        'createDate': 'createDate',
        'dueDateTime': 'dueDateTime',
        'priority': 'priority',
        'ticketCategory': 'ticketCategory',
        'ticketNumber': 'ticketNumber',
        'ticketType': 'ticketType'
   }

    def __init__(self, id=None, title=None, companyID=None, issueType=None, subIssueType=None, status=None, queueID=None, source=None, description=None, configurationItemID=None, contractID=None, 
                 createDate=None, dueDateTime=None, priority=None, ticketCategory=None, ticketNumber=None, ticketType=None):
        self._id = None
        self._title = None
        self._companyID = None
        self._issueType = None
        self._subIssueType = None
        self._status = None
        self._queueID = None
        self._source = None
        self._description = None
        self._configurationItemID = None
        self._contractID = None
        self._createDate = None
        self._dueDateTime = None
        self._priority = None
        self._ticketCategory = None
        self._ticketNumber = None
        self._ticketType = None
        
        if id is not None:
            self.id = id
        if title is not None:
            self.title = title
        if companyID is not None:
            self.companyID = companyID
        if issueType is not None:
            self.issueType = issueType
        if subIssueType is not None:
            self.subIssueType = subIssueType
        if status is not None:
            self.status = status
        if queueID is not None:
            self.queueID = queueID
        if source is not None:
            self.source = source
        if description is not None:
            self.description = description
        if configurationItemID is not None:
            self.configurationItemID = configurationItemID
        if contractID is not None:
            self.contractID = contractID
        if createDate is not None:
            self.createDate = createDate
        if dueDateTime is not None:
            self.dueDateTime = dueDateTime
        if priority is not None:
            self.priority = priority
        if ticketCategory is not None:
            self.ticketCategory = ticketCategory
        if ticketNumber is not None:
            self.ticketNumber = ticketNumber
        if ticketType is not None:
            self.ticketType = ticketType

    @property
    def id(self):
        return self._id
    
    @id.setter
    def id(self, id):
        self._id = id

    @property
    def title(self):
        return self._title
    
    @title.setter
    def title(self, title):
        self._title = title

    @property
    def companyID(self):
        return self._companyID
    
    @companyID.setter
    def companyID(self, companyID):
        self._companyID = companyID

    @property
    def issueType(self):
        return self._issueType
    
    @issueType.setter
    def issueType(self, issueType):
        self._issueType = issueType

    @property
    def status(self):
        return self._status
    
    @status.setter
    def status(self, status):
        self._status = status

    @property
    def queueID(self):
        return self._queueID
    
    @queueID.setter
    def queueID(self, queueID):
        self._queueID = queueID

    @property
    def source(self):
        return self._source
    
    @source.setter
    def source(self, source):
        self._source = source

    @property
    def description(self):
        return self._description
    
    @description.setter
    def description(self, description):
        self._description = description

    @property
    def configurationItemID(self):
        return self._configurationItemID
    
    @configurationItemID.setter
    def configurationItemID(self, configurationItemID):
        self._configurationItemID = configurationItemID

    @property
    def contractID(self):
        return self._contractID
    
    @contractID.setter
    def contractID(self, contractID):
        self._contractID = contractID

    @property
    def createDate(self):
        return self._createDate
    
    @createDate.setter
    def createDate(self, createDate):
        self._createDate = createDate

    @property
    def dueDateTime(self):
        return self._dueDateTime

    @dueDateTime.setter
    def dueDateTime(self, dueDateTime):
        self._dueDateTime =dueDateTime

    @property
    def priority(self):
        return self._priority

    @priority.setter
    def priority(self, priority):
        self._priority = priority

    @property
    def ticketCategory(self):
        return self._ticketCategory

    @ticketCategory.setter
    def ticketCategory(self, ticketCategory):
        self._ticketCategory = ticketCategory

    @property
    def ticketNumber(self):
        return self._ticketNumber
    
    @ticketNumber.setter
    def ticketNumber(self, ticketNumber):
        self._ticketNumber = ticketNumber

    @property
    def ticketType(self):
        return self._ticketType
    
    @ticketType.setter
    def ticketType(self,ticketType):
        self._ticketType = ticketType

    @classmethod
    def from_unifi_alert(cls, data):
        return cls( 
            print(data)
            )


    def to_dict(self):
        """Returns the model properties as a dict"""
        result = {}

        for attr, _ in six.iteritems(self.types):
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
        return result


    def to_str(self):
        """Returns the string representation of the model"""
        return pprint.pformat(self.to_dict())

