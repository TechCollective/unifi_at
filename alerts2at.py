#!/usr/bin/env python

# Description:
# Creates Autotask Tickets for UniFi alerts

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
from pyunifi.controller import Controller # TechCollective's feature branch
#import pyunifi
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

# Move to pyunifi
def _api_url_v2():
    return c.url + "v2/api/site/" + c.site_id + "/"

# Move to pyunifi
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

# Move to pyautotask
def get_tickets_field_value(name, lable):
    for field in tickets_entityInformation_fields:
        if field['name'] == name:
            for picklistValue in field['picklistValues']:
                if picklistValue['label'] == lable:
                    return str(picklistValue['value'])

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
    if mac:
        return c.get_device_stat(mac)


def check_existing_ticket(m_alert, event_config):
    print("              - checking for existing ticket")

    filter_fields = ""
    if hasattr(m_alert, "at_id"):
        filter_fields = at.create_filter("eq", "configurationItemID", str(m_alert.device_from.at_id))

    if filter_fields == "":
        filter_fields = at.create_filter("eq", "subIssueType", get_tickets_field_value("subIssueType",event_config['Subissue type']))
    else:
        filter_fields = filter_fields + "," + at.create_filter("eq", "subIssueType", get_tickets_field_value("subIssueType",event_config['Subissue type']))

    filter_fields = filter_fields + "," + at.create_filter("eq", "companyID", str(m_alert.at_company_id))
    return at.create_query("tickets", filter_fields)

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
        print("         - Already has a ticket Ticket")
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

        #print(syslog)

        m_alert = models.manifold_alert.from_unifi_syslog_dict(syslog)
        print("     - " + m_alert.unifi_alert_key)
        
        if create_ticket:
            if syslog['key'] == "DEVICE_DISCOVERED":
                print("          - Device Discovered. Ignoring")
                create_ticket = False
        
        
        if create_ticket:
            if m_alert.alert_time < datetime.today() - timedelta(days=1):
                print("          - Alert is old. Ignoring")
                create_ticket = False

        if create_ticket:
            print(syslog)
            sys.exit()

        #sys.exit()
        # if syslog['key'] == "DEVICE_RECONNECTED_WITH_DOWNLINKS":
        #     print(syslog['key'] + "-" + syslog['message'])
        # elif syslog['key'] == "DEVICE_UNREACHABLE_WITH_DOWNLINKS":
        #     print(syslog['key'] + "-" + syslog['message'])
        # elif syslog['key'] == "DEVICE_RECONNECTED_SEVERAL_TIMES":
        #     print(syslog['key'] + "-" + syslog['message'])
        # elif syslog['key'] == "DEVICE_RECONNECTED":
        #     print(syslog['key'] + "-" + syslog['message'])
        # elif syslog['key'] == "DEVICE_UNREACHABLE":
        #     print(syslog['key'] + "-" + syslog['message'])
        # elif syslog['key'] == "ISP_HIGH_LATENCY":
        #     print(syslog['key'] + "-" + syslog['message'])
        # elif syslog['key'] == "ISP_PACKET_LOSS":
        #     print(syslog['key'] + "-" + syslog['message'])
        # elif syslog['key'] == "CLIENT_IP_CONFLICT":
        #     print(syslog['key'] + "-" + syslog['message'])
        #     print(syslog)
        # elif syslog['key'] == "CLIENT_IP_CONFLICT_BULK":
        #     print(syslog['key'] + "-" + syslog['message'])
        #     print(syslog)
        # elif syslog['key'] == "DEVICE_DISCOVERED":
        #     #print(syslog['key'] + "-" + syslog['message'])
        #     a=True
        # elif syslog['key'] == "DEVICE_ADOPTED":
        #     # print(syslog['key'] + "-" + syslog['message'])
        #     a = True
        # elif syslog['key'] == "PORT_TRANSMISSION_ERRORS":
        #     print(syslog['key'] + "-" + syslog['message'])
        # elif syslog['key'] == "NETWORK_FAILED_OVER_TO_BACKUP_LTE":
        #     print(syslog['key'] + "-" + syslog['message'])
        # elif syslog['key'] == "RADIUS_SERVER_ISSUE":
        #     print(syslog['key'] + "-" + syslog['message'])
        # elif syslog['key'] == "NETWORK_RETURNED_FROM_BACKUP_WAN":
        #     print(syslog['key'] + "-" + syslog['message'])
        # elif syslog['key'] == "NETWORK_WAN_FAILED_MULTIPLE_TIMES":
        #     print(syslog['key'] + "-" + syslog['message'])
        # elif syslog['key'] == "ULTE_WARNING_LIMIT_EXCEEDED":
        #     print(syslog['key'] + "-" + syslog['message'])
        # elif syslog['key'] == "NETWORK_WAN_FAILED":
        #     print(syslog['key'] + "-" + syslog['message'])
        # else:
        #     print(syslog['key'])
        #     print(syslog)
        #     sys.exit()
        
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
    load_alerts_config()
    at_unifi_sites = sites_in_at()
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
                #check_system_log(site, company[0])
                #check_gateway(site)

                #TODO Need to figure out what this is
                #print(check_warnings(site))
                #clear_fixed_tickets(site, company)
                #TODO need to figure out what is creating Toast popups on the web interface of the unifi controller
                #time.sleep(10)
main()

#print(c.site_get())