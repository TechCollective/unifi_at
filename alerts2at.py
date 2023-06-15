#!/usr/bin/env python

# Description:
# Creates Autotask Tickets for UniFi alerts

# Requirements
# API User has to have "edit Protected Data" permissions to edit UDFs
# TODO create an onboarding script
# Needed to create the following Autotask UDFs for these scripts
# Companies
#  Name         			| Type					| Sort Oder	|
#  UniFi Site ID			| Text (Multi Line)		| 2			| This is where the primary company where the site goes. CIs for UniFi devices will go here.
#  UniFi Subsite ID			| Text (Multi Line)		| 2			| This is where a seconardy site will go. If you want these CIs to show up as a configured client in a site, put that UniFi ID here
#
# Configuration Items
#  Name						| Type					| Sort Oder
#  UniFi Alerts Ignore list	| Text (Multi Line)		| 3
#  UniFi First Seen			| Date					| 2
#  UniFi Last Seen			| Date					| 2
#
# Needed Service Desk Issue Types
# Issue Type Name: UniFi Alerts
# All Subissues are associated with the "Monitoring Alert" Queue
#  Issue Type Name:
#  Commit Error
#  Detect Rogue AP
#  TODO Need to create
#  Detect Rogue DHCP Server
#  IPS Alert
#  Lost Contact
#  LTE Hard Limit Used
#  LTE Subscription Unknown
#  LTE Threshold
#  LTE Weak Signal
#  LTE Muliple Alerts
#  Radar Detected
#  STP Port Blocking
#  WAN Transition
#  ZZZ Unknown Event


# TODO Create a report on all site-devices that have entries in the ignroe
# TODO check for UniFi devices in AT that are not in the UniFi controller and deactivate them.
# TODO It looks like someone setup a device to the wrong client in Autotask and this confused the script. It was able to create an alert ticket, but not close it because it was on the wrong client.
# TODO create a search for device script and maybe connect it to slack
# TODO Alert in Slack or as a ticket if the script cannot log into the controller

import requests
import json
import csv
import sys
import time
from datetime import datetime, timedelta
import dateutil.parser
from pyunifi.controller import Controller
#config file within the same directory
import config
from pyautotask.atsite import atSite
import models

c = Controller(config.UnifiHost, config.UnifiUsername, config.UnifiPassword, config.UnifiPort, "v5")
at = atSite(config.atHost, config.atUsername, config.atPassword, config.atAPIInterationcode)

tickets_entityInformation_fields = at._api_read("Tickets/entityInformation/fields")['fields']

alerts_config = {}
issueTypes = []
subIssueTypes = []
ticketStatuses = []
atCIType4network = config.atCIType4network
atCICategory = config.atCICategory
atProductID = config.atProductID
# Create an Issue Type UniFi Alerts
atUnifiIssueType = "24"  # Need to move to the conf file
# Create a Sub-Issue Type called Lost Contact
atLostContact = "252"
atCommitError = "259"
atWANTransition = "264"
# Fix spelling to Rogue
atRougeAp = "254"
atStpBlocking = "260"
atLteHardLimitUsed = "251"
atLteThreshold = "253"
atUnknownAlert = "258"
atLteHardLimitCutoff = "267"

# Names in Unifi to ignore. Maybe switch this over to Site ID, so if the name changes, they don't pop out of this list.
unifi_ignore = config.unifi_ignore

def check_get_device_stat(mac):
	url = c._api_url() + "stat/device/" + mac
	response = c.session.get(url, params=None, headers=c.headers)
	if response.headers.get("X-CSRF-Token"):
		c.headers = {"X-CSRF-Token": response.headers["X-CSRF-Token"]}

	obj = json.loads(response.text)
	if "meta" in obj:
		if obj["meta"]["rc"] != "ok":
			if obj['meta']['msg'] != "api.err.UnknownDevice":
#				raise APIError(obj["meta"]["msg"])
				print("Unknown Device: " + obj['meta']['msg'])
	if "data" in obj:
		result = obj["data"]
	else:
		result = obj
	return result

def archive_alert(alert_id):
	params = {'_id': alert_id}
	return c._run_command('archive-alarm', params, mgr="evtmgr")


# Old
def send_unifi_alert_ticket(ticket_title, description, sub_issue, company_id, ci_id):
	filter_fields1 = at.create_filter("eq", "configurationItemID", str(ci_id))
	filter_fields2 = at.create_filter("eq", "subIssueType", sub_issue)
	filter_fields = filter_fields1 + "," + filter_fields2
	ticket = at.create_query("tickets", filter_fields)
	date = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000000Z")
	due_date = datetime.utcnow()
	due_date += timedelta(hours = 2)
	# TODO Check if other devices are on within the same network. Add that detail to the ticket
	if not ticket: # checks to see if there are already a ticket and doesn't create one
		# TODO add Due date. Currently expiring tickets by 2 horus before creation date.
		params = {
			'companyID': company_id,
			'configurationItemID': ci_id,
			'createDate': date,
			'dueDateTime': due_date,
			'description': description,
			'issueType': atUnifiIssueType,
			'subIssueType': sub_issue,
			'priority': "1",
			'source': "8",
			'status': "1",
			'queueID': "8",
			'title': ticket_title
		}
		return at._api_write("Tickets", params)
	else:
		return ticket

def lost_contact(alert, unifi_type):
	# TODO for each "Lost_Contact" event, we should check if the router is up. If the router is down, then it's the site that is down
	# and we shouldn't make multiple tickets. 
	# On the other hand, it the Gateway looses contact for some reason other than internet and other devices actually go down, we wouldn't get alerted.

	device = check_get_device_stat(alert[unifi_type])

	if device:
		if device[0]['state'] != 1:
			# TODO One possible fix is to power cycle the switch port if the devices is on a POE switch and powered by that switch.
			# TODO Most of these are solved by sending a set inform. Need to work on that.

#			ci = at.get_ci_by_serial(device[0]['serial'])[0]
			ci_object = at.get_ci_by_serial(device[0]['serial'])
			#Need to add something here to create CI if it doesn't exsit
			if ci_object:
				ci = ci_object[0]
				if unifi_type == 'gw':
					ticket_title = "UniFi Alert: Lost contact with the gateway"
				else:
					ticket_title = "UniFi Alert: Lost contact with the UniFi device"
				description = "Message from the UniFi Controller is: \n" + alert['datetime'] + " - " + alert['msg'] + "\n\nThis message will auto clear if the device checks back in.\n\n If we susspect that this issue can be resolved by sending a set inform, please assign the ticket to Jeff so he can attempt an autoheal script on it"

				send_unifi_alert_ticket(ticket_title, description, atLostContact, ci['companyID'], ci['id'])
	archive_alert(alert['_id'])

def commit_error(alert, unifi_type):
	device = check_get_device_stat(alert[unifi_type])
	ci = at.get_ci_by_serial(device[0]['serial'])[0]
	ticket_title = "UniFi Alert: Commit Error"
	description = "Message from the UniFi Controller is: " + alert['msg'] + "\n\nMore Information - Commit Error was: " + alert['commit_errors'] + "\n\nPlease not this message will not auto clear"
	send_unifi_alert_ticket(ticket_title, description, atCommitError, ci['companyID'], ci['id'])
	print("sent in a ticket for " + ci['referenceTitle'])
	archive_alert(alert['_id'])

def wan_transition(alert):
	device = check_get_device_stat(alert['gw'])
	# I think I can match uplink to wan1 ip
	alert_date = dateutil.parser.isoparse(alert['datetime'])
	if alert_date.strftime("%Y-%m-%d") == datetime.today().strftime("%Y-%m-%d"):
		if device:
			if device[0]['wan1']['ip'] != device[0]['uplink']['ip']:
				ci = at.get_ci_by_serial(device[0]['serial'])[0]
				ticket_title = "Gateway failover event"
				description = "Message from the UniFi Controller is: \n" + alert['datetime'] + " - " + alert['msg']
				send_unifi_alert_ticket(ticket_title, description, atWANTransition, ci['companyID'], ci['id'])
				print("sent in a ticket for " + ci['referenceTitle'])
				archive_alert(alert['_id'])				
			else:
				archive_alert(alert['_id'])
		else:
			print("EVT_GW_WANTransition - no device was returned")
			print(alert['msg'])
	else:
		archive_alert(alert['_id'])

def rouge_ap(alert):
	device = check_get_device_stat(alert['ap'])
	alert_date = dateutil.parser.isoparse(alert['datetime'])
	if alert_date.strftime("%Y-%m-%d") == datetime.today().strftime("%Y-%m-%d"):
		if device:
			ci = at.get_ci_by_serial(device[0]['serial'])[0]
			ticket_title = "Rogue AP Detected"
			description = "Message from UniFi Controller is: \n" + alert['datetime'] + " - " + alert['msg'] + "\n\n\n\nPlease Note: This message will not autoclear.\nIf this is a know Access Point and you wish to stop getting these alerts.\n * Consult with a senior tech!\n * Log into the UniFi Controller. \n * Make sure you are using 'Legacy Mode'. \n * Under 'Insight' on the left \n * pick 'Neighboring Access Point' in the upper right hand drop down list\n * Look for a AP that has a red dot in the 'Rouge' Column \n * On the far right of that row, when you hoover over it, the words 'Mark as known' will appear. Pick it. \n * Archive all Rogue AP alerts under 'Alerts'"

			send_unifi_alert_ticket(ticket_title, description, atRougeAp, ci['companyID'], ci['id'])
			print("sent in a ticket for " + ci['referenceTitle'])
			archive_alert(alert['_id'])

	else:
		archive_alert(alert['_id'])

def rouge_dhcp(alert):
	device = check_get_device_stat(alert['sw'])
	alert_date = dateutil.parser.isoparse(alert['datetime'])
	if alert_date.strftime("%Y-%m-%d") == datetime.today().strftime("%Y-%m-%d"):
		if device:
			ci = at.get_ci_by_serial(device[0]['serial'])[0]
			ticket_title = "Rogue DHCP Server Detected"
			description = "Message from UniFi Controller is: \n" + alert['datetime'] + " - " + alert['msg'] + "\n\n\n\nPlease Note: This message will not autoclear.\n\nIf this server is suppose to be acting as a DHCP server, please add it to the DHCP Guadian's list in the UniFi Controller. Please inform a senior tech."

			send_unifi_alert_ticket(ticket_title, description, atRougeAp, ci['companyID'], ci['id'])
			print("sent in a ticket for " + ci['referenceTitle'])
			archive_alert(alert['_id'])

	else:
		archive_alert(alert['_id'])


# TODO Figure out what to do with these
def radar_detected(alert):
	print(" - AP - Radar Detected")
	print(alert['msg'])

def stp_blocking(alert):
	device = check_get_device_stat(alert['sw'])
	port = int(alert['port']) -1
	if device[0]['port_table'][port]['stp_state'] != 'forwarding':
		ci = at.get_ci_by_serial(device[0]['serial'])[0]
		ticket_title = "Switch has an STP Event"
		description = "Message from UniFi Controller is: " + alert['msg']
		send_unifi_alert_ticket(ticket_title, description, atStpBlocking, ci['companyID'], ci['id'])
		print("sent in a ticket for "+ci['referenceTitle'])
		archive_alert(alert['_id'])
	elif device[0]['port_table'][port]['stp_state'] != 'disabled':
		archive_alert(alert['_id'])
	else:
		archive_alert(alert['_id'])

def lte_hard_limit_used(alert):
	# TODO Link this to the Threshold ticket, but change status to new and prioirty to Crital
	device = check_get_device_stat(alert['dev'])
	alert_date = dateutil.parser.isoparse(alert['datetime'])
	if alert_date.month == datetime.now().month:
		device = check_get_device_stat(alert['dev'])
		ci = at.get_ci_by_serial(device[0]['serial'])[0]
		ticket_title = "LTE Hard Limit reached"
		description = "Message from UniFi Controller is: " + alert['msg']
		send_unifi_alert_ticket(ticket_title, description, atLteHardLimitUsed, ci['companyID'], ci['id'])
		print("sent in a ticket for "+ ci['referenceTitle'])
		archive_alert(alert['_id'])

def lte_hard_limit_cutoff(alert):
	# TODO Link this to the Threshold ticket, but change status to new and prioirty to Crital
	device = check_get_device_stat(alert['dev'])
	alert_date = dateutil.parser.isoparse(alert['datetime'])
	if alert_date.month == datetime.now().month:
		device = check_get_device_stat(alert['dev'])
		ci = at.get_ci_by_serial(device[0]['serial'])[0]
		ticket_title = "LTE Hard Limit Cutoff"
		description = "Message from UniFi Controller is: " + alert['msg']
		send_unifi_alert_ticket(ticket_title, description, atLteHardLimitCutoff, ci['companyID'], ci['id'])
		print("sent in a ticket for "+ ci['referenceTitle'])
		archive_alert(alert['_id'])

def lte_threshold(alert):
	alert_date = dateutil.parser.isoparse(alert['datetime'])
	if alert_date.month == datetime.now().month:
		# TODO check if there is a ticket and update the ticket if it's a new Threshold
		# create ticket for first threshold. Append ticket for the next thresholds. Change status to "new"
		device = check_get_device_stat(alert['dev'])
		ci = at.get_ci_by_serial(device[0]['serial'])[0]
		ticket_title = "LTE Threshold reached"
		description = "Message from UniFi Controller is: " + alert['msg']
		send_unifi_alert_ticket(ticket_title, description, atLteThreshold, ci['companyID'], ci['id'])
		print("sent in a ticket for "+ ci['referenceTitle'])
		archive_alert(alert['_id'])
	else:
		archive_alert(alert['_id'])

def ipsAlert(alert):
	# TODO Create ticket for jeff to do something
	print(" - IPS Alert")
	print(alert['msg'])

def outlet_power_cycle(alert):
	# TODO Create ticket
	print(" TODO Create ticket function for power cycled events")
	print(alert['msg'])
	archive_alert(alert['_id'])

def unknown_alert(alert):
	alert_date = dateutil.parser.isoparse(alert['datetime'])
	if alert_date.month == datetime.now().month:
		print(alert)
		device = []
		key = ""
		# TODO remove device check here. Just create a ticket, assign it to jeff. put in the org and the full alert information. I can sort it from there.
		if 'dev' in alert:
			key = 'dev'
		elif 'xg' in alert:
			key = 'xg'
		if key != "":
			device = check_get_device_stat(alert[key])
			# TODO if device doesn't excite, create it
			ci = at.get_ci_by_serial(device[0]['serial'])[0]
			ticket_title = "Unknown UniFi Alert"
			description = "Since this is an alert that I have not seen before, a tech will have to assess how urgent this is. If it is not urgent, please assign to Jeff, so he can update the script to detect these alerts in the furture. Please no not archive the alert!\n\n\nMessage from UniFi Controller is: " + alert['msg'] + "\nAlert Key is: " + alert['key'] + "\n\nAlert was not Archived."
			send_unifi_alert_ticket(ticket_title, description, atUnknownAlert, ci['companyID'], ci['id'])
			print("sent in a ticket for " + ci['referenceTitle'])
		else:
			print("-----------------------------------------------")
			print("create fuction to send in a ticket without a CI")



def _api_url_v2():
    return c.url + "v2/api/site/" + c.site_id + "/"

def _api_write_v2(url, params=None):
    return c._write(_api_url_v2() + url, params)

def load_alerts_config():
    # TODO need error checking here. Make sure the file is formated correctly
    reader = csv.DictReader(open('unifi_alerts_config.csv'))
    for row in reader:
        key = row.pop('Event')
        if key in alerts_config:
            pass
        alerts_config[key] = row

# 	# TODO for each "Lost_Contact" event, we should check if the router is up. If the router is down, then it's the site that is down
# 	# and we shouldn't make multiple tickets. 
# 	# On the other hand, it the Gateway looses contact for some reason other than internet and other devices actually go down, we wouldn't get alerted.

# 	device = check_get_device_stat(alert[unifi_type])

# 	if device:
# 		if device[0]['state'] != 1:
# 			# TODO One possible fix is to power cycle the switch port if the devices is on a POE switch and powered by that switch.
# 			# TODO Most of these are solved by sending a set inform. Need to work on that.

# #			ci = at.get_ci_by_serial(device[0]['serial'])[0]
# 			ci_object = at.get_ci_by_serial(device[0]['serial'])
# 			#Need to add something here to create CI if it doesn't exsit
# 			if ci_object:
# 				ci = ci_object[0]
# 				if unifi_type == 'gw':
# 					ticket_title = "UniFi Alert: Lost contact with the gateway"
# 				else:
# 					ticket_title = "UniFi Alert: Lost contact with the UniFi device"
# 				description = "Message from the UniFi Controller is: \n" + alert['datetime'] + " - " + alert['msg'] + "\n\nThis message will auto clear if the device checks back in.\n\n If we susspect that this issue can be resolved by sending a set inform, please assign the ticket to Jeff so he can attempt an autoheal script on it"

# 				send_unifi_alert_ticket(ticket_title, description, atLostContact, ci['companyID'], ci['id'])
# 	archive_alert(alert['_id'])
 
def get_device_from_alert(alert):
    mac = None
    for key in alert:
        if alert['key'] == "EVT_GW_Lost_Contact":
            mac = alert['gw']
        elif alert['key'] == "EVT_GW_CommitError":
            mac = alert['gw']
        elif alert['key'] == "EVT_GW_CommitError":
            mac = alert['gw']
        elif alert['key'] == "EVT_GW_WANTransition":
            mac = alert['gw']
        elif alert['key'] == "EVT_AP_Lost_Contact":
            mac = alert['ap']
        elif alert['key'] == "EVT_SW_Lost_Contact":
            mac = alert['sw']
        elif alert['key'] == "EVT_SW_StpPortBlocking":
            mac = alert['sw']
        elif alert['key'] == "EVT_LTE_Lost_Contact":
            mac = alert['dev']
        elif alert['key'] == "EVT_XG_Lost_Contact":
            mac = alert['xg']


    # try:
    #     device = c.get_device_stat(alert[unifi_type])
    # except:
    #     pass
    # return device
    if mac:
        return c.get_device_stat(mac)











def get_tickets_field_value(name, lable):
    for field in tickets_entityInformation_fields:
        if field['name'] == name:
            for picklistValue in field['picklistValues']:
                if picklistValue['label'] == lable:
                    return str(picklistValue['value'])


# OLD
def get_issueType( issueTypeConfig ):
    issueTypes, subIssueTypes = load_issueTypes()
    for issueType in issueTypes:
        if issueType['label'] == issueTypeConfig:
            return issueType['value']

# OLD
def get_subIssueType(subIssueTypeConfig):
    issueTypes, subIssueTypes = load_issueTypes()
    for subIssueType in subIssueTypes:
        if subIssueType['label'] == subIssueTypeConfig:
            return subIssueType['value']
# OLD
def get_ticket_status(statusConfig):
    ticket_statuses = load_statuses()
    for status in ticket_statuses:
        if status['label'] == statusConfig:
            return status['value']

def check_existing_ticket(m_alert, event_config):
    print(event_config)
    filter_fields = ""

    if hasattr(m_alert, "at_id"):
#    if m_alert.device_from.at_id:
        filter_fields = at.create_filter("eq", "configurationItemID", str(m_alert.device_from.at_id))
    if filter_fields == "":
        filter_fields = at.create_filter("eq", "subIssueType", get_tickets_field_value("subIssueType",event_config['Subissue type']))
    else:
        filter_fields = filter_fields + "," + at.create_filter("eq", "subIssueType", get_tickets_field_value("subIssueType",event_config['Subissue type']))
    print(filter_fields)
    return at.create_query("tickets", filter_fields)

#def create_alert_ticket(alert, event, company, device, description_bonus):
def create_alert_ticket(m_alert, event_config):
    ticket_exsiting = check_existing_ticket(m_alert, event_config)
    #TODO maybe add an updated note
    if ticket_exsiting == []:
        print("         - Creating Ticket")
        print(event_config['Subissue type'])
        params = {
                'title': event_config['Ticket Title'],
                #'companyID': company['id'],
                'companyID': m_alert.at_company_id,
                'issueType': get_tickets_field_value("issueType", event_config['Issue type']),
                'subIssueType': get_tickets_field_value("subIssueType", event_config['Subissue type']),
                'status': get_tickets_field_value("status", 'New'),
                'queueID': get_tickets_field_value("queueID", event_config['Queue']),
                'source' : get_tickets_field_value("source", 'Monitoring Alert'),
            }
        description = 'Message from the UniFi Controller is: ' + m_alert.alert_time.strftime("%Y-%m-%d, %H:%M") + " " + m_alert.message
        # TODO pull extra information for description in the event_config
        params['description'] = description
        
        #if m_alert.device_from.at_id:
        if hasattr(m_alert, "at_id"):
            params['configurationItemID'] = m_alert.device_from.at_id

        if m_alert.unifi_alert_key == "EVT_GW_Lost_Contact":
            params['priority'] = get_tickets_field_value("priority", 'Critical')
        else:
            params['priority'] = get_tickets_field_value("priority", 'Medium')

        # TODO check other devices. Get their "last seen" to see if we can assume they have not checked in. Add results to body

            #'createDate': date,
            #'dueDateTime': due_date,
        return at._api_write("Tickets", params)
    else:
        archive_alert(m_alert.unifi_alert_id)


def get_event_config(alert_key):
    event_config = None
    for key in alerts_config:
        if key == alert_key:
            event_config = alerts_config[key]
            break
    return event_config

# system-log/update-alert
# system-log/admin-access
# system-log/client-alert
# system-log/ap-logs
# system-log/triggers
# app-traffic-rate?start=1686013478558&end=1686099878558&includeUnidentified=false

def check_system_log(site, company):
    print("- Checking System Logs")   
    # 1 hour = 1.00 	3,600,000
    furture_time = time.time_ns() // 1000000 - 3600000
    hour_past = 0
    params = {"timestampFrom": hour_past, "timestampTo": furture_time, "pageSize": 100, "categories": ["INTERNET", "POWER", "DEVICES", "SYSTEM"], "pageNumber": 0, "systemLogDeviceTypes": [
    	"GATEWAYS", "SWITCHES", "ACCESS_POINT", "SMART_POWER", "BUILDING_TO_BUILDING_BRIDGES", "UNIFI_LTE", "NON_NETWORK_DEVICES"]}
    # TODO Move to pyunifi
    syslogs = _api_write_v2("system-log/system-critical-alert", params)

    for syslog in syslogs:
        event_config = None
        create_ticket = True

        print(syslog)
        sys.exit()
        m_alert = models.manifold_alert.from_unifi_syslog_dict(syslog)

        if syslog['key'] == "DEVICE_RECONNECTED_WITH_DOWNLINKS":
            print(syslog['key'] + "-" + syslog['message'])
        elif syslog['key'] == "DEVICE_UNREACHABLE_WITH_DOWNLINKS":
            print(syslog['key'] + "-" + syslog['message'])
        elif syslog['key'] == "DEVICE_RECONNECTED_SEVERAL_TIMES":
            print(syslog['key'] + "-" + syslog['message'])
        elif syslog['key'] == "DEVICE_RECONNECTED":
            print(syslog['key'] + "-" + syslog['message'])
        elif syslog['key'] == "DEVICE_UNREACHABLE":
            print(syslog['key'] + "-" + syslog['message'])
        elif syslog['key'] == "ISP_HIGH_LATENCY":
            print(syslog['key'] + "-" + syslog['message'])
        elif syslog['key'] == "ISP_PACKET_LOSS":
            print(syslog['key'] + "-" + syslog['message'])
        elif syslog['key'] == "CLIENT_IP_CONFLICT":
            print(syslog['key'] + "-" + syslog['message'])
            print(syslog)
        elif syslog['key'] == "CLIENT_IP_CONFLICT_BULK":
            print(syslog['key'] + "-" + syslog['message'])
            print(syslog)
        elif syslog['key'] == "DEVICE_DISCOVERED":
            #print(syslog['key'] + "-" + syslog['message'])
            a=True
        elif syslog['key'] == "DEVICE_ADOPTED":
            # print(syslog['key'] + "-" + syslog['message'])
            a = True
        elif syslog['key'] == "PORT_TRANSMISSION_ERRORS":
            print(syslog['key'] + "-" + syslog['message'])
        elif syslog['key'] == "NETWORK_FAILED_OVER_TO_BACKUP_LTE":
            print(syslog['key'] + "-" + syslog['message'])
        elif syslog['key'] == "RADIUS_SERVER_ISSUE":
            print(syslog['key'] + "-" + syslog['message'])
        elif syslog['key'] == "NETWORK_RETURNED_FROM_BACKUP_WAN":
            print(syslog['key'] + "-" + syslog['message'])
        elif syslog['key'] == "NETWORK_WAN_FAILED_MULTIPLE_TIMES":
            print(syslog['key'] + "-" + syslog['message'])
        elif syslog['key'] == "ULTE_WARNING_LIMIT_EXCEEDED":
            print(syslog['key'] + "-" + syslog['message'])
        elif syslog['key'] == "NETWORK_WAN_FAILED":
            print(syslog['key'] + "-" + syslog['message'])
        else:
            print(syslog['key'])
            print(syslog)
            sys.exit()


        
def check_unarchived_alerts(site, company):
    print("- Checking unarchvied alerts")
    alerts = c.get_alerts_unarchived()

    for alert in alerts:
        event_config = None
        create_ticket = True
       
        m_alert = models.manifold_alert.from_unifi_dict(alert)
        unifi_device = get_device_from_alert(alert)
        if unifi_device:
            #TODO Check if device excite, if not create it.
            m_alert.device_from = models.manifold_device.from_unifi_dict(unifi_device)
            m_alert.device_from.at_id = at.get_ci_by_serial(m_alert.device_from.serial)[0]['id']
        m_alert.at_company_id = company['id']

        print("     - " + m_alert.unifi_alert_key)
        
        if create_ticket:
            if m_alert.alert_time < datetime.today() - timedelta(days=1):
                print("          - Alert is old. Clearing alert")
                archive_alert(m_alert.unifi_alert_id)
                create_ticket = False

        event_config = get_event_config(m_alert.unifi_alert_key)
        if create_ticket:
            if event_config is None:
                print("          - No config for this alert. Skipping alert.")
                create_ticket = False

        #if "Lost_Contact" in alert['key']:
        if "Lost_Contact" in m_alert.unifi_alert_key:
            #if device['state']:
            if m_alert.device_from.state == 1:
                print("          - Device state is active. Clearing alert.")
                #archive_alert(alert['_id'])
                archive_alert(m_alert.unifi_alert_id)
                create_ticket = False
            #else:
                # TODO add "disconnection_reason" (from device json) to body
                # TODO add how long device has been down to body
                # TODO add last seen to body
                # TODO check if there are other open "Lost Contact" tickets and add their ticket numbers to the body
        if create_ticket:
            if event_config['Create Ticket'] == "TRUE":
                reply = create_alert_ticket(m_alert, event_config)
                # TODO check the reply and respond to errors
                if reply != []:
                    archive_alert(m_alert.unifi_alert_id)



                
        
        
    
def check_unarchived_alerts_old(site):
	alerts = c.get_alerts_unarchived()
	print(site['desc'])
	for alert in alerts:
		if alert['key'] == "EVT_GW_Lost_Contact":
			lost_contact(alert, 'gw')
		elif alert['key'] == "EVT_AP_Lost_Contact":
			lost_contact(alert, 'ap')
		elif alert['key'] == "EVT_SW_Lost_Contact":
			lost_contact(alert, 'sw')
		elif alert['key'] == "EVT_LTE_Lost_Contact":
			lost_contact(alert, 'dev')
		elif alert['key'] == "EVT_XG_Lost_Contact":
			lost_contact(alert, 'xg')
		elif alert['key'] == "EVT_GW_CommitError":
			commit_error(alert, 'gw')
		elif alert['key'] == "EVT_GW_RestartedUnknown": # we run a different script to detect if there are multiple alerts for the same device.
			archive_alert(alert['_id'])	
		elif alert['key'] == "EVT_GW_WANTransition": # WAN Failover event
			wan_transition(alert)
		elif alert['key'] == "EVT_AP_DetectRogueAP":
			rouge_ap(alert)
		elif alert['key'] == "EVT_AP_RadarDetected":
			radar_detected(alert)
		elif alert['key'] == "EVT_SW_StpPortBlocking":
			stp_blocking(alert)
		elif alert['key'] == "EVT_SW_RestartedUnknown":
			archive_alert(alert['_id'])	
		elif alert['key'] == "EVT_LTE_HardLimitUsed":
			lte_hard_limit_used(alert)
		elif alert['key'] == "EVT_LTE_HardLimitCutoff":
			lte_hard_limit_cutoff(alert)
		elif alert['key'] == "EVT_LTE_Threshold":
			lte_threshold(alert)
		elif alert['key'] == "EVT_IPS_IpsAlert":
			ipsAlert(alert)
		elif alert['key'] == "EVT_SW_DetectRogueDHCP":
			rouge_dhcp(alert)
		elif alert['key'] == "EVT_USP_OutletPowerCycle":
			outlet_power_cycle(alert)
		else:
			unknown_alert(alert)


def close_ticket(ticket):
	# TODO add a note to the ticket	

    params = {
        'id': ticket['id'],
        'status': "5",
    }
    return at._api_update("Tickets", params)

def clear_fixed_tickets(site, company):
    # TODO if time entry add note, alert tech in slack, do not close
    
	# Fix Lost Contact tickets if device comes back on
	filter_fields = at.create_filter("noteq", "status", "5") # Not equial Closed ticket
	filter_fields = filter_fields + "," + at.create_filter("eq", "subIssueType", atLostContact) # UniFi subisseu Lost Contact
	filter_fields = filter_fields + "," + at.create_filter("eq", "companyID", str(company[0]['id'])) # Autotask Company
	tickets = at.create_query("tickets", filter_fields)
	for ticket in tickets:
		if ticket['configurationItemID'] is not None:
			at_device = at.get_ci_by_id(str(ticket['configurationItemID']))
			unifi_device = check_get_device_stat(at_device[0]['serialNumber'])
			if unifi_device:
				if unifi_device[0]['state'] == 1:
					close_ticket(ticket)
	# Fix WAN Transition tickets if Primary WAN comes back up
	filter_fields = at.create_filter("noteq", "status", "5") # Not equial Closed ticket
	filter_fields = filter_fields + "," + at.create_filter("eq", "subIssueType", atWANTransition) # UniFi subisseu Lost Contact
	filter_fields = filter_fields + "," + at.create_filter("eq", "companyID", str(company[0]['id'])) # Autotask Company
	tickets = at.create_query("tickets", filter_fields)
	for ticket in tickets:
		if ticket['configurationItemID'] is not None:
			at_device = at.get_ci_by_id(str(ticket['configurationItemID']))
			unifi_device = check_get_device_stat(at_device[0]['serialNumber'])
			if unifi_device:
				if unifi_device[0]['wan1']['ip'] == unifi_device[0]['uplink']['ip']:
					close_ticket(ticket)

def check_radius_ip():
	atRadiusIpChange = "265" # Hard Coding everything else, why not this.
	c.site_id = "x28yoxh6" # Hard coding Worker Center until I figure out a better way.
	device = check_get_device_stat("24:5a:4c:98:9f:49")
	if device[0]['connect_request_ip'] != "104.37.239.117": # Hard coding IP addree for the current office. Need to just update Jumpcloud
		ci = at.get_ci_by_serial(device[0]['serial'])[0]
		ticket_title = "Alert: Worker Center's external IP changed"
		description = "This will break radius. I'm working on a way to update Jumpcloud automaticly, but for now, you must log into just cloud and change the IP address for radius to " + device[0]['connect_request_ip'] + ".\n\n\n You need to assign this ticket to Jeff to fix the scrip, because the IP address is currently hardcoded."
		send_unifi_alert_ticket(ticket_title, description, atRadiusIpChange, ci['companyID'], ci['id'])
		print("sent in a ticket for " + ci['referenceTitle'])

# TODO Move this to pyunifi
def check_warnings(site):
    return c._api_read("stat/widget/warnings")

#TODO move to pyautotask
def load_issueTypes():
    ticket_fields = at._api_read("Tickets/entityInformation/fields")
    for ticket_field in ticket_fields['fields']:
        if ticket_field['name'] == "issueType":
            issueTypes = ticket_field['picklistValues']
        if ticket_field['name'] == "subIssueType":
            subIssueTypes = ticket_field['picklistValues']
    return issueTypes, subIssueTypes

def load_statuses():
    ticket_fields = at._api_read("Tickets/entityInformation/fields")
    for ticket_field in ticket_fields['fields']:
        if ticket_field['name'] == "status":
            ticketStatuses = ticket_field['picklistValues']
    return ticketStatuses

def sites_in_at():
    at_unifi_sites = []
    for site in c.get_sites():
        if site['desc'] not in unifi_ignore:
            c.site_id = site['name']
            filter_field = at.create_filter("contains", "UniFi Site ID", site['name'], 1)
            company = at.get_companies(filter_field)
           
            if not company:
                print(site['desc'] + " doesn't have a UniFi Site ID. Please add " + site['name'] + " to the Autotask Company's UDF field")
            else:
                at_unifi_sites.append(site)
    return at_unifi_sites

def main():
    # check_radius_ip()
    # Loop through all sites in the Un267,iFi Controller
    load_alerts_config()
    at_unifi_sites = sites_in_at()
    # TODO Create function to check for Site ID in Autotask and return only sites that do have it. We can use that fuction to print the sites that don't in the begining of the run.
    #for site in c.get_sites():
    for site in at_unifi_sites:
        if site['desc'] not in unifi_ignore:
            c.site_id = site['name']
            filter_field = at.create_filter("contains", "UniFi Site ID", site['name'], 1)
            company = at.get_companies(filter_field)
           
            if not company:
                print(site['desc'] + " doesn't have a UniFi Site ID. Please add " + site['name'] + " to the Autotask Company's UDF field")
            else:
                print("\n" + site['desc'])
                check_unarchived_alerts(site, company[0])
                #check_gateway(site)
                #check_system_log(site, company[0])
                #TODO Need to figure out what this is
                #print(check_warnings(site))
                #clear_fixed_tickets(site, company)
                #TODO need to figure out what is creating Toast popups on the web interface of the unifi controller
                #time.sleep(10)
main()